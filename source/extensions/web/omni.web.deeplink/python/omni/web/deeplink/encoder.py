"""Provides Base64URL encoding and decoding functionality for deep links."""

__all__ = ["Base64URLEncoder"]

import base64
import binascii
import json
import urllib.parse

import carb


class Base64URLEncoder:
    """Handle Base64URL encoding/decoding for deep links"""

    @staticmethod
    def encode(data: dict) -> str:
        """Encode dictionary to Base64URL string

        Args:
            data (dict): Dictionary to encode

        Returns:
            str: Base64URL encoded string (no padding)
        """
        # Serialize the dictionary to a JSON string
        json_string = json.dumps(data, separators=(",", ":"))  # this prevents commas with spaces
        # Encode the JSON string to bytes
        json_bytes = json_string.encode("utf-8")
        # Perform Base64URL encoding
        base64url_bytes = base64.urlsafe_b64encode(json_bytes)
        # Decode the Base64URL bytes to a string
        url = base64url_bytes.decode("utf-8")
        url_bytes = url.encode("utf-8")
        crc = binascii.crc32(url_bytes)
        return Base64URLEncoder._add_padding(f"{url}{hex(crc).upper()[-2:]}")

    @staticmethod
    def decode(encoded: str, remove_padding: bool = True, use_crc: bool = True) -> dict:
        """Decode Base64URL string to dictionary

        Args:
            encoded (str): Base64URL encoded string
            remove_padding (bool): Remove padding characters if needed for decoding
            use_crc (bool): Use CRC to validate the link

        Returns:
            dict: Decoded data structure

        Raises:
            ValueError: If decoding fails or invalid JSON
        """
        # decode link_data to dict
        if not encoded:
            raise ValueError("Encoded string is empty")

        if remove_padding:
            encoded = Base64URLEncoder._remove_padding(encoded)

        if use_crc:
            crc = encoded[-2:]
            encoded = encoded[:-2]
            url_bytes = encoded.encode("utf-8")
            crc32 = binascii.crc32(url_bytes)
            if hex(crc32).upper()[-2:] != crc:
                raise ValueError(f"CRC mismatch. The deeplink may be corrupted.")

        try:
            # Encode the input string to bytes if it's not already
            encoded_bytes = encoded.encode("ascii")
            # Decode the URL-safe Base64 string to bytes
            decoded_bytes = base64.urlsafe_b64decode(encoded_bytes)
            # Decode the bytes to a UTF-8 string
            json_string = decoded_bytes.decode("utf-8")
            # Parse the JSON string into a dictionary
            return json.loads(json_string)

        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
            carb.log_error(f"Error decoding or parsing: {e}")

        raise ValueError(f"Failed to decode deep link")

    @staticmethod
    def _add_padding(encoded: str) -> str:
        """Add padding characters if needed for decoding

        Args:
            encoded (str): Base64URL encoded string to add padding to

        Returns:
            str: Portal URL with encoded data embedded
        """
        portal_base_url = carb.settings.get_settings().get("exts/omni.web.deeplink/portal_base_url")
        application_id = carb.settings.get_settings().get("exts/omni.web.deeplink/application_id")
        portal_url = portal_base_url.replace("<app-id>", urllib.parse.quote(application_id))
        portal_url = portal_url.replace("<link-data>", encoded)
        return portal_url

    @staticmethod
    def _remove_padding(encoded: str) -> str:
        """Remove padding characters if needed for decoding

        Args:
            encoded (str): URL string to extract encoded data from

        Returns:
            str: Extracted encoded data from query parameters
        """
        portal_base_url = carb.settings.get_settings().get("exts/omni.web.deeplink/portal_base_url")

        # Extract the query string part
        if "?" in encoded:
            query_string = encoded.split("?")[1]
            # Parse the query string
            parsed_params = urllib.parse.parse_qs(query_string)

            # link-data becomes link_data
            if parsed_params.get("link_data"):
                return f"{parsed_params.get('link_data')[0]}"

            if parsed_params.get("payload"):
                return f"{parsed_params.get('payload')[0]}"

        return encoded

    @staticmethod
    def can_decode_link(encoded: str, remove_padding: bool = True, use_crc: bool = True) -> bool:
        """Check if the link can be decoded

        Args:
            encoded (str): Base64URL encoded string
            remove_padding (bool): Remove padding characters if needed for decoding
            use_crc (bool): Use CRC to validate the link

        Returns:
            bool: True if the link can be decoded, False otherwise
        """

        try:
            Base64URLEncoder.decode(encoded, remove_padding, use_crc)
            return True
        except (ValueError, TypeError):
            return False

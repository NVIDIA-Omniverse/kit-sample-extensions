## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""Tests for the read_log_file helper in log_download module."""

import base64
import os
import tempfile

import carb
import carb.settings
import omni.kit.app
import omni.kit.test

from ..log_download import read_log_file


class TestLogDownload(omni.kit.test.AsyncTestCase):
    """Unit tests for read_log_file."""

    async def setUp(self):
        self.temp_files = []
        self.app = omni.kit.app.get_app()
        self.settings = carb.settings.get_settings()

    async def tearDown(self):
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                carb.log_warn(f"Failed to clean up temp file {temp_file}: {e}")
        self.temp_files.clear()
        await self.app.next_update_async()

    def _create_temp_log_file(self, content: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".log", prefix="test_kit_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
        except Exception:
            os.close(fd)
            raise
        self.temp_files.append(path)
        return path

    async def test_returns_dict_with_expected_keys(self):
        """Successful read returns a dict with filename, content, and size."""
        log_path = self._create_temp_log_file(b"Test log line\n")
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        self.assertIn("filename", result)
        self.assertIn("content", result)
        self.assertIn("size", result)

    async def test_content_is_valid_base64_of_original_bytes(self):
        """content field round-trips back to the original file bytes."""
        test_content = b"Hello, log!\nLine 2\n"
        log_path = self._create_temp_log_file(test_content)
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        decoded = base64.b64decode(result["content"])
        self.assertEqual(decoded, test_content)

    async def test_size_matches_raw_byte_count(self):
        """size field equals the number of raw bytes in the file."""
        test_content = b"A" * 1234
        log_path = self._create_temp_log_file(test_content)
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["size"], len(test_content))

    async def test_filename_is_basename_of_path(self):
        """filename field is the basename of the log path."""
        log_path = self._create_temp_log_file(b"Test\n")
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["filename"], os.path.basename(log_path))

    async def test_returns_none_for_nonexistent_file(self):
        """Returns None when the file does not exist."""
        result = await read_log_file(log_path="/nonexistent/path/to/log.txt")
        self.assertIsNone(result)

    async def test_returns_none_when_no_path_and_no_setting(self):
        """Returns None when log_path is None and /log/file setting is empty."""
        original = self.settings.get_as_string("/log/file")
        self.settings.set_string("/log/file", "")
        try:
            result = await read_log_file(log_path=None)
            self.assertIsNone(result)
        finally:
            if original:
                self.settings.set_string("/log/file", original)

    async def test_reads_from_settings_when_no_path_given(self):
        """Falls back to /log/file setting when log_path is None."""
        test_content = b"Log from settings\n"
        log_path = self._create_temp_log_file(test_content)
        original = self.settings.get_as_string("/log/file")
        self.settings.set_string("/log/file", log_path)
        try:
            result = await read_log_file(log_path=None)
            self.assertIsNotNone(result)
            self.assertEqual(base64.b64decode(result["content"]), test_content)
        finally:
            if original:
                self.settings.set_string("/log/file", original)

    async def test_binary_content_preserved(self):
        """All 256 byte values survive the base64 round-trip."""
        test_content = bytes(range(256)) * 100  # 25.6 KB
        log_path = self._create_temp_log_file(test_content)
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        self.assertEqual(base64.b64decode(result["content"]), test_content)

    async def test_large_file_returns_single_payload(self):
        """read_log_file always returns one dict; omni.kit.livestream.messaging splits on the wire."""
        test_content = b"X" * 200_000  # 200 KB — well above the 64 KiB messaging threshold
        log_path = self._create_temp_log_file(test_content)
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["size"], len(test_content))
        self.assertEqual(base64.b64decode(result["content"]), test_content)

    async def test_empty_file_returns_payload_with_zero_size(self):
        """Empty files return a valid payload with size 0 and empty content."""
        log_path = self._create_temp_log_file(b"")
        result = await read_log_file(log_path=log_path)

        self.assertIsNotNone(result)
        self.assertEqual(result["size"], 0)
        self.assertEqual(result["content"], "")

    async def test_returns_none_when_file_exceeds_size_limit(self):
        """read_log_file returns None without opening the file when it exceeds MAX_LOG_DOWNLOAD_SIZE_BYTES."""
        import omni.web.log_downloader.log_download as log_download_module

        original_limit = log_download_module.MAX_LOG_DOWNLOAD_SIZE_BYTES
        log_download_module.MAX_LOG_DOWNLOAD_SIZE_BYTES = 10  # 10 bytes
        try:
            log_path = self._create_temp_log_file(b"This is definitely more than 10 bytes")
            result = await read_log_file(log_path=log_path)
            self.assertIsNone(result)
        finally:
            log_download_module.MAX_LOG_DOWNLOAD_SIZE_BYTES = original_limit

    async def test_file_at_exact_size_limit_is_allowed(self):
        """A file exactly at MAX_LOG_DOWNLOAD_SIZE_BYTES is accepted (limit is exclusive)."""
        import omni.web.log_downloader.log_download as log_download_module

        original_limit = log_download_module.MAX_LOG_DOWNLOAD_SIZE_BYTES
        test_content = b"A" * 100
        log_download_module.MAX_LOG_DOWNLOAD_SIZE_BYTES = len(test_content)
        try:
            log_path = self._create_temp_log_file(test_content)
            result = await read_log_file(log_path=log_path)
            self.assertIsNotNone(result)
            self.assertEqual(result["size"], len(test_content))
        finally:
            log_download_module.MAX_LOG_DOWNLOAD_SIZE_BYTES = original_limit

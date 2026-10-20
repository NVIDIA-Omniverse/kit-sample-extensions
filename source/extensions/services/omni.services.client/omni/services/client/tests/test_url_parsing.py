# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni.kit.test import AsyncTestCase
from omni.services.client.transports.local import *

from .. import AsyncClient, TransportNotFoundError


class AsyncClientURLParsingTestCase(AsyncTestCase):
    """Test cases for parsing of URL and associated error handlers."""

    async def test_url_parsing_with_local_scheme_does_not_raise_error(self) -> None:
        """Validate that an URI provided to an AsyncClient with a valid scheme segment does not raise any error."""
        try:
            _ = AsyncClient(uri="local://")
        except:
            self.fail(msg='Expected an AsyncClient to be successfully constructed using a "local://" URI.')

    async def test_url_parsing_with_missing_scheme_raises_value_error(self) -> None:
        """Validate that an URI provided to an AsyncClient without a valid scheme segment raises a ValueError."""
        TEST_URI = "127.0.0.1"

        with self.assertRaises(expected_exception=ValueError) as exc:
            _ = AsyncClient(uri=TEST_URI)

        self.assertEqual(
            first=str(exc.exception),
            second=f'The URI provided to the Client ("{TEST_URI}") did not contain a scheme fulfilling the pattern "<scheme>://<netloc>/<path>".',
        )

    async def test_url_parsing_with_unregistered_scheme_raises_transport_not_found_error(self) -> None:
        """
        Validate that an URI provided to an AsyncClient without a registered scheme segment raises a
        TransportNotFoundError.
        """
        TEST_SCHEME = "transport-not-yet-registered"
        TEST_URI = f"{TEST_SCHEME}://example.com"

        with self.assertRaises(expected_exception=TransportNotFoundError) as exc:
            _ = AsyncClient(uri=TEST_URI)

        self.assertEqual(
            first=str(exc.exception),
            second=f'No suitable transport for the scheme "{TEST_SCHEME}" can be found when attempting to fulfill the pattern "<scheme>://<netloc>/<path>". Ensure the right client transport extensions are enabled.',
        )

    async def test_scheme_parsing_is_done_in_a_case_insensitive_manner(self) -> None:
        """
        Validate that when parsing the scheme of a URI, retreiving the Transport from the scheme is done in a
        case-insensitive manner.
        """
        try:
            _ = AsyncClient(uri="LoCaL://")
        except:
            self.fail(msg='Expected an AsyncClient to be successfully constructed using a "local://" URI.')

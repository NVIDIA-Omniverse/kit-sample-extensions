# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import List, Tuple

from fastapi import Request
from omni.kit.test import AsyncTestCase
from starlette.types import Scope

from ..requests import convert_headers_to_dict, get_correlation_id


class CoreRequestsTestCase(AsyncTestCase):
    """Test cases for validation of Request utilities."""

    def _build_request(self, headers: List[Tuple[str, str]] = []) -> Request:
        """
        Utility method to facilitate creating a FastAPI Request containing Headers as they would be formatted from a
        legitimate request reaching a Service endpoint.

        Args:
            headers (List[Tuple[str, str]]): Headers to include in the incoming request.

        Returns:
            Request: A FastAPI Request formatted using the given Headers.

        """
        scope: Scope = {
            "type": "http",
            "headers": headers,
        }
        return Request(scope=scope)

    async def test_empty_headers_are_converted_to_empty_dict(self) -> None:
        """Validate that empty Request headers are converted to an equivalent empty Python dictionary."""
        headers = []
        dict = convert_headers_to_dict(request=self._build_request(headers=headers))

        self.assertEqual(first=dict, second={})

    async def test_headers_are_converted_to_dict(self) -> None:
        """Validate that standard Request Headers are converted to their appropriate Python dictionary format."""
        headers = [
            (b"X-Test-Header", b"Test value"),
        ]
        dict = convert_headers_to_dict(request=self._build_request(headers=headers))

        self.assertEqual(first=dict, second={"x-test-header": "Test value"})

    async def test_duplicate_header_keys_are_joined_into_dict(self) -> None:
        """
        Validate that Request Headers containing multiple identical keys are merged into the same key in the resulting
        Python dictionary, in order to prevent loss of data.
        """
        headers = [
            (b"X-Test-Header", b"Test value 1"),
            (b"X-Test-Header", b"Test value 2"),
        ]
        dict = convert_headers_to_dict(request=self._build_request(headers=headers))

        self.assertEqual(first=dict, second={"x-test-header": "Test value 1,Test value 2"})

    async def test_duplicate_header_keys_with_mixed_casing_are_joined_into_dict(self) -> None:
        """
        Validate that Request Headers containing multiple identical keys with mixed casing are merged into the same key
        in the resulting Python dictionary, in order to prevent loss of data.
        """
        headers = [
            (b"x-TEsT-HeaDER", b"Test value 1"),
            (b"x-TeSt-HeADeR", b"Test value 2"),
        ]
        dict = convert_headers_to_dict(request=self._build_request(headers=headers))

        self.assertEqual(first=dict, second={"x-test-header": "Test value 1,Test value 2"})

    async def test_correlation_id_type(self) -> None:
        """Validate that Correlation IDs are of the appropriate type, if supported."""
        correlation_id = get_correlation_id()

        if correlation_id is not None:
            self.assertIsInstance(obj=correlation_id, cls=str)
            self.assertGreater(a=len(correlation_id), b=0)

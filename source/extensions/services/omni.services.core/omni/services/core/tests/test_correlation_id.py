# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import json
from typing import Any, Dict, List, Optional, Tuple
from unittest import skipIf

IS_CORRELATION_ID_SUPPORTED = True
try:
    from asgi_correlation_id.middleware import is_valid_uuid4
except:
    IS_CORRELATION_ID_SUPPORTED = False

import carb
import omni.kit.test
from fastapi import Header, HTTPException, Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from ..exceptions import KitServicesBaseException
from ..main import deregister_router, get_app, register_router
from ..routers import ServiceAPIRouter


@skipIf(condition=not IS_CORRELATION_ID_SUPPORTED, reason="Skipping test, as Correlation IDs are not enabled.")
class CorrelationIDTestCase(omni.kit.test.AsyncTestCase):
    """Test cases for validation of unique Correlation ID Headers from the Services framework."""

    SETTING_PATH_PREFIX = "/exts/omni.services.core/correlation_id"
    USE_MIDDLEWARE_SETTING_PATH = f"{SETTING_PATH_PREFIX}/use_default_middleware"
    HEADER_NAME_SETTING_PATH = f"{SETTING_PATH_PREFIX}/header_name"
    UPDATE_REQUEST_HEADER_SETTING_PATH = f"{SETTING_PATH_PREFIX}/update_request_header"

    TEST_SERVICE_URL = "/lorem-ipsum"

    def setUp(self) -> None:
        super().setUp()

        # Capture initial Carbonite settings to ensure start-up values can be inspected:
        self._settings = carb.settings.get_settings_interface()
        self._default_use_default_correlation_id_middleware = self._settings.get_as_bool(
            self.USE_MIDDLEWARE_SETTING_PATH
        )
        self._default_header_name = self._settings.get_as_string(self.HEADER_NAME_SETTING_PATH)
        self._default_update_request_header = self._settings.get_as_bool(self.UPDATE_REQUEST_HEADER_SETTING_PATH)

        # Setup a test endpoint to be used by individual tests:
        self._set_up_test_endpoint()

    def tearDown(self) -> None:
        # Tear down the test endpoint used by individual tests:
        self._tear_down_test_endpoint()

        # Restore default Carbonite settings to avoid interfering with other tests in the session's test cases:
        self._settings.set(self.USE_MIDDLEWARE_SETTING_PATH, self._default_use_default_correlation_id_middleware)
        self._settings.set(self.HEADER_NAME_SETTING_PATH, self._default_header_name)
        self._settings.set(self.UPDATE_REQUEST_HEADER_SETTING_PATH, self._default_update_request_header)

        return super().tearDown()

    def _set_up_test_endpoint(self) -> None:
        """Set up a test endpoint to be used by individual tests."""
        self._router = ServiceAPIRouter()

        @self._router.get(path=self.TEST_SERVICE_URL)
        async def lorem_ipsum(request: Request) -> Dict[str, Any]:
            return {"success": True}

        register_router(router=self._router)

    def _tear_down_test_endpoint(self) -> None:
        """Tear down the test endpoint used by individual tests."""
        deregister_router(router=self._router)

    async def _get_response(
        self,
        url: str,
        data: Optional[Any] = None,
        headers: List[Tuple[bytes, bytes]] = [],
    ) -> Tuple[Any, int, Dict[str, str]]:
        """
        Utility to send a request to the given Service handler and provide its response.

        Args:
            url (str): URL of the Service handler where to route the request to.
            data (Optional[Any]): Optional data to send as the `body` of the request.
            headers (List[Tuple[bytes, bytes]]): Additional HTTP Headers to send along with the request.

        Returns:
            Tuple[Any, int, Dict[str, str]]: A Tuple containing the response from the given Service endpoint, with
                information about the response's `body`, its status code and list of Headers.

        """
        scope = {
            "type": "http",
            "method": "GET",
            "path": url,
            "query_string": b"",
            "headers": [
                (b"content-type", b"application/json"),
                *headers,
            ],
        }
        if data is not None:
            scope["body"] = json.dumps(data).encode("ascii")

        async def _receive():
            body = bytes(scope["body"], "ascii") if not isinstance(scope["body"], bytes) else scope["body"]
            return {
                "type": "http.request",
                "body": body,
            }

        results: List[Any] = []

        async def _send(result_data: Any):
            results.append(result_data)

        # Send a request to the Service endpoint hosted at the given URL:
        await get_app()(scope=scope, receive=_receive, send=_send)

        # Parse the Service response:
        is_json_response = False
        response_code = 200
        response_headers: Dict[str, str] = {}
        response_body: Any = None
        for entry in results:
            if entry["type"] == "http.response.start":
                if "status" in entry:
                    response_code = entry["status"]
                if "headers" in entry:
                    if list(
                        filter(lambda x: x[0] == b"content-type" and x[1] == b"application/json", entry["headers"])
                    ):
                        is_json_response = True
                    for key, value in entry["headers"]:
                        decoded_key = str(key, encoding="utf-8")
                        decoded_value = str(value, encoding="utf-8")
                        response_headers[decoded_key] = decoded_value
            elif entry["type"] == "http.response.body" and "body" in entry:
                response_body = entry["body"].decode("utf-8")
                if is_json_response:
                    # In case the response contains the `Content-Type: application/json` Header, provide the response
                    # under its parsed representation for convenience (assuming it is well-formed JSON):
                    response_body = json.loads(response_body)

        return response_body, response_code, response_headers

    async def test_default_settings_values(self) -> None:
        """Validate default value for Carbonite settings related to Correlation IDs."""
        self.assertEqual(first=self._default_use_default_correlation_id_middleware, second=True)
        self.assertEqual(first=self._default_header_name, second="X-Correlation-ID")
        self.assertEqual(first=self._default_update_request_header, second=True)

    async def test_correlation_ids_have_the_expected_format(self) -> None:
        """Validate that `X-Correlation-ID` Headers emitted with responses are in the expected format."""
        _, _, headers = await self._get_response(url=self.TEST_SERVICE_URL)

        self.assertIn(member="x-correlation-id", container=headers)
        self.assertGreater(a=len(headers["x-correlation-id"]), b=0)
        self.assertTrue(
            expr=is_valid_uuid4(headers["x-correlation-id"]),
            msg='Expected the "X-correlation-ID" Header to be formatted as a valid UUID version 4 token.',
        )

    async def test_correlation_ids_are_unique_for_each_request(self) -> None:
        """Validate that each request emitted against the Services API contain unique Correlation IDs."""
        _, _, headers_a = await self._get_response(url=self.TEST_SERVICE_URL)
        _, _, headers_b = await self._get_response(url=self.TEST_SERVICE_URL)

        self.assertIn(member="x-correlation-id", container=headers_a)
        self.assertIn(member="x-correlation-id", container=headers_b)
        self.assertNotEqual(first=headers_a["x-correlation-id"], second=headers_b["x-correlation-id"])

    async def test_service_responds_to_requests_with_same_correlation_ids(self) -> None:
        """
        Validate that if an incoming request is received by the Service containing a valid Correlation ID, it is reused
        when serving the response.
        """
        HEADER_NAME_KEY = "X-Correlation-ID"
        REQUEST_ID = "d4b15197780949aa8e2de85a9538c142"

        self.assertTrue(
            expr=is_valid_uuid4(REQUEST_ID),
            msg=f'Expected the "{HEADER_NAME_KEY}" Header to be formatted as a valid UUID version 4 token.',
        )

        _, _, headers = await self._get_response(
            url=self.TEST_SERVICE_URL,
            headers=[
                # Send a valid UUID version 4 along with the request, to ensure the response will contain the same one:
                (str.encode(HEADER_NAME_KEY.lower()), str.encode(REQUEST_ID)),
            ],
        )

        self.assertIn(member=HEADER_NAME_KEY.lower(), container=headers)
        self.assertEqual(first=headers[HEADER_NAME_KEY.lower()], second=REQUEST_ID)

    async def test_service_responds_to_requests_with_new_correlation_ids_when_invalid(self) -> None:
        """
        Validate that if an incoming request is received by the Service containing an invalid Correlation ID, a new one
        is issued when serving the response.
        """
        HEADER_NAME_KEY = "X-Correlation-ID"
        REQUEST_ID = "!!!-invalid-UUID-v4-!!!"

        self.assertFalse(
            expr=is_valid_uuid4(REQUEST_ID),
            msg=f'Expected the test "{HEADER_NAME_KEY}" Header to be formatted as a invalid UUID version 4 token.',
        )

        _, _, headers = await self._get_response(
            url=self.TEST_SERVICE_URL,
            headers=[
                # Send an invalid UUID version 4 along with the request, to ensure the response will contain a new,
                # valid UUID version 4 ID issued by the Service:
                (str.encode(HEADER_NAME_KEY.lower()), str.encode(REQUEST_ID)),
            ],
        )

        self.assertIn(member=HEADER_NAME_KEY.lower(), container=headers)
        self.assertGreater(a=len(headers[HEADER_NAME_KEY.lower()]), b=0)
        self.assertTrue(
            expr=is_valid_uuid4(headers[HEADER_NAME_KEY.lower()]),
            msg=f'Expected the "{HEADER_NAME_KEY}" Header to be formatted as a valid UUID version 4 token.',
        )
        self.assertNotEqual(first=headers[HEADER_NAME_KEY.lower()], second=REQUEST_ID)

    async def test_reading_correlation_id_from_request_is_possible_from_endpoints(self) -> None:
        """Confirm that the Correlation ID sent from clients can be read from server-side endpoints."""
        HEADER_NAME_KEY = "X-Correlation-ID"
        REQUEST_ID = "d4b15197780949aa8e2de85a9538c143"
        TEST_SERVICE_READING_CORRELATION_ID = "/test-receiving-correlation-id"

        router = ServiceAPIRouter()

        @router.get(path=TEST_SERVICE_READING_CORRELATION_ID)
        async def lorem_ipsum(request: Request, x_request_id=Header()) -> Dict[str, Any]:
            # Confirm that the Correlation ID sent from clients can be read either from the `request.headers`
            # dictionary, or directly from the `x_request_id` HTTP Header:
            self.assertIn(member=HEADER_NAME_KEY.lower(), container=request.headers)
            self.assertEqual(first=request.headers[HEADER_NAME_KEY.lower()], second=REQUEST_ID)
            self.assertEqual(first=x_request_id, second=REQUEST_ID)
            return {"success": True}

        register_router(router=router)

        _, _, headers = await self._get_response(
            url=TEST_SERVICE_READING_CORRELATION_ID,
            headers=[
                (str.encode(HEADER_NAME_KEY.lower()), str.encode(REQUEST_ID)),
            ],
        )

        self.assertIn(member=HEADER_NAME_KEY.lower(), container=headers)
        self.assertEqual(first=headers[HEADER_NAME_KEY.lower()], second=REQUEST_ID)

        deregister_router(router=router)

    async def test_http_500_errors_contain_correlation_ids(self) -> None:
        """
        Validate that endpoint exceptions resulting in HTTP `500` errors return Correlation IDs along with their
        responses.
        """
        HEADER_NAME_KEY = "X-Correlation-ID"
        TEST_SERVICE_ERROR_URL = "/test/error"
        TEST_SERVICE_ERROR_MESSAGE = "Ooops!"

        for ExceptionClass in [HTTPException, KitServicesBaseException]:
            with self.subTest(ExceptionClass=ExceptionClass):
                router = ServiceAPIRouter()

                @router.get(path=TEST_SERVICE_ERROR_URL)
                async def lorem_ipsum(request: Request) -> Dict[str, Any]:
                    raise ExceptionClass(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=TEST_SERVICE_ERROR_MESSAGE)

                register_router(router=router)

                body, status_code, headers = await self._get_response(url=TEST_SERVICE_ERROR_URL)

                self.assertEqual(first=body, second={"detail": TEST_SERVICE_ERROR_MESSAGE})
                self.assertEqual(first=status_code, second=HTTP_500_INTERNAL_SERVER_ERROR)
                self.assertIsNotNone(obj=headers)
                self.assertIn(member=HEADER_NAME_KEY.lower(), container=headers)
                self.assertGreater(a=len(headers[HEADER_NAME_KEY.lower()]), b=0)
                self.assertTrue(
                    expr=is_valid_uuid4(headers[HEADER_NAME_KEY.lower()]),
                    msg=f'Expected the "{HEADER_NAME_KEY}" Header to be formatted as a valid UUID version 4 token.',
                )

                deregister_router(router=router)

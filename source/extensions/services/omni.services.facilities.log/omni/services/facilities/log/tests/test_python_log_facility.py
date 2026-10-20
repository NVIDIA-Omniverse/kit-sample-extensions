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
import os
from logging import Logger
from typing import Any, Dict, List, Optional, Tuple
from unittest import skip

import carb
import omni.kit.app
from omni.kit.test import AsyncTestCase
from omni.services.core.main import deregister_router, get_app, register_router
from omni.services.core.requests import get_correlation_id
from omni.services.core.routers import ServiceAPIRouter
from omni.services.facilities.log import PythonLogFacility


class PythonLogFacilityTestCase(AsyncTestCase):
    """Test cases for the Python log Facility."""

    INCLUDE_CORRELATION_ID_IF_AVAILABLE_SETTINGS_PATH = (
        "/exts/omni.services.facilities.log/includeCorrelationIdIfAvailable"
    )
    """Path of the Carbonite setting dictating whether Correlation IDs should be included in logs, if available."""

    async def setUp(self):
        super().setUp()

        # Configure the appropriate verbosity of the log, only for this test case (in order to avoid having the logs
        # being too verbose for the other tests present in this extension, and making it difficult to retrieve
        # information from the log during development):
        settings = carb.settings.get_settings_interface()
        self._original_include_correlation_id_if_available = settings.get_as_bool(
            self.INCLUDE_CORRELATION_ID_IF_AVAILABLE_SETTINGS_PATH
        )
        self._original_log_level_verbosity = settings.get_as_string("/log/level")
        self._original_log_output_stream_level_verbosity = settings.get_as_string("/log/outputStreamLevel")
        settings.set("/log/level", "verbose")
        settings.set("/log/outputStreamLevel", "verbose")

        self._log_data = None
        self._log_facility = PythonLogFacility(logger_name=__name__)

        def _on_log_event(event) -> None:
            self._log_data = event

        self._log_stream = omni.kit.app.get_app().get_log_event_stream()
        self._log_subscription = self._log_stream.create_subscription_to_pop(
            _on_log_event, name="Test log event stream"
        )

    async def tearDown(self):
        self._log_subscription = None
        self._log_stream = None

        # Restore the original verbosity of the log, in order to let configuration options dictate the behavior of the
        # logs for any potential subsequent tests included with the extension:
        settings = carb.settings.get_settings_interface()
        settings.set(
            self.INCLUDE_CORRELATION_ID_IF_AVAILABLE_SETTINGS_PATH, self._original_include_correlation_id_if_available
        )
        settings.set("/log/level", self._original_log_level_verbosity)
        settings.set("/log/outputStreamLevel", self._original_log_output_stream_level_verbosity)

        super().tearDown()

    @property
    def filename(self) -> str:
        """
        Return the name of the current Python file (including the extension).

        Args:
            None

        Returns:
            str: The name of the current Python file (including the extension).

        """
        return os.path.basename(__file__)

    def _get_correlation_id_header_key(self) -> str:
        """
        Utility method to return the name of the key used to identifiy the Correlation ID of a request in the Headers of
        a response from Service framework.

        Args:
            None

        Returns:
            The name of the key used to identifiy the Correlation ID of a request in the Headers of a response from
            Service framework.

        """
        settings = carb.settings.get_settings_interface()
        correlation_id_header_key = settings.get_as_string("/exts/omni.services.core/correlation_id/header_name")
        return correlation_id_header_key.lower()

    def include_correlation_id_if_available(self, enable: bool) -> None:
        """
        Utility to drive whether Correlation IDs should be included in log entries, if they are available.

        Args:
            enable (bool): Flag indicating whether Correlation IDs should be included in log entries.

        Returns:
            None

        """
        settings = carb.settings.get_settings_interface()
        settings.set(self.INCLUDE_CORRELATION_ID_IF_AVAILABLE_SETTINGS_PATH, enable)

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

    async def test_default_log_facility_settings_values(self) -> None:
        """Validate the default values of the Carbonite settings for the `PythonLogFacility` configuration."""
        self.assertTrue(
            expr=self._original_include_correlation_id_if_available,
            msg="Expected the original value of the flag dictating whether to include Correlation IDs in logs to be `True`.",
        )

    async def test_log_facility_can_provide_access_to_the_logger_instance(self) -> None:
        """Validate that the `PythonLogFacility` provides access to the underlying Python logger instance."""
        logger = self._log_facility.get_logger()

        self.assertIsInstance(obj=logger, cls=Logger)

    @skip("`carb.logging.LEVEL_VERBOSE` does not generate stream events")
    async def test_log_facility_can_record_info_message(self) -> None:
        """Validate that the `PythonLogFacility` can record `verbose` messages."""
        self._log_facility.verbose("VERBOSE MESSAGE")
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(first=self._log_data.payload["level"], second=-1)

    @skip("`carb.logging.LEVEL_INFO` does not generate stream events")
    async def test_log_facility_can_record_info_message(self) -> None:
        """Validate that the `PythonLogFacility` can record `info` messages."""
        self._log_facility.info("INFO MESSAGE")
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(first=self._log_data.payload["level"], second=-1)

    async def test_log_facility_can_record_warning_message(self) -> None:
        """Validate that the `PythonLogFacility` can record `warning` messages."""
        self._log_facility.warning("WARNING MESSAGE")
        await omni.kit.app.get_app().next_update_async()

        self.assertIsNotNone(obj=self._log_data.payload)
        self.assertIn(member="level", container=self._log_data.payload)
        self.assertEqual(first=self._log_data.payload["level"], second=0)

    async def test_log_facility_can_record_error_message(self) -> None:
        """Validate that the `PythonLogFacility` can record `error` messages."""
        self._log_facility.error("ERROR MESSAGE")
        await omni.kit.app.get_app().next_update_async()

        self.assertIsNotNone(obj=self._log_data.payload)
        self.assertIn(member="source", container=self._log_data.payload)
        self.assertIn(member="level", container=self._log_data.payload)
        self.assertIn(member="filename", container=self._log_data.payload)
        self.assertIn(member="functionName", container=self._log_data.payload)
        self.assertIn(member="lineNumber", container=self._log_data.payload)
        self.assertIn(member="message", container=self._log_data.payload)
        self.assertEqual(first=self._log_data.payload["source"], second=__name__)
        self.assertEqual(first=self._log_data.payload["level"], second=1)
        self.assertEqual(first=self._log_data.payload["filename"], second=self.filename)
        self.assertEqual(first=self._log_data.payload["message"], second="ERROR MESSAGE")

    async def test_log_facility_can_record_fatal_message(self) -> None:
        """Validate that the `PythonLogFacility` can record `fatal` messages."""
        self._log_facility.fatal("ERROR MESSAGE")
        await omni.kit.app.get_app().next_update_async()

        self.assertIsNotNone(obj=self._log_data.payload)
        self.assertIn(member="source", container=self._log_data.payload)
        self.assertIn(member="level", container=self._log_data.payload)
        self.assertIn(member="filename", container=self._log_data.payload)
        self.assertIn(member="functionName", container=self._log_data.payload)
        self.assertIn(member="lineNumber", container=self._log_data.payload)
        self.assertIn(member="message", container=self._log_data.payload)
        self.assertEqual(first=self._log_data.payload["source"], second=__name__)
        self.assertEqual(first=self._log_data.payload["level"], second=2)
        self.assertEqual(first=self._log_data.payload["filename"], second=self.filename)
        self.assertEqual(first=self._log_data.payload["message"], second="ERROR MESSAGE")

    async def test_log_facility_from_a_service_endpoint_includes_correlation_id(self) -> None:
        """Validate that the `PythonLogFacility` can record proper information in the handler of a Service."""
        self.include_correlation_id_if_available(enable=True)

        router = ServiceAPIRouter()
        router.register_facility(name="logger", facility_inst=self._log_facility)

        @router.get(path="/test")
        async def test(logger: PythonLogFacility = router.get_facility(name="logger")):
            logger.error("ERROR MESSAGE")
            return {"sucess": True}

        register_router(router=router)

        _, _, headers = await self._get_response(url="/test")
        await omni.kit.app.get_app().next_update_async()

        # Ensure the log message that was recorded by the Service endpoint contained the appropriate information:
        self.assertIsNotNone(obj=self._log_data)
        self.assertIn(member="source", container=self._log_data.payload)
        self.assertIn(member="level", container=self._log_data.payload)
        self.assertIn(member="filename", container=self._log_data.payload)
        self.assertIn(member="functionName", container=self._log_data.payload)
        self.assertIn(member="lineNumber", container=self._log_data.payload)
        self.assertIn(member="message", container=self._log_data.payload)
        self.assertEqual(first=self._log_data.payload["source"], second=__name__)
        self.assertEqual(first=self._log_data.payload["level"], second=1)
        self.assertEqual(first=self._log_data.payload["filename"], second=self.filename)

        # Ensure the response contains a Correlation ID in its Header (if enabled):
        expected_correlation_id = get_correlation_id()
        if expected_correlation_id:
            correlation_id_header_name = self._get_correlation_id_header_key()
            self.assertIn(member=correlation_id_header_name, container=headers)

            # Ensure the Correlation ID is found in the message, as desired:
            self.assertEqual(
                first=f"[CorrelationID={expected_correlation_id}] ERROR MESSAGE",
                second=self._log_data.payload["message"],
            )

        deregister_router(router=router)

    async def test_log_facility_from_a_service_endpoint_does_not_include_correlation_id_if_not_desired(self) -> None:
        """Validate that the `PythonLogFacility` does not record Correlation IDs if not desired."""
        self.include_correlation_id_if_available(enable=False)

        router = ServiceAPIRouter()
        router.register_facility(name="logger", facility_inst=self._log_facility)

        @router.get(path="/test")
        async def test(logger: PythonLogFacility = router.get_facility(name="logger")):
            logger.error("ERROR MESSAGE")
            return {"sucess": True}

        register_router(router=router)

        _, _, headers = await self._get_response(url="/test")
        await omni.kit.app.get_app().next_update_async()

        # Ensure the response contains a Correlation ID in its Header (if enabled):
        expected_correlation_id = get_correlation_id()
        if expected_correlation_id is not None:
            correlation_id_header_name = self._get_correlation_id_header_key()
            self.assertIn(member=correlation_id_header_name, container=headers)

        # Ensure the log message that was recorded by the Service endpoint contained the appropriate information:
        self.assertIsNotNone(obj=self._log_data)
        self.assertIn(member="source", container=self._log_data.payload)
        self.assertIn(member="level", container=self._log_data.payload)
        self.assertIn(member="filename", container=self._log_data.payload)
        self.assertIn(member="functionName", container=self._log_data.payload)
        self.assertIn(member="lineNumber", container=self._log_data.payload)
        self.assertIn(member="message", container=self._log_data.payload)
        self.assertEqual(first=self._log_data.payload["source"], second=__name__)
        self.assertEqual(first=self._log_data.payload["level"], second=1)
        self.assertEqual(first=self._log_data.payload["filename"], second=self.filename)

        # Ensure the Correlation ID is not found in the message, as desired:
        self.assertEqual(first="ERROR MESSAGE", second=self._log_data.payload["message"])

        deregister_router(router=router)

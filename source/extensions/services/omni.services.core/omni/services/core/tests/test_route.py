# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for encoders of the Kit microservices framework."""

import gzip
import json
import typing
import zlib
from unittest.mock import patch

import carb
import fastapi
from omni.services.core import exceptions, main, routers
from omni.services.core._route import _CompressedRequest

from . import base


class EncodingTest(base.BaseServiceTest):

    def tearDown(self):
        # Remove temporary routes added for the purposes of this test case after each test:
        self._remove_route_patterns(["*/gzip-test*"])

        super().tearDown()

    async def _post_request_async(self, url: str, data: typing.Any, content_encoding: str = "gzip") -> list:
        result = []
        scope = {
            "type": "http",  # Change this so it can be amqp etc. as well, will require Router change.
            "method": "POST",
            "path": url,
            "query_string": b"",
            "headers": [(b"content-type", b"application/json"), (b"content-encoding", str.encode(content_encoding))],
            "body": gzip.compress(json.dumps(data).encode("ascii")),
        }

        async def _receive():
            body = bytes(scope["body"], "ascii") if not isinstance(scope["body"], bytes) else scope["body"]
            return {"type": "http.request", "body": body}

        async def _send(result_data):
            result.append(result_data)

        await main.get_app()(scope, _receive, _send)

        return_value = None
        return_code = 200
        for entry in result:
            if entry["type"] == "http.response.body":
                return_value = json.loads(entry["body"].decode("utf-8"))
            elif entry["type"] == "http.response.start":
                return_code = entry["status"]

        return return_value, return_code

    async def test_post_gzip_data_norouter(self):
        async def foo(data=fastapi.Body(...)):
            return data

        main.register_endpoint("post", "/gzip-test", foo)

        data = {"foo": "bar"}
        result, status = await self._post_request_async("/gzip-test", data)
        self.assertEqual(result, data)
        self.assertEqual(status, 200)

    async def test_post_gzip_data_router(self):
        router = routers.ServiceAPIRouter()

        @router.post("/gzip-test-router")
        async def foo(data=fastapi.Body(...)):
            return data

        main.register_router(router)

        data = {"foo": "bar"}
        result, status = await self._post_request_async("/gzip-test-router", data)
        self.assertEqual(result, data)
        self.assertEqual(status, 200)

    async def test_post_gzip_data_router_without_matching_encoding_logs_an_error(self) -> None:
        """Validate that a compressed route without supported encoder prints an error to the log."""
        router = routers.ServiceAPIRouter()

        TEST_ENDPOINT_URL = "/gzip-test-compressed-route"
        TEST_CONTENT_ENCODING = "unsupported"

        @router.post(path=TEST_ENDPOINT_URL)
        async def lorem_ipsum(data=fastapi.Body(...)):
            return {"success": True}  # pragma: no cover

        main.register_router(router=router)

        with patch.object(target=carb, attribute="log_error") as mock_carb_log_error:
            _, _ = await self._post_request_async(
                url=TEST_ENDPOINT_URL, data={}, content_encoding=TEST_CONTENT_ENCODING
            )

        mock_carb_log_error.assert_called_once_with(f"{TEST_CONTENT_ENCODING} is not a registered decoder")

    async def test_deregistering_websocket_router_succeeds(self):
        websocket_router = routers.ServiceAPIRouter()

        @websocket_router.websocket("/test-websocket-router")
        async def lorem_ipsum() -> None:
            return {}  # pragma: no cover

        main.register_router(router=websocket_router)

        # Deregister the WebSocket router to ensure no exception is raised when attempting to list `methods` of a
        # router, which are not present on an `APIWebSocketRoute`:
        main.deregister_router(router=websocket_router)

    async def test_register_facility_registration(self):
        class FacilityStub:
            pass  # pragma: no cover

        facility_stub = FacilityStub()

        router = routers.ServiceAPIRouter()
        router.register_facility("stub", facility_stub)

        # We do what fastapi does and call the dependency.
        router.get_facility("stub").dependency()

        # We should fail for a facility that doesn't exist.
        with self.assertRaises(exceptions.ServiceUnavailableError):
            router.get_facility("foo").dependency()

    # ------------------------------------------------------------------
    # Regression tests for OMPE-91964 / NVBug 6118403:
    # `_CompressedRequest.body()` must process every Content-Encoding
    # value (no early `break`) and must surface unknown encoders instead
    # of silently returning partially-decoded bytes.
    #
    # These tests drive `_CompressedRequest.body()` directly on an ASGI
    # scope, matching the runtime probe captured in the bug ticket.
    # ------------------------------------------------------------------

    @staticmethod
    def _make_compressed_request(content_encodings: typing.List[str], body: bytes) -> _CompressedRequest:
        headers = [(b"content-type", b"application/octet-stream")]
        for encoding in content_encodings:
            headers.append((b"content-encoding", encoding.encode("ascii")))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 0),
        }

        sent = {"done": False}

        async def receive():
            if sent["done"]:
                return {"type": "http.disconnect"}
            sent["done"] = True
            return {"type": "http.request", "body": body, "more_body": False}

        return _CompressedRequest(scope, receive)

    async def test_body_chained_encodings_are_all_decoded(self) -> None:
        """Regression for OMPE-91964: with multiple `Content-Encoding` values, every
        layer must be decoded.

        The previous implementation broke out of the loop after the first
        successful decompress, so the body was returned with the inner
        encodings still in place.
        """
        plaintext = b"OMPE-91964 chained encoding regression payload"
        # Body was deflated, then gzipped. Content-Encoding lists encodings
        # outermost first ("gzip, deflate") -- decoding walks the list in order.
        body = gzip.compress(zlib.compress(plaintext))

        request = self._make_compressed_request(["gzip", "deflate"], body)
        decoded = await request.body()

        self.assertEqual(decoded, plaintext)

    async def test_body_unknown_trailing_encoder_propagates_keyerror(self) -> None:
        """Regression for OMPE-91964: an unknown encoder past index 0 must not
        be silently ignored.

        With the previous code, the early `break` after the first successful
        decompress made the `except KeyError` handler unreachable for any
        trailing encoder. The function returned bytes that still required a
        further decode step, and no error was raised or logged.
        """
        plaintext = b"OMPE-91964 unknown trailing encoder payload"
        body = gzip.compress(plaintext)

        request = self._make_compressed_request(["gzip", "not-a-real-encoder"], body)

        with patch.object(target=carb, attribute="log_error") as mock_carb_log_error:
            with self.assertRaises(KeyError):
                await request.body()

        mock_carb_log_error.assert_called_once_with("not-a-real-encoder is not a registered decoder")

    async def test_body_single_encoding_still_decodes(self) -> None:
        """Smoke test: dropping the `break` must not regress the single-encoding
        happy path."""
        plaintext = b"OMPE-91964 single-encoding smoke test payload"
        body = gzip.compress(plaintext)

        request = self._make_compressed_request(["gzip"], body)
        decoded = await request.body()

        self.assertEqual(decoded, plaintext)

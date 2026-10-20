# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
import socket

import aiohttp
import omni.services.client as _client
from fastapi import Body, FastAPI
from omni.kit.test import AsyncTestCase
from omni.services.transport.client.base import exceptions
from omni.services.transport.client.base.exceptions import BaseServiceError
from starlette.status import HTTP_405_METHOD_NOT_ALLOWED


def _free_local_port() -> int:
    """Return a TCP port that is free on 127.0.0.1, where uvicorn binds the test servers.

    A fixed port (formerly 8000) fails whenever another local service already listens on it: uvicorn then
    logs "[Errno 98] address already in use" and every request reaches the other service (404 Not Found).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class BaseaioHTTPTest(AsyncTestCase):

    SERVER_PORT = _free_local_port()

    async def _start_server(self, app: FastAPI):
        from uvicorn import Config, Server

        config = Config(app, loop="asyncio", log_level="error", port=self.SERVER_PORT)
        server = Server(config=config)
        asyncio.ensure_future(server.serve())
        # Release the loop so the server can start
        await asyncio.sleep(0.1)
        return server

    async def tearDown(self):
        self._server.should_exit = True
        # Release the loop so the server can stop
        await asyncio.sleep(1.0)

        super().tearDown()


class TestaioHTTPClient_Get(BaseaioHTTPTest):

    async def setUp(self):
        super().setUp()

        app = FastAPI()

        async def ping():
            return "pong"

        async def ping_with_value(value: str):
            return value

        async def ping_with_multiple_value(value_a: str, value_b: str):
            return [value_a, value_b]

        app.get("/ping")(ping)
        app.get("/query/params")(ping_with_value)
        app.get("/query/multiparams")(ping_with_multiple_value)
        app.get("/foo/ping")(ping)
        app.get("/foo/test-underscores")(ping)

        async def send(arg):
            return arg

        async def send_with_arg(arg: str, value: str):
            return [arg, value]

        async def sendblob():
            return {"foo": "bar"}

        app.get("/sendblob")(sendblob)
        app.get("/send/{arg}")(send)
        app.get("/foo/send/{arg}")(send)
        app.get("/params/{arg}")(send_with_arg)

        self._server = await self._start_server(app)
        self._client = _client.AsyncClient(f"http://localhost:{self.SERVER_PORT}")

    async def test_simple_function(self):
        assert await self._client.ping() == "pong"

    async def test_simple_function_with_param(self):
        assert await self._client.query.params(value="bar") == "bar"

    async def test_simple_function_with_multiple_params(self):
        assert await self._client.query.multiparams(value_a="bar", value_b="baz") == ["bar", "baz"]

    async def test_nested_function(self):
        assert await self._client.foo.ping() == "pong"

    async def test_function_with_params(self):
        assert await self._client.send.get("data") == "data"

    async def test_nested_function_with_params(self):
        assert await self._client.foo.send("data") == "data"

    async def test_method_appended(self):
        assert await self._client.foo.send.get("data") == "data"

    async def test_simple_function_with_args_and_params(self):
        assert await self._client.params.get("data", value="bar") == ["data", "bar"]

    async def test_underscores_to_hyphen(self):
        self.assertEqual(await self._client.foo.test_underscores.get(), "pong")

    async def test_http_status(self):
        self.assertEqual(await self._client.sendblob.get(), {"foo": "bar"})

    async def test_no_raise_on_status(self):
        client = _client.AsyncClient(f"http://localhost:{self.SERVER_PORT}", raise_for_status=False)
        self.assertIn("__http_status__", await client.sendblob.get())


class TestaioHTTPClient_Post(BaseaioHTTPTest):

    async def setUp(self):
        super().setUp()

        app = FastAPI()

        async def ping():
            return "pong"

        app.post("/ping")(ping)
        app.post("/foo/ping")(ping)

        # Embed here is critical for kwargs to work and should be hidden from regular users.
        async def send(arg: str = Body("", embed=True)):
            return arg

        app.post("/send")(send)
        app.post("/foo/send")(send)

        async def sum_values(a: int, b: int = Body(0, embed=True)):
            return a + b

        app.post("/sum/{a}")(sum_values)

        async def multiply(a: int = Body(0, embed=True), b: int = Body(0, embed=True)):
            return a * b

        app.post("/multiply")(multiply)

        async def sendblob():
            return {"foo": "bar"}

        app.post("/sendblob")(sendblob)

        self._server = await self._start_server(app)
        self._client = _client.AsyncClient(f"http://localhost:{self.SERVER_PORT}")

    async def test_simple_function(self):
        assert await self._client.ping() == "pong"

    async def test_nested_function(self):
        assert await self._client.foo.ping() == "pong"

    async def test_function_with_params(self):
        assert await self._client.send(arg="data") == "data"

    async def test_nested_function_with_params(self):
        assert await self._client.foo.send(arg="data") == "data"

    async def test_mixed_arg_kwarg_arg_only(self):
        assert await self._client.sum(10) == 10

    async def test_mixed_arg_kwarg(self):
        assert await self._client.sum(10, b=20) == 30

    async def test_mixed_kwarg_only_should_fail(self):
        with self.assertRaises(exceptions.ServiceNotFoundError):
            await self._client.sum(b=20)

    async def test_kwargs_only(self):
        assert await self._client.multiply(a=20, b=1) == 20

    async def test_http_status(self):
        self.assertEqual(await self._client.sendblob(), {"foo": "bar"})

    async def test_no_raise_on_status(self):
        client = _client.AsyncClient(f"http://localhost:{self.SERVER_PORT}", raise_for_status=False)
        self.assertIn("__http_status__", await client.sendblob())


class TestaioHTTPClient_persistent_connection(BaseaioHTTPTest):

    async def setUp(self):
        super().setUp()

        app = FastAPI()

        async def ping():
            return "pong"

        app.get("/ping")(ping)

        self._server = await self._start_server(app)
        self._client = _client.AsyncClient(f"http://localhost:{self.SERVER_PORT}", persist_connections=True)

    async def test_session_is_created(self):
        self.assertTrue(isinstance(self._client._transport._session, aiohttp.ClientSession))
        await self._client.stop_async()

    async def test_session_closes_cleanly_async(self):
        await self._client.stop_async()
        self.assertTrue(self._client._transport.closed)

    def test_session_closes_cleanly_sync(self):
        self._client.stop()
        self.assertTrue(self._client._transport.closed)

    async def test_session_closes_cleanly_async_after_use(self):
        assert await self._client.ping() == "pong"
        await self._client.stop_async()
        self.assertTrue(self._client._transport.closed)

    async def test_session_closes_cleanly_after_use(self):
        assert await self._client.ping() == "pong"
        self._client.stop()
        self.assertTrue(self._client._transport.closed)


class AsyncClientArgumentProcessingTestCase(BaseaioHTTPTest):
    """Test case for handling arguments provided to the AsyncClient constructs."""

    async def setUp(self):
        super().setUp()

        app = FastAPI()

        async def ping():
            return "pong"

        app.get("/ping")(ping)

        self._server = await self._start_server(app)
        self._client = _client.AsyncClient(f"http://localhost:{self.SERVER_PORT}")

    async def test_standard_request_completes_successfully(self) -> None:
        """Validate that a standard request succeeds as expected."""
        response = await self._client.ping.get()

        self.assertEqual(first=response, second="pong")

    async def test_case_insensitive_methods_are_supported(self) -> None:
        """Validate that a request using a mixed-case supported methods completes successfully."""
        response = await self._client.ping(__method__="GeT")

        self.assertEqual(first=response, second="pong")

    async def test_invalid_methods_raise_keyerror_exception(self) -> None:
        """Validate that a request using an unsupported method raises a `KeyError` exception."""
        with self.assertRaises(expected_exception=KeyError) as exc:
            _ = await self._client.ping(__method__="!!!invalid-method!!!")

        self.assertEqual(
            first=str(exc.exception),
            # Work around `KeyError` adding single-quote characters and additional character escaping when performing
            # `str(exc.exception)`:
            second=f"'Method \"!!!invalid-method!!!\" not found amongst the supported HTTP Transport methods [\\'get\\', \\'post\\', \\'put\\', \\'delete\\', \\'patch\\'] to reach URI \"http://localhost:{self.SERVER_PORT}/ping\".'",
        )

    async def test_request_using_unsupported_method_to_proper_uri_provides_information(self) -> None:
        """
        Validate that a request against a valid Service URI but using an incorrect method provides Users with some
        background information.
        """
        with self.assertRaises(expected_exception=BaseServiceError) as exc:
            _ = await self._client.ping(__method__="post", raise_for_status=True)
        expected_exception_str = str(exc.exception)
        error_first_part = f"{HTTP_405_METHOD_NOT_ALLOWED}, message='Method Not Allowed'"
        error_url = f"http://localhost:{self.SERVER_PORT}/ping"
        self.assertTrue(expected_exception_str.startswith(error_first_part))
        self.assertTrue(expected_exception_str.find(error_url) != -1)

# SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import fastapi
import omni.kit.test
import omni.services.client as _client
import omni.services.core
from fastapi import staticfiles
from omni.services.client.transports import local
from omni.services.transport.client.base import consumer as base
from omni.services.transport.client.base import exceptions


class Test(omni.kit.test.AsyncTestCase):
    async def test_local_transport(self):
        client = _client.AsyncClient("local://")
        assert isinstance(client._transport, local.Transport)

    async def test_register_transport(self):
        class Foo(base.BaseConsumer):
            pass

        _client.register("foo", Foo)
        available_transports = _client.get_available_transports()
        self.assertIn("foo", available_transports)
        self.assertEqual(available_transports["foo"], Foo)

    async def test_local_transport_no_app(self):
        client = _client.AsyncClient("local://")
        self.assertEqual(client._transport._app, omni.services.core.main.get_app())

    async def test_raises_for_transport_not_found(self):
        with self.assertRaises(_client.TransportNotFoundError):
            _client.AsyncClient("unregistred-transport://foo")


class TestLocalClient_Get(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()

        async def ping():
            return "pong"

        app.get("/ping")(ping)
        app.get("/foo/ping")(ping)

        async def send(arg):
            return arg

        app.get("/send/{arg}")(send)
        app.get("/foo/send/{arg}")(send)

        self._client = _client.AsyncClient("local://", app=app)

    async def test_simple_function(self):
        self.assertEqual(await self._client.ping(), "pong")

    async def test_nested_function(self):
        self.assertEqual(await self._client.foo.ping(), "pong")

    async def test_function_with_params(self):
        self.assertEqual(await self._client.send("data"), "data")

    async def test_nested_function_with_params(self):
        self.assertEqual(await self._client.foo.send("data"), "data")

    async def test_method_appended(self):
        self.assertEqual(await self._client.foo.send.get("data"), "data")


class TestLocalClient_PathUrl_Get(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()

        async def ping():
            return "pong"

        app.get("/bar/ping")(ping)
        app.get("/bar/foo/ping")(ping)

        async def send(arg):
            return arg

        app.get("/bar/send/{arg}")(send)
        app.get("/bar/foo/send/{arg}")(send)

        self._client = _client.AsyncClient("local:///bar", app=app)

    async def test_simple_function(self):
        self.assertEqual(await self._client.ping(), "pong")

    async def test_nested_function(self):
        self.assertEqual(await self._client.foo.ping(), "pong")

    async def test_function_with_params(self):
        self.assertEqual(await self._client.send("data"), "data")

    async def test_nested_function_with_params(self):
        self.assertEqual(await self._client.foo.send("data"), "data")

    async def test_method_appended(self):
        self.assertEqual(await self._client.foo.send.get("data"), "data")


class TestLocalClient_Post(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()

        async def ping():
            return "pong"

        app.post("/ping")(ping)
        app.post("/foo/ping")(ping)

        # Embed here is critical for kwargs to work and should be hidden from regular users.
        async def send(arg: str = fastapi.Body("", embed=True)):
            return arg

        app.post("/send")(send)
        app.post("/foo/send")(send)

        async def sum_values(a: int, b: int = fastapi.Body(0, embed=True)):
            return a + b

        app.post("/sum/{a}")(sum_values)

        self._client = _client.AsyncClient("local://", app=app)

    async def test_simple_function(self):
        self.assertEqual(await self._client.ping(), "pong")

    async def test_nested_function(self):
        self.assertEqual(await self._client.foo.ping(), "pong")

    async def test_function_with_params(self):
        self.assertEqual(await self._client.send(arg="data"), "data")

    async def test_nested_function_with_params(self):
        self.assertEqual(await self._client.foo.send(arg="data"), "data")

    async def test_mixed_arg_kwarg_arg_only(self):
        self.assertEqual(await self._client.sum(10), 10)

    async def test_mixed_arg_kwarg(self):
        self.assertEqual(await self._client.sum(10, b=20), 30)

    async def test_mixed_kwarg_only_should_fail(self):
        with self.assertRaises(exceptions.ServiceNotFoundError):
            await self._client.sum(b=20)


class TestLocalClient_IncludedRouter(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()
        router = fastapi.APIRouter(prefix="/included")

        @router.get("/ping")
        async def ping():
            return "pong"

        @router.post("/send")
        async def send(arg: str = fastapi.Body("", embed=True)):
            return arg

        app.include_router(router)
        nested_router = fastapi.APIRouter(prefix="/nested")
        nested_router.include_router(router)
        app.include_router(nested_router)

        self._client = _client.AsyncClient("local://", app=app)

    async def test_get(self):
        self.assertEqual(await self._client.included.ping(), "pong")

    async def test_post(self):
        self.assertEqual(await self._client.included.send(arg="data"), "data")

    async def test_nested_get(self):
        self.assertEqual(await self._client.nested.included.ping(), "pong")


class TestLocalClient_Headers(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()

        async def ping(x_my_header: str = fastapi.Header(...)):
            return x_my_header

        app.get("/get/ping")(ping)
        app.post("/post/ping")(ping)
        self._client = _client.AsyncClient("local://", app=app)

    async def test_header_post(self):
        self.assertEqual(await self._client.post.ping.post(__headers__={"X-My-Header": "pong"}), "pong")

    async def test_header_get(self):
        self.assertEqual(await self._client.get.ping.get(__headers__={"X-My-Header": "pong"}), "pong")


class TestLocalClient_DifferentMounts(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()

        app.mount("/get/static", staticfiles.StaticFiles())
        app.mount("/post/static", staticfiles.StaticFiles())
        app.mount("/a/static", staticfiles.StaticFiles())

        async def ping():
            return "pong"

        app.get("/get/ping")(ping)
        app.post("/post/ping")(ping)
        self._client = _client.AsyncClient("local://", app=app)

    async def test_header_post(self):
        self.assertEqual(await self._client.post.ping.post(), "pong")

    async def test_header_get(self):
        self.assertEqual(await self._client.get.ping.get(), "pong")


class TestLocalClient_MixedPaths(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        app = fastapi.FastAPI()

        async def get_test():
            return "get"

        async def post_test():
            return "post"

        async def delete_test():
            return "delete"

        app.get("/test")(get_test)
        app.post("/test")(post_test)
        app.delete("/test")(delete_test)

        self._client = _client.AsyncClient("local://", app=app)

    async def test_get_path(self):
        self.assertEqual(await self._client.test.get(), "get")

    async def test_post_path(self):
        self.assertEqual(await self._client.test.post(), "post")

    async def test_delete_path(self):
        self.assertEqual(await self._client.test.delete(), "delete")

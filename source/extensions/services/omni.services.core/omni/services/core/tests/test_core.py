# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for the core interface of the Kit microservices framework."""

import os
from pathlib import Path
from typing import List

import carb
import fastapi
import omni.services.core.main as main
import starlette
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from omni.services.facilities.base import Facility

from ..routers import ServiceAPIRouter
from . import base


class TestServicesCore(base.BaseServiceTest):

    def tearDown(self):
        # Remove temporary routes added for the purposes of this test case after each test:
        self._remove_route_patterns(["*/foo*", "*/bar*"])

        super().tearDown()

    async def test_register_get_endpoint(self):
        async def foo():
            return "bar"

        main.register_endpoint("get", "/foo", foo)
        result, status = await self._get_request_async("/foo")
        self.assertEqual(status, 200)
        self.assertEqual(result, "bar")

    async def test_register_post_endpoint(self):
        async def foo():
            return "bar"

        main.register_endpoint("post", "/foo", foo)
        result, status = await self._post_request_async(url="/foo", data={})
        self.assertEqual(status, 200)
        self.assertEqual(result, "bar")

    async def test_registered_router_accepts_json_without_content_type_by_default(self):
        router = ServiceAPIRouter()

        @router.post("/foo")
        async def foo(payload: dict):
            return payload

        main.register_router(router)
        result, status = await self._post_request_async(url="/foo", data={"bar": "baz"}, headers=[])
        self.assertEqual(status, 200)
        self.assertEqual(result, {"bar": "baz"})

    async def test_strict_content_type_setting_controls_registered_router(self):
        settings = carb.settings.get_settings_interface()
        setting_path = "/exts/omni.services.core/strict_content_type"
        original_value = settings.get(setting_path)
        settings.set(setting_path, True)

        try:
            service = main.ServicesCoreExtension()
            router = ServiceAPIRouter()

            @router.post("/foo")
            async def foo(payload: dict):
                return payload

            service.register_router(router)

            headerless_result, headerless_status = await self._post_request_async(
                url="/foo", data={"bar": "baz"}, headers=[], app=service._app
            )
            if hasattr(service._app.router, "strict_content_type"):
                self.assertTrue(service._app.router.strict_content_type)
                self.assertEqual(headerless_status, 422)
            else:
                # FastAPI versions before 0.132 retain unknown application options without enforcing them.
                self.assertTrue(service._app.extra["strict_content_type"])
                self.assertEqual(headerless_status, 200)
                self.assertEqual(headerless_result, {"bar": "baz"})

            result, status = await self._post_request_async(url="/foo", data={"bar": "baz"}, app=service._app)
            self.assertEqual(status, 200)
            self.assertEqual(result, {"bar": "baz"})
        finally:
            settings.set(setting_path, original_value)

    async def test_register_router_no_prefix(self):
        router = fastapi.APIRouter()

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router)
        result, status = await self._get_request_async("/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "foo")

    async def test_register_router_prefix(self):
        router = fastapi.APIRouter()

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router, prefix="/test")
        result, status = await self._get_request_async("/test/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "foo")

    async def test_register_router_main_dotted_prefix(self):
        router = fastapi.APIRouter()

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router, prefix="test.baz")
        result, status = await self._get_request_async("/test/baz/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "foo")

    async def test_register_router_with_prefix(self):
        router = ServiceAPIRouter(prefix="/test")

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router)
        result, status = await self._get_request_async("/test/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "foo")

    async def test_deregister_router_with_prefix(self):
        """Validate that deregistering routers with a given prefix succeeds."""
        TEST_ROUTER_PREFIX = "/test"

        router = ServiceAPIRouter(prefix=TEST_ROUTER_PREFIX)

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router=router)
        result, status = await self._get_request_async("/test/bar")
        self.assertEqual(first=status, second=200)
        self.assertEqual(first=result, second="foo")

        main.deregister_router(router=router, prefix=TEST_ROUTER_PREFIX.replace("/", ""))

    async def test_register_router_with_dotted_prefix(self):
        router = ServiceAPIRouter(prefix="test.baz")

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router)
        result, status = await self._get_request_async("/test/baz/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "foo")

    async def test_default_status_response(self) -> None:
        """Validate that the response from the `/status` endpoint matches the expected data."""
        result, status = await self._get_request_async("/status")

        expected_response = await main._status()
        self.assertEqual(first=status, second=200)
        self.assertEqual(first=result, second=expected_response)
        self.assertIsInstance(obj=result, cls=str)

    async def test_register_router_with_bypassed_path(self):
        """Validate that registering a router with bypassed paths does not make the endpoint available."""
        router = ServiceAPIRouter()
        router._bypassed_paths = ["/path-a", "/path-b"]

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router=router, prefix="/test")
        result, status = await self._get_request_async("/test/bar")

        self.assertEqual(first=status, second=200)
        self.assertEqual(first=result, second="foo")

    async def test_router_with_list_param(self):
        router = ServiceAPIRouter(prefix="/test")

        @router.get("/bar")
        async def bar(test_param: List = fastapi.Query(default=None)):
            return test_param

        main.register_router(router)
        list_param = ["one", "2", "three"]
        result, status = await self._get_request_async("/test/bar", query_params={"test_param": list_param})
        self.assertEqual(status, 200)
        self.assertEqual(result, list_param)

    async def test_router_tags(self):
        router = ServiceAPIRouter(prefix="/foo", tags=["foo", "bar"])
        self.assertEqual(router.tags, ["foo", "bar"])

    async def test_register_facility(self) -> None:
        """Validate that registering a Facility increases the number of tracked Facility instances."""

        class TestFacility(Facility):
            pass

        test_facility = TestFacility()

        initial_facility_count = len(main._singleton._facilities)
        main.register_facility(facility=test_facility)
        final_facility_count = len(main._singleton._facilities)

        self.assertEqual(first=final_facility_count, second=initial_facility_count + 1)

    async def test_registering_a_middleware_after_application_start_raises_an_exception(self) -> None:
        """Validate that registering a Middleware after starting the application raises an Exception."""

        class TestMiddleware:
            pass  # pragma: no cover

        with self.assertRaises(expected_exception=RuntimeError) as exc:
            main.register_middleware(cls=TestMiddleware)

        self.assertGreater(a=len(exc.exception.args), b=0)
        self.assertEqual(first=exc.exception.args[0], second="Cannot add middleware after an application has started")

    async def test_registering_a_websocket_endpoint_does_not_raise_an_exception(self) -> None:
        """Validate that registering a WebSocket endpoint does not raise an Exception."""

        async def lorem_ipsum():
            return {"success": True}

        main.register_websocket_endpoint(url="/test-websocket-endpoint", func=lorem_ipsum)

        response, status = await self._get_request_async(url="/test-websocket-endpoint")

        self.assertIn(member="detail", container=response)
        self.assertEqual(first="Not Found", second=response["detail"])
        self.assertEqual(first=status, second=404)

    async def test_register_mount(self):
        static_files_directory = os.path.join(Path(__file__).parent.absolute(), "static-files")

        main.register_mount("/foo", StaticFiles(directory=static_files_directory))
        result, status = await self._get_request_async("/foo/bar.json")
        self.assertEqual(status, 200)
        self.assertEqual(result, {"baz": "qux"})

    async def test_register_mount_with_args(self):
        static_files_directory = os.path.join(Path(__file__).parent.absolute(), "static-files")

        main.register_mount("/foo", StaticFiles(directory=static_files_directory), name="foo")

        routes_found = []
        for route in main.get_app().routes:
            if isinstance(route, starlette.routing.Mount) and route.path == "/foo":
                routes_found.append(route)

        self.assertEqual(len(routes_found), 1)
        self.assertEqual(routes_found[0].name, "foo")
        self.assertEqual(routes_found[0].path, "/foo")

    async def test_mounting_html_redirects_to_index_file(self):
        static_files_directory = os.path.join(Path(__file__).parent.absolute(), "static-files")

        main.register_mount("/foo", StaticFiles(directory=static_files_directory, html=True))

        # Validate that a request for "/foo" receives a response for a 307 redirect to "/foo/":
        result, status = await self._get_request_async("/foo")
        self.assertEqual(status, 307)
        self.assertEqual(result, "")

        # Validate that a request for "/foo/" receives a response from the "index.html" file in the mounted directory:
        result, status = await self._get_request_async("/foo/")
        self.assertEqual(status, 200)
        self.assertIn("<h1>foo</h1>", result)

    async def test_mount_returns_404_for_missing_files(self):
        static_files_directory = os.path.join(Path(__file__).parent.absolute(), "static-files")

        main.register_mount("/foo", StaticFiles(directory=static_files_directory, html=True))
        result, status = await self._get_request_async("/foo/non-existing-file.mp4")
        self.assertEqual(status, 404)

    async def test_deregister_endpoint(self):
        async def foo():
            return "bar"

        main.register_endpoint("get", "/foo", foo)
        result, status = await self._get_request_async("/foo")
        self.assertEqual(status, 200)
        self.assertEqual(result, "bar")

        main.deregister_endpoint("get", "/foo")
        result, status = await self._get_request_async("/foo")
        self.assertEqual(status, 404)
        self.assertEqual(result, {"detail": "Not Found"})

    async def test_deregister_endpoint_with_arg(self):
        async def foo(arg):
            return arg

        url = "/foo/{arg}"

        main.register_endpoint("get", url, foo)
        result, status = await self._get_request_async("/foo/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "bar")

        main.deregister_endpoint("get", url)
        result, status = await self._get_request_async("/foo/bar")
        self.assertEqual(status, 404)

    async def test_deregister_endpoint_ignores_routes_without_path(self):
        async def foo():
            return "bar"

        class RouteWithoutPath:
            pass

        app = main.get_app()
        route_without_path = RouteWithoutPath()

        main.register_endpoint("get", "/foo", foo)
        app.routes.insert(0, route_without_path)
        try:
            main.deregister_endpoint("get", "/foo")
        finally:
            if route_without_path in app.routes:
                app.routes.remove(route_without_path)

        result, status = await self._get_request_async("/foo")
        self.assertEqual(status, 404)
        self.assertEqual(result, {"detail": "Not Found"})

    async def test_deregister_router(self):
        router = fastapi.APIRouter()
        prefix = "/test"

        @router.get("/bar")
        async def bar():
            return "foo"

        main.register_router(router, prefix=prefix)
        result, status = await self._get_request_async("/test/bar")
        self.assertEqual(status, 200)
        self.assertEqual(result, "foo")

        main.deregister_router(router, prefix=prefix)
        self.assertFalse(any(getattr(route, "original_router", None) is router for route in main.get_app().routes))
        result, status = await self._get_request_async("/test/bar")
        self.assertEqual(status, 404)

    def _create_included_router_route(self, router, prefix):
        class IncludeContext:
            pass

        class IncludedRouterRoute:
            pass

        include_context = IncludeContext()
        include_context.prefix = prefix
        included_router_route = IncludedRouterRoute()
        included_router_route.original_router = router
        included_router_route.include_context = include_context
        return included_router_route

    async def test_deregister_router_removes_included_router_route_without_path(self):
        router = fastapi.APIRouter()
        included_router_route = self._create_included_router_route(router, "/test")

        app = main.get_app()
        app.routes.insert(0, included_router_route)
        try:
            main.deregister_router(router, prefix="/test")
            self.assertNotIn(included_router_route, app.routes)
        finally:
            if included_router_route in app.routes:
                app.routes.remove(included_router_route)

    async def test_deregister_router_without_prefix_removes_all_included_router_routes(self):
        router = fastapi.APIRouter()
        included_router_routes = [
            self._create_included_router_route(router, "/test"),
            self._create_included_router_route(router, "/other"),
        ]

        app = main.get_app()
        app.routes[0:0] = included_router_routes
        try:
            main.deregister_router(router)
            for included_router_route in included_router_routes:
                self.assertNotIn(included_router_route, app.routes)
        finally:
            for included_router_route in included_router_routes:
                if included_router_route in app.routes:
                    app.routes.remove(included_router_route)

    async def test_deregister_mount(self):
        static_files_directory = os.path.join(Path(__file__).parent.absolute(), "static-files")

        main.register_mount("/foo", StaticFiles(directory=static_files_directory))
        result, status = await self._get_request_async("/foo/bar.json")
        self.assertEqual(status, 200)
        self.assertEqual(result, {"baz": "qux"})

        main.deregister_mount("/foo")
        result, status = await self._get_request_async("/foo")
        self.assertEqual(status, 404)
        self.assertEqual(result, {"detail": "Not Found"})

    async def test_set_description(self):
        main.set_metadata("foo", "bar", "123")

        self.assertEqual(main.get_app().title, "foo")
        self.assertEqual(main.get_app().description, "bar")
        self.assertEqual(main.get_app().version, "123")

    async def test_set_application_root_path(self) -> None:
        """Validate that setting the application's root path configures the application as expected."""
        TEST_ROOT_PATH = "/test-root-path"

        original_root_path = main.get_app().root_path
        main.set_metadata(title="foo", description="bar", version="123", root_path=TEST_ROOT_PATH)
        final_root_path = main.get_app().root_path

        self.assertEqual(first=final_root_path, second=TEST_ROOT_PATH)

        main.set_metadata(title="foo", description="bar", version="123", root_path=original_root_path)

    async def test_set_tag_metadata(self):
        tags_metadata = [{"name": "tag", "description": "tag_description"}]

        main.set_metadata("foo", "bar", "123", tags_metadata=tags_metadata)
        self.assertEqual(main.get_app().openapi_tags, tags_metadata)


class TestSetMetadataFastAPIOptions(base.BaseServiceTest):
    ROUTE_PREFIX = "/metadata-test"

    def setUp(self):
        super().setUp()
        app = main.get_app()
        self._original_title = app.title
        self._original_description = app.description
        self._original_version = app.version
        self._original_root_path = app.root_path
        self._original_docs_url = app.docs_url
        self._original_openapi_url = app.openapi_url
        self._original_redoc_url = app.redoc_url
        self._original_default_response_class = app.router.default_response_class

    def tearDown(self):
        main.set_metadata(
            title=self._original_title,
            description=self._original_description,
            version=self._original_version,
            root_path=self._original_root_path,
            docs_url=self._original_docs_url,
            openapi_url=self._original_openapi_url,
            redoc_url=self._original_redoc_url,
            default_response_class=self._original_default_response_class,
        )
        self._remove_route_patterns([f"{self.ROUTE_PREFIX}*"])
        super().tearDown()

    def _set_fastapi_options(self, **kwargs):
        app = main.get_app()
        main.set_metadata(title=app.title, description=app.description, version=app.version, **kwargs)

    async def _get_request_details_async(self, url):
        result = []
        scope = {
            "type": "http",
            "method": "GET",
            "path": url,
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
        }

        async def _receive():
            return {}

        async def _send(data):
            result.append(data)

        await main.get_app()(scope, _receive, _send)

        body = ""
        status = 503
        headers = {}
        for entry in result:
            if entry["type"] == "http.response.start":
                status = entry["status"]
                headers = {key.decode("utf-8"): value.decode("utf-8") for key, value in entry.get("headers", [])}
            elif entry["type"] == "http.response.body":
                body = entry["body"].decode("utf-8")

        return body, status, headers

    async def test_router_prefix_alone_keeps_docs_global(self):
        router = fastapi.APIRouter()

        @router.get("/things")
        async def list_things():
            return ["thing"]

        main.register_router(router, prefix="/v1")

        try:
            route_result, route_status = await self._get_request_async("/v1/things")
            self.assertEqual(route_status, 200)
            self.assertEqual(route_result, ["thing"])

            versioned_docs_result, versioned_docs_status = await self._get_request_async("/v1/docs")
            self.assertEqual(versioned_docs_status, 404)
            self.assertEqual(versioned_docs_result, {"detail": "Not Found"})

            global_docs_result, global_docs_status = await self._get_request_async("/docs")
            self.assertEqual(global_docs_status, 200)
            self.assertIn("/openapi.json", global_docs_result)
        finally:
            main.deregister_router(router, prefix="/v1")

    async def test_set_metadata_can_move_docs_endpoints_for_versioned_router(self):
        router = fastapi.APIRouter()

        @router.get("/things")
        async def list_things():
            return ["thing"]

        self._set_fastapi_options(
            docs_url="/v1/docs",
            openapi_url="/v1/openapi.json",
            redoc_url="/v1/redoc",
        )
        main.register_router(router, prefix="/v1")

        try:
            app = main.get_app()
            self.assertEqual(app.docs_url, "/v1/docs")
            self.assertEqual(app.openapi_url, "/v1/openapi.json")
            self.assertEqual(app.redoc_url, "/v1/redoc")

            route_result, route_status = await self._get_request_async("/v1/things")
            self.assertEqual(route_status, 200)
            self.assertEqual(route_result, ["thing"])

            docs_result, docs_status = await self._get_request_async("/v1/docs")
            self.assertEqual(docs_status, 200)
            self.assertIn("/v1/openapi.json", docs_result)

            openapi_result, openapi_status = await self._get_request_async("/v1/openapi.json")
            self.assertEqual(openapi_status, 200)
            self.assertEqual(openapi_result["info"]["title"], app.title)
            self.assertIn("/v1/things", openapi_result["paths"])

            redoc_result, redoc_status = await self._get_request_async("/v1/redoc")
            self.assertEqual(redoc_status, 200)
            self.assertIn("/v1/openapi.json", redoc_result)

            default_docs_result, default_docs_status = await self._get_request_async("/docs")
            self.assertEqual(default_docs_status, 404)
            self.assertEqual(default_docs_result, {"detail": "Not Found"})

            default_openapi_result, default_openapi_status = await self._get_request_async("/openapi.json")
            self.assertEqual(default_openapi_status, 404)
            self.assertEqual(default_openapi_result, {"detail": "Not Found"})

            default_redoc_result, default_redoc_status = await self._get_request_async("/redoc")
            self.assertEqual(default_redoc_status, 404)
            self.assertEqual(default_redoc_result, {"detail": "Not Found"})
        finally:
            main.deregister_router(router, prefix="/v1")

    async def test_set_metadata_can_replace_existing_docs_routes(self):
        self._set_fastapi_options(
            docs_url="/v1/docs",
            openapi_url="/v1/openapi.json",
            redoc_url="/v1/redoc",
        )
        self._set_fastapi_options(
            docs_url="/v2/docs",
            openapi_url="/v2/openapi.json",
            redoc_url="/v2/redoc",
        )

        app = main.get_app()
        self.assertEqual(app.docs_url, "/v2/docs")
        self.assertEqual(app.openapi_url, "/v2/openapi.json")
        self.assertEqual(app.redoc_url, "/v2/redoc")

        old_docs_result, old_docs_status = await self._get_request_async("/v1/docs")
        self.assertEqual(old_docs_status, 404)
        self.assertEqual(old_docs_result, {"detail": "Not Found"})

        old_openapi_result, old_openapi_status = await self._get_request_async("/v1/openapi.json")
        self.assertEqual(old_openapi_status, 404)
        self.assertEqual(old_openapi_result, {"detail": "Not Found"})

        new_docs_result, new_docs_status = await self._get_request_async("/v2/docs")
        self.assertEqual(new_docs_status, 200)
        self.assertIn("/v2/openapi.json", new_docs_result)

        new_openapi_result, new_openapi_status = await self._get_request_async("/v2/openapi.json")
        self.assertEqual(new_openapi_status, 200)
        self.assertEqual(new_openapi_result["info"]["title"], app.title)

    async def test_set_metadata_can_disable_docs_endpoints(self):
        self._set_fastapi_options(docs_url=None, openapi_url=None, redoc_url=None)
        app = main.get_app()

        self.assertIsNone(app.docs_url)
        self.assertIsNone(app.openapi_url)
        self.assertIsNone(app.redoc_url)

        docs_result, docs_status = await self._get_request_async("/docs")
        self.assertEqual(docs_status, 404)
        self.assertEqual(docs_result, {"detail": "Not Found"})

        openapi_result, openapi_status = await self._get_request_async("/openapi.json")
        self.assertEqual(openapi_status, 404)
        self.assertEqual(openapi_result, {"detail": "Not Found"})

        redoc_result, redoc_status = await self._get_request_async("/redoc")
        self.assertEqual(redoc_status, 404)
        self.assertEqual(redoc_result, {"detail": "Not Found"})

    async def test_set_metadata_can_update_default_response_class(self):
        router = fastapi.APIRouter()

        @router.get("/plain")
        async def plain():
            return "plain response"

        self._set_fastapi_options(default_response_class=PlainTextResponse)
        main.register_router(router, prefix=self.ROUTE_PREFIX)

        try:
            body, status, headers = await self._get_request_details_async(f"{self.ROUTE_PREFIX}/plain")
            self.assertEqual(status, 200)
            self.assertEqual(body, "plain response")
            self.assertTrue(headers.get("content-type", "").startswith("text/plain"))
            self.assertEqual(main.get_app().router.default_response_class, PlainTextResponse)
        finally:
            main.deregister_router(router, prefix=self.ROUTE_PREFIX)

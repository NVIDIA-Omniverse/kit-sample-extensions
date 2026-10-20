# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Omniverse microservices framework."""

__all__ = [
    "register_endpoint",
    "register_websocket_endpoint",
    "register_asyncapi_app",
    "register_mount",
    "register_facility",
    "register_router",
    "register_middleware",
    "deregister_endpoint",
    "deregister_mount",
    "deregister_router",
    "deregister_asyncapi_app",
    "register_encoder",
    "set_metadata",
    "get_app",
    "register_health_provider",
    "deregister_health_provider",
    "get_health_providers",
]

import os
from typing import Any, Callable, Dict, List, Optional, Set, Type

import carb
import omni.ext
import omni.kit
import omni.kit.app
import omni.services.facilities.base as facilities
import starlette
from carb.eventdispatcher import get_eventdispatcher
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIWebSocketRoute
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from . import _app, _encoding, routers
from .health import HealthCheckRegistry, HealthCheckResult

_singleton = None
_UNSET = object()
_DOCS_ROUTE_NAMES = {"openapi", "swagger_ui_html", "swagger_ui_redirect", "redoc_html"}


def register_endpoint(verb: str, url: str, func: Callable[..., Any], **kwargs: Optional[Any]) -> None:
    """
    Register an endpoint with the Services framework.

    Args:
        verb (str): HTTP verb the endpoint should respond to (e.g. "get", "post", "put", etc.).
        url (str): URL of the endpoint.
        func (Callable[..., Any]): Callback to execute upon reaching the endpoint.
        **kwargs: Optional additional parameters to forward to FastAPI.

    Returns:
        None

    """
    _singleton.register_endpoint(verb, url, func, **kwargs)


def register_websocket_endpoint(url: str, func: Callable[..., Any], **kwargs) -> None:
    """
    Register an endpoint with the Services framework accessible via websockets.

    Args:
        url (str): URL of the endpoint.
        func (Callable[..., Any]): Callback to execute upon reaching the endpoint.
        **kwargs: Optional additional parameters to forward to FastAPI.

    Returns:
        None

    """
    _singleton.register_websocket_endpoint(url, func, **kwargs)


def register_asyncapi_app(app, app_name: str, **kwargs):
    """
    Register an AsyncAPI Application with the services framework

    Args:
        app: Instance of the AsyncAPI Application
        app_id (str): Machine friendly name for the application
        **kwargs: Optional additional parameters
    """
    _singleton.register_asyncapi_app(app, app_name, **kwargs)


def register_mount(path: str, app: ASGIApp, **kwargs: Optional[Any]) -> None:
    """
    Register a mount point with the Services framework.

    Args:
        path (str): URL of the endpoint.
        app (ASGIApp): An ASGI-compatible mount point to forward to FastAPI.
        **kwargs: Optional additional parameters to forward to FastAPI.

    Returns:
        None

    """
    _singleton.register_mount(path, app, **kwargs)


def register_facility(facility: facilities.Facility) -> None:
    """
    Register a facility with the Services framework.

    Args:
        facility (facilities.Facility): Facility to register to the Services framework.

    Returns:
        None
    """
    _singleton.facilities.append(facility)


def register_router(router: routers.ServiceAPIRouter, **kwargs: Optional[Any]) -> None:
    """
    Register a router with the Services framework.

    Args:
        router (routers.ServiceAPIRouter): Router to register to the Services framework.
        **kwargs: Optional additional parameters to forward to FastAPI.

    Returns:
        None

    """
    _singleton.register_router(router, **kwargs)


def register_middleware(cls: type, **kwargs: Optional[Any]) -> None:
    """
    Register a middleware with Services framework.

    Args:
        cls (type): Middleware to register to the Services framework.
        **kwargs: Optional additional parameters to forward to FastAPI.

    Returns:
        None

    """
    _singleton.app.add_middleware(cls, **kwargs)


def deregister_endpoint(verb: str, url: str) -> None:
    """
    Deregister an endpoint from the Services framework.

    Args:
        verb (str): HTTP verb of the endpoint to deregister (e.g. "get", "post", "put", etc.).
        url (str): URL of the endpoint to deregister.

    Returns:
        None

    """
    _singleton.deregister_endpoint(verb, url)


def deregister_mount(path: str) -> None:
    """
    Deregister a mount point from the Services framework.

    Args:
        path (str): Path of the mount point to deregister.

    Returns:
        None

    """
    _singleton.deregister_mount(path)


def deregister_router(router: routers.ServiceAPIRouter, prefix: str = None) -> None:
    """
    Deregister a router from the Services framework.

    Args:
        router (routers.ServiceAPIRouter): Router to deregister.
        prefix (str): Prefix of the Router to deregister.

    Returns:
        None

    """
    _singleton.deregister_router(router, prefix=prefix)


def deregister_asyncapi_app(app_name: str):
    """
    Deregister an AsyncAPI Application with the services framework

    Args:
        app_name (str): Name of the application
    """
    _singleton.deregister_asyncapi_app(app_name=app_name)


def register_encoder(name: str, encoder: Any) -> None:
    """
    Register a data encoder.

    The encoder is expected to have both a `compress` and `decompress` function.

    Args:
        name (str): Name of the encoder to register.
        encoder (Any): Encoder to register.

    Returns:
        None

    """
    _encoding.register_encoder(name, encoder)


def set_metadata(
    title: str,
    description: str,
    version: str,
    tags_metadata: List[Dict[str, str]] = None,
    root_path: Optional[str] = None,
    docs_url: Any = _UNSET,
    openapi_url: Any = _UNSET,
    redoc_url: Any = _UNSET,
    default_response_class: Any = _UNSET,
) -> None:
    """
    Set service metadata

    Args:
        title (str): Title of the service
        description (str): Description of the service
        version (str): Version of the service

    Kwargs:
        tags_metadata List[Dict[str, str]]: List of definitions for tags in the format: [{"name": "<name of tag>"}, "description": "<tag description>"}, {"name": "<name of tag>"}, "description": "<tag description>"}]
        root_path (Optional[str]): Root path to use in case of a service being behind a proxy (see the `Fast API documentation <https://fastapi.tiangolo.com/advanced/behind-a-proxy>`_ for reference).
        docs_url (Optional[str]): Path to the Swagger UI page. Pass `None` to disable it.
        openapi_url (Optional[str]): Path to the OpenAPI schema. Pass `None` to disable it.
        redoc_url (Optional[str]): Path to the ReDoc page. Pass `None` to disable it.
        default_response_class (Type[Response]): Default FastAPI response class for routes registered after this call.

    Returns:
        None

    """
    _singleton.set_description(title, description, version)

    if root_path:
        _singleton.set_root_path(root_path)

    if docs_url is not _UNSET or openapi_url is not _UNSET or redoc_url is not _UNSET:
        _singleton.set_docs_urls(docs_url=docs_url, openapi_url=openapi_url, redoc_url=redoc_url)

    if default_response_class is not _UNSET:
        _singleton.set_default_response_class(default_response_class)

    if tags_metadata:
        get_app().openapi_tags.extend(tags_metadata)


def get_app():
    return _singleton.app


def register_health_provider(
    name: str,
    check: Callable[[], HealthCheckResult],
    probe_types: Optional[List[str]] = None,
) -> None:
    """Register a health check provider.

    Args:
        name: Unique provider name (e.g. "omni.services.livestream.session").
        check: Callable returning HealthCheckResult.
        probe_types: Which probes this provider participates in.
            Valid: "livez", "readyz", "startupz". Default: ["livez", "readyz"].
    """
    _singleton._health_registry.register(name, check, probe_types)


def deregister_health_provider(name: str) -> None:
    """Deregister a health check provider."""
    _singleton._health_registry.deregister(name)


def get_health_providers() -> Dict[str, Any]:
    """Get all registered health providers and their active status.

    Returns:
        dict: {"provider_name": {"probe_types": [...], "active": bool}, ...}
    """
    settings = carb.settings.get_settings()
    active_list = settings.get("/exts/omni.services.core/health/activeProviders") or []
    all_providers = _singleton._health_registry.get_all_providers()
    return {
        name: {
            "probe_types": entry.probe_types,
            "active": name in active_list,
        }
        for name, entry in all_providers.items()
    }


async def _status():
    """Returns the current status of the service."""
    return "OK"


def _deprecated_probe(old: str, new: str):
    """Return a handler that warns about a deprecated probe endpoint."""

    async def _handler():
        carb.log_warn(f"{old} is deprecated, use {new} instead")
        status = await _status()
        return {
            "status": status,
            "deprecated": True,
            "message": f"{old} is deprecated. Use {new} instead.",
        }

    return _handler


class ServicesCoreExtension(omni.ext.IExt):
    """
    Core Services extension

    The Core of Kit's microservices framework.

    Services can be registered using the `controlport`.
    When paired with one (or multiple) of the transport extensions the services can be served to be accessed over
    various protocols such as HTTP, HTTPS, etc.

    """

    _title = "Kit services core"
    _description = "Drive Kit with microservices"
    _version = "0.1"

    def __init__(self, *args, **kwargs):
        super(ServicesCoreExtension, self).__init__(*args, **kwargs)

        _settings = carb.settings.get_settings_interface()
        root_path = _settings.get_as_string("/exts/omni.services.core/root_path") or ""
        strict_content_type = _settings.get_as_bool("/exts/omni.services.core/strict_content_type")

        self._app = _app.OmniverseService(
            title=self._title,
            description=self._description,
            version=self._version,
            openapi_tags=[],
            root_path=root_path,
            strict_content_type=strict_content_type,
        )
        self._facilities: List[facilities.Facility] = []

        # Register FastAPI middlewares to assist with configuration of the Services framework:
        self._register_middlewares()

        self._async_apps = {}
        self._health_registry = HealthCheckRegistry()
        self._app_ready = False
        self._app_ready_sub = None

    def _register_middlewares(self) -> None:
        """
        Register FastAPI middlewares to assist with configuration of the Services framework.

        Args:
            None

        Return:
            None

        """
        settings = carb.settings.get_settings_interface()
        CORRELATION_ID_SETTING_PREFIX = "/exts/omni.services.core/correlation_id"

        use_default_correlation_id_middleware = settings.get_as_bool(
            f"{CORRELATION_ID_SETTING_PREFIX}/use_default_middleware"
        )
        if use_default_correlation_id_middleware:
            header_name = settings.get_as_string(f"{CORRELATION_ID_SETTING_PREFIX}/header_name")
            update_request_header = settings.get_as_bool(f"{CORRELATION_ID_SETTING_PREFIX}/update_request_header")

            try:
                from asgi_correlation_id import CorrelationIdMiddleware

                self._app.add_middleware(
                    middleware_class=CorrelationIdMiddleware,
                    header_name=header_name,
                    update_request_header=update_request_header,
                )
            except ImportError as exc:
                carb.log_verbose(f"`asgi_correlation_id` middleware not imported: {str(exc)}")

    @property
    def app(self) -> _app.OmniverseService:
        """
        Return a reference to the FastAPI app.

        Returns:
            (OmniverseApp): A reference to the OmniverseService app.

        """
        return self._app

    def set_description(self, title: str, description: str, version: str) -> None:
        """
        Set the description of the microservices framework.

        Args:
            title (str): Title of the microservices framework.
            description (str): Description of the microservices framework.
            version (str): String representing the semantic versioning scheme of the microservices framework.

        Returns:
            None

        """
        self._app.title = title
        self._app.description = description
        self._app.version = version
        self._reset_openapi_schema()

    def set_root_path(self, root_path: str) -> None:
        """
        Set the root path of the service (e.g.: `/api/v1`).

        Args:
            root_path (str): Root path to use in case of a service being behind a proxy (https://fastapi.tiangolo.com/advanced/behind-a-proxy/)

        Returns:
            None

        """
        self._app.root_path = root_path
        self._reset_openapi_schema()

    async def _openapi_endpoint(self, req: Request) -> JSONResponse:
        """Serve the OpenAPI schema using the same root_path behavior as FastAPI."""
        root_path = req.scope.get("root_path", "").rstrip("/")
        schema = self._app.openapi()
        if root_path and self._app.root_path_in_servers:
            server_urls = {server.get("url") for server in schema.get("servers", [])}
            if root_path not in server_urls:
                schema = dict(schema)
                schema["servers"] = [{"url": root_path}] + schema.get("servers", [])
        return JSONResponse(schema)

    async def _swagger_ui_endpoint(self, req: Request) -> HTMLResponse:
        """Serve the Swagger UI for the current OpenAPI route."""
        root_path = req.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + self._app.openapi_url
        oauth2_redirect_url = self._app.swagger_ui_oauth2_redirect_url
        if oauth2_redirect_url:
            oauth2_redirect_url = root_path + oauth2_redirect_url

        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{self._app.title} - Swagger UI",
            oauth2_redirect_url=oauth2_redirect_url,
            init_oauth=self._app.swagger_ui_init_oauth,
            swagger_ui_parameters=self._app.swagger_ui_parameters,
        )

    async def _swagger_ui_redirect_endpoint(self, _: Request) -> HTMLResponse:
        """Serve the OAuth2 redirect page used by Swagger UI."""
        return get_swagger_ui_oauth2_redirect_html()

    async def _redoc_endpoint(self, req: Request) -> HTMLResponse:
        """Serve the ReDoc page for the current OpenAPI route."""
        root_path = req.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + self._app.openapi_url
        return get_redoc_html(openapi_url=openapi_url, title=f"{self._app.title} - ReDoc")

    def _remove_docs_routes(self, route_paths: Set[Optional[str]]) -> None:
        """Remove dynamically managed OpenAPI/Swagger/ReDoc helper routes."""
        valid_paths = {path for path in route_paths if path}
        self._app.routes[:] = [
            route
            for route in self._app.routes
            if not (getattr(route, "path", None) in valid_paths and getattr(route, "name", None) in _DOCS_ROUTE_NAMES)
        ]

    def _register_docs_routes(self) -> None:
        """Register OpenAPI/Swagger/ReDoc helper routes using FastAPI's public helpers."""
        if self._app.openapi_url:
            self._app.add_route(self._app.openapi_url, self._openapi_endpoint, include_in_schema=False, name="openapi")

            if self._app.docs_url:
                self._app.add_route(
                    self._app.docs_url,
                    self._swagger_ui_endpoint,
                    include_in_schema=False,
                    name="swagger_ui_html",
                )

                if self._app.swagger_ui_oauth2_redirect_url:
                    self._app.add_route(
                        self._app.swagger_ui_oauth2_redirect_url,
                        self._swagger_ui_redirect_endpoint,
                        include_in_schema=False,
                        name="swagger_ui_redirect",
                    )

            if self._app.redoc_url:
                self._app.add_route(
                    self._app.redoc_url,
                    self._redoc_endpoint,
                    include_in_schema=False,
                    name="redoc_html",
                )

    def set_docs_urls(
        self,
        docs_url: Any = _UNSET,
        openapi_url: Any = _UNSET,
        redoc_url: Any = _UNSET,
    ) -> None:
        """
        Update the FastAPI documentation endpoint paths on the running service app.

        Args:
            docs_url (Optional[str]): Path to the Swagger UI page. Pass `None` to disable it.
            openapi_url (Optional[str]): Path to the OpenAPI schema. Pass `None` to disable it.
            redoc_url (Optional[str]): Path to the ReDoc page. Pass `None` to disable it.

        Returns:
            None

        """
        updated_docs_url = self._app.docs_url if docs_url is _UNSET else docs_url
        updated_openapi_url = self._app.openapi_url if openapi_url is _UNSET else openapi_url
        updated_redoc_url = self._app.redoc_url if redoc_url is _UNSET else redoc_url

        route_paths = {
            self._app.docs_url,
            self._app.openapi_url,
            self._app.redoc_url,
            getattr(self._app, "swagger_ui_oauth2_redirect_url", None),
            updated_docs_url,
            updated_openapi_url,
            updated_redoc_url,
        }

        self._remove_docs_routes(route_paths)

        self._app.docs_url = updated_docs_url
        self._app.openapi_url = updated_openapi_url
        self._app.redoc_url = updated_redoc_url

        self._register_docs_routes()
        self._reset_openapi_schema()

    def set_default_response_class(self, default_response_class: Type[Response]) -> None:
        """
        Set the default FastAPI response class for future routes registered on the app.

        Args:
            default_response_class (Type[Response]): Response class to use by default.

        Returns:
            None

        """
        self._app.router.default_response_class = default_response_class
        if hasattr(self._app, "default_response_class"):
            self._app.default_response_class = default_response_class
        self._reset_openapi_schema()

    @property
    def facilities(self) -> List[facilities.Facility]:
        """
        Return the list of Facilities currently registered with the microservices framework.

        Returns:
            List[facilities.Facility]: The list of Facilities currently registered.

        """
        return self._facilities

    def on_startup(self) -> None:
        global _singleton
        _singleton = self

        show_status_endpoint = carb.settings.get_settings_interface().get_as_bool(
            "exts/omni.services.core/show_status_endpoint"
        )
        self.register_endpoint(
            "get",
            "/status",
            _status,
            include_in_schema=show_status_endpoint,
            summary="Returns the current status of the service",
        )
        self.register_endpoint(
            "get",
            "/health",
            _deprecated_probe("/health", "/livez"),
            include_in_schema=show_status_endpoint,
            summary="Health probe (deprecated, use /livez)",
            deprecated=True,
        )
        self.register_endpoint(
            "get",
            "/ready",
            _deprecated_probe("/ready", "/readyz"),
            include_in_schema=show_status_endpoint,
            summary="Readiness probe (deprecated, use /readyz)",
            deprecated=True,
        )
        self.register_endpoint(
            "get",
            "/startup",
            _deprecated_probe("/startup", "/startupz"),
            include_in_schema=show_status_endpoint,
            summary="Startup probe (deprecated, use /startupz)",
            deprecated=True,
        )

        manager = omni.kit.app.get_app().get_extension_manager()
        self._data_path = os.path.join(manager.get_extension_path_by_module(__name__), "data")

        # Used by some of the connectors but should eventually be removed.
        self.register_endpoint("get", "/controlport/status", _status, include_in_schema=False)

        self.register_endpoint("get", "/asyncapi/docs", self._async_app_docs_endpoint)
        self.register_endpoint("get", "/asyncapi/schema", self._async_app_schema_endpoint)

        # Subscribe to app-ready event and register the built-in health
        # provider that tracks it.
        self._app_ready_sub = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_APP_READY,
            on_event=lambda _: setattr(self, "_app_ready", True),
            observer_name="omni.services.core.health",
        )
        self._health_registry.register(
            name="omni.kit.app",
            check=lambda: HealthCheckResult(
                healthy=self._app_ready,
                message="App ready" if self._app_ready else "App not ready",
            ),
            probe_types=["livez", "readyz", "startupz"],
        )

        # Register aggregated probe endpoints.
        self.register_endpoint(
            "get",
            "/livez",
            self._livez_endpoint,
            include_in_schema=show_status_endpoint,
            summary="Liveness probe",
        )
        self.register_endpoint(
            "get",
            "/readyz",
            self._readyz_endpoint,
            include_in_schema=show_status_endpoint,
            summary="Readiness probe",
        )
        self.register_endpoint(
            "get",
            "/startupz",
            self._startupz_endpoint,
            include_in_schema=show_status_endpoint,
            summary="Startup probe",
        )
        self.register_endpoint(
            "get",
            "/healthz/providers",
            self._health_providers_endpoint,
            include_in_schema=show_status_endpoint,
            summary="Health check provider discovery",
        )

    async def _livez_endpoint(self):
        return self._probe_handler("livez")

    async def _readyz_endpoint(self):
        return self._probe_handler("readyz")

    async def _startupz_endpoint(self):
        return self._probe_handler("startupz")

    async def _health_providers_endpoint(self):
        return get_health_providers()

    def _probe_handler(self, probe_type: str):
        settings = carb.settings.get_settings()
        active_list = settings.get("/exts/omni.services.core/health/activeProviders") or []

        results = {}
        all_healthy = True

        # Iterate in activeProviders order so the application developer
        # controls evaluation and response order.
        for name in active_list:
            entry = self._health_registry.get_provider(name)
            if entry is None or probe_type not in entry.probe_types:
                continue

            try:
                result = entry.check()
                results[name] = {
                    "healthy": result.healthy,
                    "message": result.message,
                }
                if not result.healthy:
                    all_healthy = False
            except Exception as exc:
                results[name] = {
                    "healthy": False,
                    "message": f"Check failed: {exc}",
                }
                all_healthy = False

        content = {
            "status": "healthy" if all_healthy else "unhealthy",
            "providers": results,
        }

        if all_healthy:
            return content
        return JSONResponse(content=content, status_code=503)

    async def _async_app_schema_endpoint(self, app_name: str):
        if app_name not in self._async_apps:
            return JSONResponse(
                status_code=404,
                content={"message": "Not Found"},
            )

        return self._async_apps[app_name].spec()

    async def _async_app_docs_endpoint(self, app_name: str):
        if app_name not in self._async_apps:
            # TODO: return a nice HTMLResponse instead.
            return JSONResponse(status_code=404, content={"message": "Not Found"})

        template_path = os.path.join(self._data_path, "templates", "asyncapi_browser.html")
        with open(template_path, "r") as file:
            html_content = file.read()

        # Replace the placeholder with the schema_url
        html_content = html_content.replace("{{ schema_url }}", f"/asyncapi/schema?app_name={app_name}")

        return HTMLResponse(content=html_content)

    def register_endpoint(self, verb: str, url: str, func: Callable[..., Any], **kwargs: Optional[Any]) -> None:
        """
        Register an endpoint with the Services framework.

        Args:
            verb (str): HTTP verb the endpoint should respond to (e.g. "get", "post", "put", etc.).
            url (str): URL of the endpoint.
            func (Callable[..., Any]): Callback to execute upon reaching the endpoint.
            **kwargs: Optional additional parameters to forward to FastAPI.

        Returns:
            None

        """
        verb_func = getattr(self._app, verb)
        verb_func(url, **kwargs)(func)
        self._reset_openapi_schema()

    def register_websocket_endpoint(self, url: str, func: Callable[..., Any], **kwargs: Optional[Any]) -> None:
        """
        Register an endpoint with the Services framework accessible via websockets.

        Args:
            url (str): URL of the endpoint.
            func (Callable[..., Any]): Callback to execute upon reaching the endpoint.
            **kwargs: Optional additional parameters to forward to FastAPI.

        Returns:
            None

        """
        self._app.add_api_websocket_route(url, func, **kwargs)
        self._reset_openapi_schema()

    def register_mount(self, path: str, app: ASGIApp, **kwargs: Optional[Any]) -> None:
        """
        Register a mount point with the Services framework.

        Args:
            path (str): URL of the endpoint.
            app (ASGIApp): An ASGI-compatible mount point to forward to FastAPI.
            **kwargs: Optional additional parameters to forward to FastAPI.

        Returns:
            None

        """
        self._app.mount(path, app, **kwargs)
        self._reset_openapi_schema()

    def register_router(self, router: routers.ServiceAPIRouter, **kwargs: Optional[Any]) -> None:
        """
        Register a router with the Services framework.

        Args:
            router (routers.ServiceAPIRouter): Router to register to the Services framework.
            **kwargs: Optional additional parameters to forward to FastAPI.

        Returns:
            None

        """
        if "prefix" in kwargs and kwargs["prefix"]:
            prefix = kwargs["prefix"].replace(".", "/")
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"
            kwargs["prefix"] = prefix

            if hasattr(router, "_bypassed_paths"):
                # NOTE: update _bypassed_paths with the prefix,
                # which is otherwise unknown to the AuthorizedServiceAPIRouter, since the router is being registered at the app level
                prefixed_bypassed_paths: Set[str] = set()
                for path in router._bypassed_paths:
                    prefixed_path = f'{kwargs["prefix"].rstrip("/")}{path}'
                    prefixed_bypassed_paths.add(prefixed_path)
                router._bypassed_paths = prefixed_bypassed_paths

        self._app.include_router(router, **kwargs)
        self._reset_openapi_schema()

    def register_asyncapi_app(self, app, app_name: str, **kwargs):
        """
        Register an AsyncAPI Application with the services framework

        Args:
            app: Instance of the AsyncAPI Application
            app_name (str): Machine friendly name for the application
            **kwargs: Optional additional parameters
        """
        self._async_apps[app_name] = app

    def deregister_endpoint(self, verb: str, url: str) -> None:
        """
        Deregister an endpoint from the Services framework.

        Args:
            verb (str): HTTP verb of the endpoint to deregister (e.g. "get", "post", "put", etc.).
            url (str): URL of the endpoint to deregister.

        Returns:
            None

        """
        to_remove = []
        for route in self._app.routes:
            path = getattr(route, "path", None)
            if path == url:
                methods = getattr(route, "methods", None) or set()
                if isinstance(route, starlette.routing.Mount) or verb.upper() in methods:
                    to_remove.append(route)

        for route in to_remove:
            self._app.routes.remove(route)

        self._reset_openapi_schema()

    def deregister_mount(self, path: str) -> None:
        """
        Deregister the given service mount point.

        Args:
            path (str): Path of the mount point to deregister.

        Returns:
            None

        """
        mounts_to_remove = []
        for route in self._app.routes:
            if isinstance(route, starlette.routing.Mount) and route.path == path:
                mounts_to_remove.append(route)

        for mount_to_remove in mounts_to_remove:
            self._app.routes.remove(mount_to_remove)

        self._reset_openapi_schema()

    def deregister_router(self, router: routers.ServiceAPIRouter, prefix: str = None) -> None:
        """
        Deregister a router from the Services framework.

        Args:
            router (routers.ServiceAPIRouter): Router to deregister.
            prefix (str): Prefix of the Router to deregister. When omitted, any included-router entries for the
                router are removed regardless of their registered prefix.

        Returns:
            None

        """
        if prefix:
            prefix = prefix.replace(".", "/")
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"

        # FastAPI 0.137.0 keeps included routers as `_IncludedRouter` route entries without a `path`.
        # Remove handles matched by `original_router` and `include_context.prefix` directly, then skip the
        # legacy flattened-route cleanup below.
        included_routers_to_remove = []
        for route in self._app.routes:
            if getattr(route, "original_router", None) is not router:
                continue

            route_prefix = getattr(getattr(route, "include_context", None), "prefix", None)
            if prefix is None or route_prefix == prefix:
                included_routers_to_remove.append(route)

        for route in included_routers_to_remove:
            self._app.routes.remove(route)

        if included_routers_to_remove:
            self._reset_openapi_schema()
            return

        for route in router.routes:
            if hasattr(route, "methods"):
                methods = sorted(route.methods)
                path = f"{prefix}{route.path}" if prefix else route.path
                for method in methods:
                    self.deregister_endpoint(method, path)
            elif issubclass(route.__class__, APIWebSocketRoute) and route in self._app.routes:
                # WebSocket routes do not feature `methods` properties, as opposed to HTTP-based routers:
                self._app.routes.remove(route)

        self._reset_openapi_schema()

    def deregister_asyncapi_app(self, app_name: str) -> None:
        """
        Deregister an AsyncAPI application

        Args:
            app_name (str): Name of the AsyncAPI application that was previously registered.
        """
        if app_name not in self._async_apps:
            carb.log_warn(f"{app_name} is not a registered AsyncAPI application")
            return

        self._async_apps.pop(app_name)

    def _reset_openapi_schema(self) -> None:
        """Reset the OpenAPI schema of the microservices framework."""
        self._app.openapi_schema = None

    def on_shutdown(self) -> None:  # pragma: no cover
        global _singleton

        self._health_registry.deregister("omni.kit.app")
        self._app_ready_sub = None

        _singleton = None

        for facility in self._facilities:
            facility.stop()

        if self._app:
            self.deregister_endpoint("get", "/status")
            self.deregister_endpoint("get", "/health")
            self.deregister_endpoint("get", "/ready")
            self.deregister_endpoint("get", "/startup")
            self.deregister_endpoint("get", "/controlport/status")
            self.deregister_endpoint("get", "/livez")
            self.deregister_endpoint("get", "/readyz")
            self.deregister_endpoint("get", "/startupz")
            self.deregister_endpoint("get", "/healthz/providers")
            self.deregister_endpoint("get", "/asyncapi/docs")
            self.deregister_endpoint("get", "/asyncapi/schema")

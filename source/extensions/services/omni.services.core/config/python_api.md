# Public API for module omni.services.core:

No public API

# Public API for module omni.services.core.main:

## Functions

- def register_endpoint(verb: str, url: str, func: Callable[Ellipsis, Any], **kwargs: Optional[Any])
- def register_websocket_endpoint(url: str, func: Callable[Ellipsis, Any], **kwargs)
- def register_asyncapi_app(app, app_name: str, **kwargs)
- def register_mount(path: str, app: ASGIApp, **kwargs: Optional[Any])
- def register_facility(facility: facilities.Facility)
- def register_router(router: routers.ServiceAPIRouter, **kwargs: Optional[Any])
- def register_middleware(cls: type, **kwargs: Optional[Any])
- def deregister_endpoint(verb: str, url: str)
- def deregister_mount(path: str)
- def deregister_router(router: routers.ServiceAPIRouter, prefix: str = None)
- def deregister_asyncapi_app(app_name: str)
- def register_encoder(name: str, encoder: Any)
- def set_metadata(title: str, description: str, version: str, tags_metadata: List[Dict[str, str]] = None, root_path: Optional[str] = None, docs_url: Any = _UNSET, openapi_url: Any = _UNSET, redoc_url: Any = _UNSET, default_response_class: Any = _UNSET)
- def get_app()
- def register_health_provider(name: str, check: Callable[[], HealthCheckResult], probe_types: Optional[List[str]] = None)
- def deregister_health_provider(name: str)
- def get_health_providers() -> Dict[str, Any]

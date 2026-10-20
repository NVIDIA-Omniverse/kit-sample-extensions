# Kit Services Core

The core of Kit's micro services framework.
Using endpoints and routers, functions can be registered to be used as microservices.

Combining the Core with the various transports (`omni.services.transport.server.*`) available services can be interacted with via the various protocols.

Using facilities (`omni.services.facilities.*`) additional, stateful, functionality can be added to the stateless services.

A reference implementation showing the combination of the core with transports, facilities and service extensions can be found in `omni.kit.controlport`.

## Documentation Endpoints

`omni.services.core` exposes the top-level FastAPI metadata through `set_metadata()`. By default the documentation endpoints are served at:

- `/docs`
- `/openapi.json`
- `/redoc`

To align the documentation with a versioned API surface, update the service metadata during your extension startup:

```python
from fastapi.responses import ORJSONResponse

import omni.services.core.main as services

services.set_metadata(
    title="My Service",
    description="Example service",
    version="1.0.0",
    docs_url="/v1/docs",
    openapi_url="/v1/openapi.json",
    redoc_url="/v1/redoc",
    default_response_class=ORJSONResponse,
)
```

These options apply to the shared FastAPI app used by `register_router()`, `register_endpoint()`, and `register_mount()`. Pass `None` for `docs_url`, `openapi_url`, or `redoc_url` to disable the corresponding documentation endpoint.

## Strict Content-Type Checking

For compatibility with existing Kit service clients, JSON request bodies without a `Content-Type` header are accepted
by default. Applications can opt in to FastAPI's strict Content-Type checking in their `.kit` file:

```toml
[settings.exts."omni.services.core"]
strict_content_type = true
```

Strict checking requires JSON requests to include a JSON Content-Type such as `application/json`. Enabling it provides
additional protection against CSRF attacks targeting unauthenticated services on localhost or trusted internal
networks. The setting is applied when `omni.services.core` starts and requires FastAPI 0.132 or newer; older FastAPI
versions retain their legacy behavior.

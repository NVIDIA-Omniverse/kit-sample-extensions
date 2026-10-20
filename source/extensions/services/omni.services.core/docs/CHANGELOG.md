# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.12.1] - 2026-10-16
### Fixed
- Tests: the GET request helper now passes a valid ASGI `receive` (one `http.request` message, then waits until cancelled).
  Starlette 1.x `FileResponse` reads `receive()` while it streams, so the mount tests failed with `KeyError: 'type'` on
  Kit 111's current Python bundle (fastapi 0.139.2, starlette 1.8.0).

## [1.12.0] - 2026-08-18
### Added
- OMPE-105894: Added the `exts."omni.services.core".strict_content_type` setting. It defaults to `false` for
  compatibility with existing Kit service clients and can be enabled by applications using FastAPI 0.132 or newer.

## [1.11.3] - 2026-07-20
### Fixed
- OMPE-99123: Updated test route tracking and cleanup for FastAPI 0.137+
  `_IncludedRouter` entries without a `path`, while retaining compatibility with FastAPI 0.120.x.

## [1.11.2] - 2026-07-03
### Fixed
- Fixed endpoint and router deregistration when FastAPI stores included routers in
  `app.routes` without a `path` attribute.

## [1.11.1] - 2026-05-28
### Fixed
- OMPE-91964: Fix unreachable error handler in `_CompressedRequest.body()`.
  The previous `break` after a successful decompress made the
  `except KeyError` unreachable for trailing `Content-Encoding` values
  and could silently return partially-decoded bytes. The loop now
  processes every encoding and propagates `KeyError` for unknown
  encoders. Added a regression test in `test_route.py`.

## [1.11.0] - 2026-04-29
### Added
- OMPE-89270: Extended `set_metadata()` with FastAPI `docs_url`, `openapi_url`, `redoc_url`, and `default_response_class` options so extensions can expose versioned documentation endpoints such as `/v1/docs` without managing a separate sub-app lifecycle.

## [1.10.0] - 2026-03-30
### Added
- Health check provider registry with `register_health_provider`, `deregister_health_provider`,
  and `get_health_providers` APIs for extensions to contribute health status.
- Aggregated probe endpoints `/livez`, `/readyz`, `/startupz` that evaluate active providers
  configured via `exts."omni.services.core".health.activeProviders`.
- Provider discovery endpoint at `/healthz/providers`.
- Built-in `omni.kit.app` provider that tracks application readiness.


### Deprecated
- `/health`, `/ready`, `/startup` endpoints now redirect to `/livez`, `/readyz`, `/startupz`
  with a deprecation warning.

## [1.9.3] - 2025-10-21
### Fixed
- Bump to re-publish

## [1.9.2] - 2025-10-17
### Fixed
- Updated repository url

## [1.9.1] - 2025-05-29
### Updated
- Change [test] to [[test]] in config.

## [1.9.0] - 2024-01-27
### Update
- Update health and status endpoints to be inline with UCS guidelines.

## [1.8.0] - 2023-11-28
### Added
- Add support for registering AsyncAPI Applications.

## [1.7.0] - 2023-10-23
### Changed
- Make /metrics endpoint visibility configurable

## [1.6.4] - 2023-10-05
### Added
- Added unit tests to increase code coverage of Core features.
- Added code documentation.

## [1.6.3] - 2023-09-01
### Changed
- Temporarily muted imports of `asgi_correlation_id` to work around mixed imports of `starlette` between `kit-services` and `kit` components.

## [1.6.2] - 2023-08-31
### Fixed
- Fixed issue where discrepancies between various various of the `starlette` dependency of FastAPI may cause crashes due to the `self._debug` attribute of `starlette` application (inherited from `starlette`) was renamed to `self.debug`.

## [1.6.1] - 2023-08-25
### Added
- Added ability to convert FastAPI Request Headers to a Python dictionary, suitable for the Service framework's `AsyncClient`.

## [1.6.0] - 2023-08-09
### Added
- Added ability to generate unique Correlation IDs to requests issued against the Services framework.

## [1.5.6] - 2023-08-08
### Fixed
- Fixed bug preventing supplying a different `route_class` than the default `omni.services.core._route.CompressedRoute`.

## [1.5.5] - 2023-07-14
### Changed
- Added filter for de-registering websocket endpoint.

## [1.5.4] - 2023-07-03
### Added
- Added support for de-registering WebSocket routes for Service API endpoints.

## [1.5.3] - 2023-06-26
### Changed
- Include router prefix if specified and update `_bypassed_paths` on the router (used by `AuthorizedServiceAPIRouter`).

## [1.5.2] - 2023-06-04
### Changed
- Added dependency on `omni.kit.async_engine` given the async nature of the library. This is to assure clean shutdowns

## [1.5.1] - 2023-05-27
### Changed
- Hide deprecated /controlport/status endpoint from OpenAPI schema.

## [1.5.0] - 2023-05-19
### Changed
- Custom App class
- Expose option for root_path

## [1.4.5] - 2023-04-27
### Changed
- Update unit tests for `omni.services.core`.

## [1.4.4] - 2023-04-27
### Changed
- Update unit tests for `omni.services.core`.

## [1.4.3] - 2023-04-24
### Changed
- Update unit tests for `omni.services.core`.

## [1.4.2] - 2023-02-28
### Changed
- Update unit tests to use `omni.kit.test.AsyncTestCase` class.

## [1.4.1] - 2023-02-01
### Added
- Add query_params to _get_request_async method of base test class

## [1.4.0] - 2023-01-22
### Added
- Add support for declaring prefixes and tags in the ServiceAPIRouter directly
- Add support for setting metadata directly on the app
- Auto-initialize openapi_tags to avoid needing checks on empty lists
- Add support for dotted prefixes

## [1.3.0] - 2022-11-09
### Remove
- Remove dependency on omni.kit.tests

## [1.2.0] - 2021-12-06
### Added
- Add /status and /controlport/status (for backwards compatibility) to indicate if the services are up.

## [1.1.1] - 2021-05-14
### Added
- Added option to register and deregister mount points for static assets.
- Enhanced documentation.
- Improved test coverage.

## [1.1.0] - 2020-11-27
### Added
- Added option to deregister endpoints and routers.

## [1.0.0] - 2020-09-17
### Added
- Initial commit of `omni.services.core` after porting it over from omni.kit.controlport.

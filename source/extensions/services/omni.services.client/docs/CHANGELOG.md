# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.9] - 2026-08-06
### Fixed
- NVBug 6570026: Resolve local transport routes nested through multiple included routers with FastAPI 0.139 while retaining compatibility with FastAPI 0.120.

## [0.5.8] - 2026-07-30
### Fixed
- Fixed local transport route discovery and JSON request bodies with FastAPI 0.139 while retaining compatibility with FastAPI 0.120.

## [0.5.6] - 2026-03-16
### Fixed
- OMPE-75512: Fix `fastapi_middleware_astack not found in request scope` assertion in local transport by injecting `AsyncExitStack` into scope before calling `route.handle()`

## [0.5.5] - 2026-01-25
### Fixed
- OMPE-77011: make omni.services.client to work with fastapi 0.118.0 or higher

## [0.5.4] - 2025-10-17
### Fixed
- Updated repository url

## [0.5.3] - 2023-08-29
### Added
- Added checks validating that URIs provided to `Client` and `AsyncClient` contain a scheme making it possible to identify the underlying Transport to use for communication.

## [0.5.2] - 2023-08-28
### Added
- Added inline code documentation to assist developers in implementing Clients against their own systems.

## [0.5.1] - 2023-05-06
### Fixed
- Bump to force re-release of extension

## [0.5.0] - 2023-05-04
### Fixed
- Fix route matching to be exact match instead of partial.

## [0.4.2] - 2023-02-28
### Changed
- Update unit tests to use `omni.kit.test.AsyncTestCase` class.

## [0.4.1] - 2023-02-15
### Fixed
- Fixed missing `super().__init__()` for Python 3.10

## [0.4.0] - 2022-07-13
### Fixed
- Fix passing query parameters for GET requests.

## [0.3.0] - 2022-04-25
### Added
- Adds `raise_for_status` kwarg to Consumers for returning errors rather than raising exceptions.

## [0.2.3] - 2021-11-04
### Fixed
- Fix for when none conventional mounts are used in local transport.

## [0.2.2] - 2021-09-28
### Fixed
- Fix support for headers in local transport.

## [0.2.1] - 2021-09-15
### Fixed
- Catch cases where a client transport is deregistered multiple times. This happens in rare occasions where two versions of an extension are loaded.

## [0.2.0] - 2020-10-09
### Added
- Add `api_version` as a parameter to the client. This can be handled by each transport individually.

## [0.1.1] - 2020-10-07
### Fixes
- Add `fastapi` as a test dependency. This should go away after SWIPAT approval.

## [0.1.0] - 2020-08-25
### Fixes
- Remove print of time for each call.

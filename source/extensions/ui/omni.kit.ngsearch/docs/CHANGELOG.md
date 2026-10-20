# Changelog

This document records all notable changes to ``omni.kit.ngsearch`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [0.3.3] - 2023-10-25
### Updated
- coverage exclusion cleanup

## [0.3.2] - 2023-10-25
### Updated
- coverage exclusion patterns

## [0.3.1] - 2023-10-24
### Added
- excluded ``idl`` package from python test coverage

## [0.3.0] - 2023-10-11
### Updated
- Removed imports from ``__init__.py`` module

## [0.2.6] - 2023-10-10
### Updated
- Removed the websockets check on extension startup
- Lazy loading of S3 backend

## [0.2.5] - 2023-09-13
### Updated
- Minor logging format change

## [0.2.4] - 2023-07-14
### Added
- Exception handling, when search operation fails

## [0.2.3] - 2023-07-05
### Fixed
- multi-server empty results return fix

## [0.2.2] - 2023-06-27
### Fixed
- embedding results return proper URLs now
- multi-server search does not break, when some servers are unresponsive

## [0.2.1] - 2023-06-12
### Updated
- re-do multi-server search in case token is expired
### Added
- flag for skipping authorization in multi-server search
- batch size to return only the top results coming from all the servers

## [0.2.0] - 2023-06-01
### Added
- added multi-server embedding retrieval functionality
### Fixed
- exception handling on availability check

## [0.1.5] - 2023-05-04
### Added
- fixed returned URL in Search Gen 2 method

## [0.1.4] - 2023-05-02
### Added
- support for S3 DeepSearch backends

## [0.1.3] - 2023-04-03
### Fixed
- fixed test

## [0.1.2] - 2023-04-03
### Fixed
- websockets 10.3 pip dependency
- added websocket version test on startup

## [0.1.1] - 2023-03-13
### Fixed
- Kit 105, py3.10 compatibility fix

## [0.1.0] - 2023-02-13
### Added
- close connection functionality
### Fixed
- 'search_gen_2' method - added a check on response status before URLs are being processed

## [0.0.11] - 2023-01-14
### Added
- added heirarchy retrieval functionality to the client
### Updated
- IDL and NGSearch packman package update

## [0.0.10] - 2023-01-14
### Added
- Add explicit [[python.module]] for "idl"

## [0.0.9] - 2022-01-10
### Added
- Telemetry context for search operations

## [0.0.8] - 2022-01-10
### Added
- OM-57029: Telemetry events
- Keep alive service transport context
- Updated manual tests to better cover various corner cases
- Added manual test run script

## [0.0.7] - 2022-11-22
### Modified
- Bugfix: return URLs with the same host as the search request was made

## [0.0.6] - 2022-11-16
### Modified
- Bugfix: try reconnecting to NGSearch, when connection was not succesful

## [0.0.5] - 2022-08-25
### Modified
- CLIP projections support added

## [0.0.4] - 2022-08-22
### Modified
- Removed Telemetry API in favor of built-in kit telemetry.

## [0.0.3] - 2022-07-20
### Added
- Telemetry API

## [0.0.2] - 2022-06-30
### Added
- Added get_embeddings API

## [0.0.1] - 2022-06-16
### Added
- Initial version implementation

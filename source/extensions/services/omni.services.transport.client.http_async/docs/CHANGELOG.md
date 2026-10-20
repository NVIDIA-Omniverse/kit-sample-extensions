# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.2] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.4.1] - 2025-05-29
### Updated
- Change [test] to [[test]] in config.

## [1.4.0] - 2025-02-24
### Changed
- OMPE-34947: Improve test to compatibility with aiohttp 3.11.11

## [1.3.6] - 2023-08-28
### Added
- Added support for handling `__method__` arguments in a case-insensitive manner.
- Added more descriptive exception messages.

## [1.3.5] - 2023-08-28
### Added
- Added inline code documentation to assist developers in implementing Clients against their own systems.

## [1.3.4] - 2023-02-28
### Changed
- Increase test `tearDown()` sleep duration, to allow enough time for tasks to be drained before shutting down the main application loop during test cases.

## [1.3.3] - 2023-02-15
### Changed
- Version bump for Python 3.10

## [1.3.2] - 2022-07-05
### Added
- Only add http_status field when using `raise_for_exception=False`. This will assume that the user will manually unpack the return values.

## [1.3.1] - 2022-06-15
### Added
- Fixes overwritten response status.

## [1.3.0] - 2022-06-03
### Added
- Support for `patch` operations

## [1.2.1] - 2022-05-11
### Added
- Catches aiohttp.ClientConnectorError as well as all generic Exceptions during a call.

## [1.2.0] - 2022-04-25
### Added
- Adds raise_for_status kwarg to Consumer for returning errors rather than raising exceptions.

## [1.1.3] - 2022-04-06
### Changed
- Moved slow import statements to be local to improve Kit startup times

## [1.1.2] - 2022-01-13
### Changed
- Fix BaseServiceError not containing the actual error message from the upstream exception.

## [1.1.1] - 2021-10-23
### Changed
- Updated iconography of Extension to match Omniverse Farm branding.

## [1.1.0] - 2021-09-27
### Added
- Added https client. This avoids having to enable a different extension to do https.

## [1.0.2] - 2021-06-16
### Fixed
- Catch error when unregistering the client when it has not been registered previously.

## [1.0.1] - 2021-05-25
### Changed
- Updated project structure to most recent template standard.

## [0.1.0] - 2020-09-17
### Added
- Initial commit.

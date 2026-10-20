# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.2] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.3.1] - 2024-05-29
### Fixed
- Fix test access to `middleware.options` or `middleware.kwargs` (backward compat with FastAPI)

## [1.3.0] - 2023-04-05
### Fixed
- Fix intermittent test failure due to lack of wait for server shutdown

## [1.2.1] - 2023-02-28
### Updated
- Add missing super().__init__() calls required for Python 3.10

## [1.2.0] - 2023-01-24
### Changed
- Add support for CORS. See README for details.

## [1.1.2] - 2022-04-06
### Changed
- Moved slow import statements to be local to improve Kit startup times

## [1.1.1] - 2021-10-23
### Changed
- Updated iconography of Extension to match Omniverse Farm branding.

## [1.1.0] - 2021-09-27
### Added
- Initial https support into http server extension instead of individual https extension

## [0.1.0] - 2020-09-17
### Added
- Initial commit.

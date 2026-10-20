# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.10] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.0.9] - 2024-05-06
### Changed
- Bump version number to pick up new upstream pip modules.

## [1.0.8] - 2023-05-23
### Changed
- Fix minor python issues preventing kit xr tests to pass

## [1.0.7] - 2023-05-05
### Changed
- Reset zeroconf version from 0.56.0 to 0.40.1 due to build issues

## [1.0.6] - 2023-04-17
### Changed
- persist added Zeroconf objects until removed; update Zeroconf library from 0.40.1 to 0.56.0

## [1.0.5] - 2023-04-05
### Changed
- broadcast to the interface bound to each IP

## [1.0.4] - 2023-03-31
### Changed
- Added exception-handling for the case where the app terminates abnormally and leaves zeroconf objects registered

## [1.0.3] - 2023-03-27
### Changed
- Now publishes (and un-publishes) on all valid IP interfaces (wifi, ethernet, etc)

## [1.0.2] - 2023-03-14
### Changed
- Ensure unique version number for MR, since 1.0.1 was published pre-MR

## [1.0.1] - 2023-03-07
### Added
- Added info logging via carb.log_info()

## [0.1.0] - 2023-01-12
### Added
- Initial commit.

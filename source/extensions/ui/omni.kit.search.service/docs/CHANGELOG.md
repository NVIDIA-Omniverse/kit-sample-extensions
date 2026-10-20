# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.13] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: handle cancelled searches and release their lifetime objects on every exit path.

## [0.1.12] - 2023-10-27
### Updated
- updating DeepSearch specific imports

## [0.1.11] - 2023-10-13
### Updated
- tests to improve test coverage

## [0.1.10] - 2023-10-11
### Updated
- updated ``omni.kit.ngsearch`` service import for compatibility with extension version ``0.3.0+``

## [0.1.9] - 2023-06-22
### Fixed
- Fixed capabilities for the Nucleus Search service
- kit 105 update

## [0.1.8] - 2023-06-02
### Added
- show only one warning per server connection failure

## [0.1.7] - 2023-03-20
### Updated
- Fix async mock in test to work with python 3.10

## [0.1.6] - 2023-03-17
### Updated
- Update search service and idl packages.
- Update get_prefixes to work for nucleus search service

## [0.1.5] - 2022-06-29
### Updated
- Moved to external repository

## [0.1.4] - 2022-06-23
### Updated
- Make use of new ngsearch api extension.

## [0.1.3] - 2022-05-13
### Added
- Switch search to find2.
- Prevent transport error when get_prefixes and search happen at the same time.

## [0.1.2] - 2022-05-04
### Added
- Return search results asynchronously

## [0.1.1] - 2022-03-08
### Added
- Added get_prefixes for the extended search field.

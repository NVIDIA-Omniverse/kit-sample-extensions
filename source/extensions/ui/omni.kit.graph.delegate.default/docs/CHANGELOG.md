# Changelog

Default Delegate for Graph View

## [1.2.6] - 2026-03-06
### Fixed
- OMPE-84863: omni.kit.graph.delegate.default test failed in DGXC

## [1.2.5] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.2.4] - 2025-09-22
### Changed
- OMPE-64395: omni.kit.graph.delegate.default needs ui.Menu & ui.Separator to use menu_compatibility=False

## [1.2.3] - 2025-09-03
### Changed
- Update test to always hide the main menubar to avoid golden image test failures.

## [1.2.2] - 2024-01-22
### Changed
- Just bumping the version to try to fix a potentially bad publish

## [1.2.1] - 2023-11-22
### Added
- Added tests to increase the code coverage

## [1.2.0] - 2023-11-09
### Changed
- Added foreground optional arg to connection method, for curve anchor drawing

## [1.1.2] - 2023-10-17
### Fixed
- Refactor to new API avoiding assumption that GPU texture handle has an infinite lifetime.

## [1.1.1] - 2023-06-20
### Fixed
- Updated golden image because of new preview images in aws

## [1.1.0] - 2023-04-13
### Changed
- Updated for Python 3.10

## [1.0.18] - 2022-09-08
### Fixed
- Give test more time for material render

## [1.0.17] - 2022-08-24
### Fixed
- Fix tests with new kit-sdk

## [1.0.16] - 2022-07-06
### Fixed
- The connection disappear since the second connection is overriding the previous one

## [1.0.15] - 2022-03-30
### Changed
- update repo_build and repo-licensing

## [1.0.14] - 2022-03-11
### Fixed
- default test

## [1.0.13] - 2022-01-17
### Changed
- Conform backdrop size unit

## [1.0.12] - 2021-12-09
### Changed
- Revert the previous style changes since it breaks the material editor

## [1.0.11] - 2021-12-06
### Added
- Some style changes to make the switch delegates working for the graph demo

## [1.0.10] - 2021-06-01
### Added
- Support for GPU ID from the model allows to put viewport to preview

## [1.0.9] - 2021-05-19
### Changed
- Shorter connection tooltips

## [1.0.8] - 2021-05-19
### Changed
- Using old style icons for collapsed nodes

## [1.0.7] - 2021-05-15
### Changed
- Minor design improvements

## [1.0.6] - 2021-05-14
### Fixed
- FreeLine tooltips

## [1.0.5] - 2021-05-12
### Fixed
- +/- icon

## [1.0.4] - 2021-05-12
### Changed
- Better raster icons support

## [1.0.3] - 2021-05-11
### Fixed
- Color of ports when using display_color

## [1.0.2] - 2021-05-07
### Changed
- Hotfix when importing compount with backdrop inside

## [1.0.1] - 2021-05-06
### Changed
- Extracted from omni.kit.widget.graph
- Design improvements

# CHANGELOG

This document records all notable changes to ``omni.curve.manipulator`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`.

## [110.0.2] - 2026-10-17

### Changed

- Republish through the verified Windows signing path with signed package metadata.

## [Unreleased]
### Fixed
- The test block no longer lists `omni.kit.renderer.core`, which `omni.debugdraw` already brings: omni.kit.test's
  sanity check refused the test process ("already a dependency"), so the extension's startup test never ran.

## [110.0.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: replace removed viewport utility headers with the supported viewport interface.

## [110.0.0] - 2025-12-10
### Changed
- Updated for Kit 110.

## [107.0.1] - 2025-03-13
### Changed
- Enable Arm Builds

## [107.0.0] - 2025-02-05
### Changed
- Updated for Kit 107. Recompiled with ABI=1.

## [105.0.5] - 2024-09-09
### Changed
- OMPE-20562: Fix deprecated usage for IStageUpdate interface.

## [105.0.4] - 2023-07-25
### Changed
- Remove unused carb header and republish.

## [105.0.3] - 2023-03-22
### Changed
- Republish after USD/python update.

## [105.0.2] - 2023-03-21
### Changed
- Republish after USD/python update.

## [105.0.1] - 2023-03-14
### Changed
- Republish after USD/python update.

## [105.0.0] - 2022-11-16
### Changed
- Update for upstream dependencies.

## [104.1.2] - 2022-09-30
### Changed
- Incrementing extension version.

## [104.1.1] - 2022-08-01
### Fixed
- Fixed waiver in extension.toml.

## [104.1.0] - 2022-04-13
### Changed
- Support pencil tool in Viewport 2.0.

## [104.0.1] - 2022-04-11
### Changed
- Worked around bad dependency from `omni.debugdraw`.

## [104.0.0] - 2022-01-27
### Added
- Added writeTarget to extension.toml

## [1.0.1] - 2021-12-02
### Changed
- Made dependencies on `omni.kit.window.viewport` optional.

## [1.0.0] - 2021-11-08
### Added
- Initial commit.

# Changelog
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [110.0.2] - 2026-10-17

### Changed

- Republish through the verified Windows signing path with signed package metadata.

## [110.0.1] - 2026-10-16
### Changed
- The tests no longer depend on `omni.hydra.usdrt_delegate`, which Kit 111 does not have. The published 110.0.0 still
  required it.

## [110.0.0] - 2025-12-10
### Changed
- Updated for Kit 110.

## [107.0.2] - 2025-07-01
### Changed
- Removed deprecated use of `AsyncTestCaseFailOnLogError`.

## [107.0.1] - 2025-03-13
### Changed
- Enable Arm Builds

## [107.0.0] - 2025-02-05
### Changed
- Updated for Kit 107. Recompiled with ABI=1.

## [105.1.16] - 2024-12-06
### Fixed
- Fixed delete with new[].

## [105.1.15] - 2023-11-30
### Fixed
- Regenerate test golden data.

## [105.1.14] - 2023-10-05
### Fixed
- Added omni.usd dependency.

## [105.1.13] - 2023-08-15
### Fixed
- Added omni.kit.commands dependency.

## [105.1.12] - 2023-06-27
### Fixed
- Added omni.ui dependency.

## [105.1.11] - 2023-05-22
### Changed
- Republish.

## [105.1.10] - 2023-05-05
### Changed
- Removed unnecessary dependency on omni.kit.window.property.

## [105.1.9] - 2023-03-22
### Changed
- Republish after USD/python update.

## [105.1.8] - 2023-03-21
### Changed
- Republish after USD/python update.

## [105.1.7] - 2023-03-14
### Changed
- Republish after USD/python update.

## [105.1.6] - 2023-02-07
### Changed
- Republish.

## [105.1.5] - 2023-01-11
### Changed
- Republish.

## [105.1.4] - 2022-11-16
### Changed
- Update for upstream dependencies.

## [105.1.3] - 2022-11-07
### Changed
- Bugfix.

## [104.1.3] - 2022-11-01
### Changed
- Bugfixes.

## [104.1.2] - 2022-10-17
### Changed
- Added function to sample a float array from given key values, rather than USD attributes.

## [104.1.1] - 2022-09-30
### Changed
- Incrementing extension version.

## [104.1.0] - 2022-09-28
### Changed
 - Fixed a bug where values after the last key were undefined
 - Removed an old debug print
 - Added option to have the range always be fixed from 0..1 both vertically and horizontally
 - Added a parameter to pass a custom style for the graph itself
 - Placed a ui.Rectangle behind the graph so the background color can be customized
 - Disabled all mouse-inputs if the widget is disabled (The Placer is still draggable, but that needs to be fixed in omni.ui)

## [104.0.8] - 2022-08-15
### Changed
- Update test.

## [104.0.7] - 2022-08-04
### Added
- Tests.

## [104.0.6] - 2022-07-08
### Fixed
- Remove use of OpenMP since libraries are not bundled with extension.

## [104.0.5] - 2022-07-07
### Added
- get_float_array_as_rgba8_2 to generate bitmap without USD

## [104.0.4] - 2022-05-03
### Fixed
- rgb test.

## [104.0.3] - 2022-04-28
### Fixed
- Tests now run on TC.

## [104.0.2] - 2022-04-27
### Fixed
- Initial placement of ramp key

## [104.0.1] - 2022-04-25
### Added
- Tests.

## [104.0.0] - 2022-01-27
### Changed
- Bump version to 104.

## [103.0.5] - 2021-11-08
- Config changes for ETM.

## [103.0.4] - 2021-10-25
- Force update of new version

## [103.0.3] - 2021-09-29
DS2 specific additions.

## [103.0.2] - 2021-08-06
Bugfixes.

## [103.0.1] - 2021-06-08
Bugfixes.

## [103.0.0] - 2021-06-23
Point to kit-sdk version 103

## [102.1.2] - 2021-06-21
Recompile.

## [102.1.1] - 2021-06-02
Recompile.

## [102.1.0] - 2021-05-25
Rename.

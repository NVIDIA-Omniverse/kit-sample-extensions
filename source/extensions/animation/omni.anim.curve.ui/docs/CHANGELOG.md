# Changelog

## [111.0.0] - 2026-10-12
### Changed
- Depends on `omni.anim.curve.core` 111.0.0, KSE's version line for Kit 111 (it was `1.1.3`, which accepts only 1.x).
  The version moves with it so the published manifest changes under a new id.

## [1.7.0] - 2025-12-15
### Changed
- Updated kit-sdk version

## [1.6.1] - 2025-10-22
### Changed
- Updated tests to guarantee property widgets ordering.

## [1.6.0] - 2025-09-18
### Changed
- Updated kit-sdk version

## [1.5.3] - 2025-08-13
### Changed
- Update menu logic to use omni.kit.menu.utils

## [1.5.2] - 2025-07-16
### Changed
- Replace omni.renderer_capture to omni.kit.renderer_capture

## [1.5.1]
### Changed
- Updated visual test base for improved test infrastructure

## [1.5.0]
### Changed
- Upgraded the Kit SDK to 108
-
## [1.4.1]
### Changed
- Upgraded the Kit SDK to 107.3.
### Fixed
- Fixed test errors caused by new Kit SDK.

## [1.4.0]
### Changed
- Upgrade the Kit SDK to 106.4
-
## [1.3.17]
### Changed
- Remove AnimationSchemaTools deprecation warning.

## [1.3.16]
### Changed
- Reformat all source with repo format.

## [1.3.15]
### Added
- Added omni.usd.schema.anim to dependencies.

## [1.3.14]
### Fixed
- OM-122557: Collapse not targeted tabs in the property window to fix the ETM issue

## [1.3.13]
### Fixed
- fixed dependence

## [1.3.12]
### Changed
- Remove context menu entries from variant editor

## [1.3.11]
### Added
- Added get instance API for curve editor to enable the simplification menu

## [1.3.10]
### Fixed
- Fixed OM-119444 that omni.anim.curve.ui unit tests failed in kit ETM test

## [1.3.9]
### Added
- Added new unit tests
### Changed
- Avoided error window name collision
- Enlarge the simplification menu to avoid the scroll bar

## [1.3.8]
### Changed
- Enabled the skipped unit tests

## [1.3.7]
### Changed
- Updated kit-sdk version

## [1.3.6] - 2023-11-27
### Changed
- Updated kit-sdk version

## [1.3.5] - 2023-09-26
### Fixed
- Fixed OM-103554 that set/remove/copy/paste key behaviors are not supported when selecting multiple objects

## [1.3.4] - 2023-09-21
### Fixed
- Fixed OM-107210 that context menu entries are enabled for attributes that are not supported.

## [1.3.3] - 2023-08-30
### Changed
- Removed "Keep time samples" option from the conversion menu

## [1.3.2] - 2023-08-23
### Changed
- Uses omni.anim.curve.core instead of omni.anim.curve.

## [1.3.1] - 2023-08-16
### Fixed
- Crash in time sample conversion and simplification UI

## [1.3.0] - 2023-07-24
### Fixed
- Keyframing multiple prims together feature from the property window
-
## [1.2.0] - 2023-04-26
### Fixed
- Context menu past animation back to work
-
## [1.1.0] - 2023-04-18
### Changed
- Try to keep the original curve shape when the default tangent type is auto
-
## [1.0.0] - 2023-04-07
### Added
- initialize version

# Changelog

## [111.0.2] - 2026-10-19
### Fixed
- Resolve Kit extension build dependencies through the selected kernel or SDK layout.

## [111.0.1] - 2026-10-18
### Changed
- Republish through the Windows signing workflow with verified signing metadata for public registry validation.

## [111.0.0] - 2026-10-12
### Changed
- KSE's version line for Kit 111. Kit 111's animation lock builds upstream animation-authoring's `omni.anim.curve.core`
  1.6.2 (with Kit's patch), a different package under the version this copy had, and KSE publishes this copy to Kit 111's
  `kit/default`, where upstream's own 1.x releases for Kit 111 would also land under the same ids. 111.0.0 is outside
  upstream's 1.x line, so the two can no longer share an id or tie in the extension manager.

## [1.6.2] - 2026-10-06
### Fixed
- Kit 111: the AnimCurve node no longer crashes when it sets its target prim. Kit 111 provides no Fabric stage
  reader/writer, and the node dereferenced the missing interface. It now writes the values to the session layer
  through USD, where the Fabric write-back put them before.
- The AnimCurve node also drives targets without a default value (e.g. only time samples) and works when the
  extension is enabled after the stage was opened.

## [1.6.1] - 2026-07-24
### Fixed
- Fixed Pre/Post Cycle infinity types not surviving stage save and reload when curve data is stored on Push Graph curve nodes.

## [1.6.0] - 2025-12-15
### Changed
- Updated kit-sdk version

## [1.5.3] - 2025-12-08
### Fixed
- Fixed ALT+S to add key

## [1.5.2] - 2025-11-17
### Changed
- publish new version

## [1.5.1] - 2025-10-22
### Changed
- Updated kit-sdk version

## [1.5.0] - 2025-09-18
### Changed
- Updated kit-sdk version

## [1.4.4] - 2025-08-29
### Fixed
- Fixed a bug that animation can't be added when there is another prim with animation.

## [1.4.3] - 2025-07-22
### Changed
- Excluded the FSD related error messages from log erro checker

## [1.4.2] - 2025-07-16
### Changed
- Replace omni.renderer_capture to omni.kit.renderer_capture

## [1.4.1]
### Changed
- Updated visual test base for improved test infrastructure

## [1.4.0]
### Changed
- Upgrade Kit SDK to 108
-
## [1.3.3]
### Changed
- Upgrade Kit SDK to 107.4

## [1.3.2]
### Changed
- Fix Nvbug 5335422 always use Fabric Shared type to create OmniGraph for animation curve node

## [1.3.1]
### Changed
- Update to support Arm

## [1.3.0]
### Changed
- Upgrade Kit SDK to 107

## [1.2.0]
### Changed
- Upgrade Kit SDK to 106.4

## [1.1.14]
### Changed
- Remove AnimationSchemaTools deprecation warning.

## [1.1.13]
### Changed
- Add support level to package.

## [1.1.12]
### Changed
- Reformat all source with repo format.

## [1.1.11]
### Added
- Added omni.usd.schema.anim to dependencies.

## [1.1.10]
### Added
- Added more unit tests
### Changed
- Ignored some unused code from the test coverage

## [1.1.9]
### Added
- Add more unit tests

## [1.1.8]
### Fixed
- [OM-119133] Curve simplification results in the appearance of new curves that are empty
- [OM-119135] Simplifying prims without translate, rotate, and scale attributes lead to errors
- [OM-119134] USD timesample to curve conversion doesn’t work on xformOp:transform

## [1.1.7]
### Fixed
- [OMPRW-638]Fixed a bug that sometimes graph nodes can't be deleted.

## [1.1.6]
### Changed
- Disable the threadSafe flag to avoid the crashes

## [1.1.5]
### Changed
- Updated kit-sdk version

## [1.1.4] - 2023-11-27
### Changed
- Updated kit-sdk version

## [1.1.3] - 2023-09-21
### Fixed
- Fixed OM-107210 that context menu entries are enabled for attributes that are not supported.

## [1.1.2] - 2023-09-12
### Fixed
- Fixed the bug that a curve is not deleted when the last key is deleted.

## [1.1.1] - 2023-09-06
### Changed
- Added a setting to control whether a curve is deleted when the last key is deleted.

## [1.1.0] - 2023-09-01
### Changed
- Use new curve node type name.

## [1.0.1] - 2023-08-30
### Changed
- Removed "clear_dense_data" option from the conversion command.

## [1.0.0] - 2023-08-24
### Changed
- Renamed from omni.anim.curve to omn.anim.curve.core.

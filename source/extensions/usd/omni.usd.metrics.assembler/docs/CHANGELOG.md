# Changelog

## [110.1.3] - 2026-10-16
### Changed
- Issue a fresh package for verified Windows signing and signed publication metadata.

## [110.1.2] - 2026-04-01
### Changed
- Removed unused built-in rules resolution from plugin metadata. Attribute resolution now only uses explicitly registered custom rules.
- Skip deep hierarchy traversal and prune subtrees when no custom rules or callbacks are registered, only resolving xformOps on top-level divergent prims.

## [110.1.1] - 2026-04-01
### Changed
- Kit SDK Update

## [110.1.0] - 2026-02-13
### Changed
- Kit SDK Update

## [109.1.0] - 2025-10-15
### Changed
- Kit SDK Update

## [109.0.0] - 2025-10-14
### Changed
- Kit SDK Update

## [108.0.0] - 2025-06-12
### Changed
- Kit SDK Update

## [107.2.0] - 2025-04-02
### Changed
- Kit SDK Update
- Metrics Assembler Added support to change stage units through change_stage_units

## [107.1.0] - 2025-03-19
### Changed
- Kit SDK Update
- Metrics Assembler Conform To XformCommonAPI option added
- Register custom attribute processing now takes a list of attribute tokens to resolve perf issues when all attributes were passed to python to process.

## [107.0.1] - 2025-01-07
### Changed
- Kit SDK Update

## [107.0.0] - 2024-12-13
### Changed
- Kit SDK Update

## [106.4.0] - 2024-10-29
### Changed
- Kit SDK Update

## [106.3.0] - 2024-09-30
### Changed
- Kit SDK Update

## [106.2.0] - 2024-09-30
### Changed
- Kit SDK Update

## [106.1.0] - 2024-07-24
### Changed
- Kit SDK Update

## [106.0.1] - 2024-02-26
### Changed
- Kit SDK Update

## [106.0.0] - 2024-01-15
### Changed
- Kit SDK Update

## [105.2.3] - 2024-01-15
### Changed
- Kit SDK Update

## [105.2.2] - 2023-10-17
### Changed
- Removed physics schema dependency

## [105.2.1] - 2023-10-09
### Changed
- Merged fixes from 2023.2 release

## [105.2.0] - 2023-08-07
### Changed
- Kit SDK Update

## [105.1.8] - 2023-10-06
### Changed
- Fixed issue with not finding correctly divergent layers when units were close to each other (cm vs mm)

## [105.1.7] - 2023-10-05
### Changed
- Fixed issue with attributes authored in higher layers

## [105.1.6] - 2023-10-02
### Changed
- Removed debug prints from extension startup/shutdown

## [105.1.5] - 2023-06-06
### Changed
- XformOp pivot invert applied as last

## [105.1.4] - 2023-06-06
### Changed
- Exposed setting for gizmo axis

## [105.1.3] - 2023-04-28
### Changed
- Issue error for Scene graph instanced prims

## [105.1.2] - 2023-04-26
### Changed
- Kit write target

## [105.1.1] - 2023-04-24
### Changed
- Kit write target

## [105.1.0] - 2023-04-14
### Changed
- SDK update

## [105.0.8] - 2023-04-03
### Changed
- SDK update

## [105.0.7] - 2023-04-03
### Changed
- Time sampled values support added
- Recursive resolve

## [105.0.6] - 2023-03-22
### Changed
- Only repacking

## [105.0.5] - 2023-03-16
### Changed
- USD update

## [105.0.4] - 2023-02-16
### Changed
- RotateX op applied before or after properly

## [105.0.3] - 2023-02-02
### Changed
- Added dependency on the metrics assembler schema, this will require app restart

## [105.0.2] - 2023-01-27
### Changed
- XformOp changes are done to the current edit target instead of the provided.

## [105.0.1] - 2023-01-20
### Added
- Units information to the mismatched units dialog.
- Enabled rotation adjustments.

## [105.0.0] - 2023-01-17
### Added
- Initial implementation

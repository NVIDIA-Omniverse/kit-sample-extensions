# Changelog

## [110.1.3] - 2026-05-28
### Fixed
- MetricsAssemblerUI.on_shutdown was clearing a misspelled attribute (_stage_event_subs) instead of the real subscription list (_stage_event_sub), leaking event-dispatcher subscriptions on every extension reload (OMPE-91950 / NVBug 6118163).

## [110.1.2] - 2026-05-05
### Fixed
- NVBug 6104092: Viewport unit overlay (cm/dm/m/km/mm/in/ft/mi) now updates in realtime when the stage's `metersPerUnit` is changed (e.g. via the Default Meters Per Unit preference slider). Added a direct `Usd.Notice.ObjectsChanged` listener so changes reported at the absolute root path are caught regardless of whether USD reports them as resync or info-only. Also post a WARNING notification telling the user that only the unit metadata was updated — object positions and sizes are NOT auto-converted.

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
- The viewport part is now optional

## [107.1.0] - 2025-03-19
### Changed
- Kit SDK Update

## [107.0.1] - 2025-01-07
### Changed
- Kit SDK Update

## [107.0.0] - 2024-12-13
### Changed
- Kit SDK Update

## [106.4.0] - 2024-10-29
### Changed
- Kit SDK Update

## [106.3.1] - 2024-10-02
### Changed
- Add 'dm' to known units, and hide the meters per unit widget when meters per unit is unknown.

## [106.3.0] - 2024-09-30
### Changed
- Kit SDK Update

## [106.2.0] - 2024-09-30
### Changed
- Kit SDK Update

## [106.1.0] - 2024-07-24
### Changed
- Kit SDK Update

## [106.0.2] - 2024-02-26
### Changed
- Kit SDK Update

## [106.0.1] - 2024-01-19
### Changed
- Removed physics dependency from tests

## [106.0.0] - 2024-01-15
### Changed
- Kit SDK Update

## [105.2.5] - 2024-01-15
### Changed
- Kit SDK Update

## [105.2.4] - 2023-10-24
## Fix
- Merged fixes from release 2023.2

## [105.2.3] - 2023-10-09
## Fix
- Merged fixes from release 2023.2

## [105.2.2] - 2023-08-30
## Fix
- OM-107163: Units should be in Show By Type

## [105.2.1] - 2023-08-08
### Changed
- Fixed issue when non USD fileformat objects were drag and dropped into stage window

## [105.1.18] - 2023-10-20
- Resolved issue when adding reference multiple times to default prim.

## [105.1.17] - 2023-10-06
- Added checks for adding reference/payload to already existing prim references/payloads or if prim already does have childs

## [105.1.16] - 2023-10-05
- Fixed recursive metrics assembler layer loading

## [105.1.15] - 2023-10-05
- Fixed ask to resolve dialog

## [105.1.14] - 2023-10-03
- Fixed move prim command

## [105.1.13] - 2023-10-02
- Removed unused window

## [105.1.12] - 2023-10-02
- Removed implicit omni.usd.metrics.assmebler.physics dependency

## [105.1.11] - 2023-09-26
- Units visualization toggle moved to Show by type
- Resolved issue when drag and dropping non USD native fileformat files

## [105.1.10] - 2023-08-07
- Changed metadata version
- Fixed issue we stale reference url

## [105.1.8] - 2023-06-29
- Prim duplication correctly update units

## [105.1.7] - 2023-06-05
- Layers are not opened if not existing
- Update layer url information when payload/reference changes

## [105.1.6] - 2023-05-24
- Do not create the metricsAssembler layer if not required

## [105.1.5] - 2023-05-05
- Correct metadata layer write

## [105.1.4] - 2023-04-28
- Correct metadata layer write

### Changed

## [105.1.3] - 2023-04-25
### Changed
- Version bump

## [105.1.2] - 2023-04-24
### Changed
- Kit write target

## [105.1.1] - 2023-04-17
### Changed
- Add support for addReference/addPayload

## [105.1.0] - 2023-04-14
### Changed
- SDK update

## [105.0.12] - 2023-04-04
### Changed
- Fixed load of resolved assets

## [105.0.11] - 2023-04-03
### Changed
- Layer name fix

## [105.0.10] - 2023-04-03
### Changed
- Resolve layer renamed to be unique
- Support for recursive resolve

## [105.0.9] - 2023-03-24
### Changed
- PrimMove hotfix

## [105.0.8] - 2023-03-22
### Changed
- IsMaster fix
- Removed layer rename

## [105.0.7] - 2023-03-16
### Changed
- USD update

## [105.0.6] - 2023-03-09
### Changed
- Fixed new stage issues
- Removing all references removes the resolve layer
- Rename prim is handled correctly

## [105.0.5] - 2023-02-28
### Changed
- Added support for drag and drop to stage window
- Changed resolve of references/payloads to end up in a single layer
- Added support for reference/payload delete

## [105.0.4] - 2023-02-16
### Changed
- Fixed drag and drop for simReady browser
- Added support for resync changes

## [105.0.3] - 2023-02-02
### Added
- Save/load resolved values into the anonymous layers
- Dependency on the metrics assembler schema will require app restart, enable from start

## [105.0.2] - 2023-01-27
### Added
- Added units information into bottom left corner.
- Parameters are resolved into individual anonymous sublayers.
- Fixed issue when drag and dropped object ended with a digit.

## [105.0.1] - 2023-01-20
### Added
- Units information to the mismatched units dialog.
- Enabled rotation adjustments.
- Removed layer information.

## [105.0.0] - 2023-01-17
### Added
- Initial implementation.

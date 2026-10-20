# CHANGELOG

This document records all notable changes to ``omni.kit.browser.material`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.7.0] - 2026-08-27
### Changed
- OMPE-101618: materials are read off the main thread, so a slow file no longer costs the app its
  frames - `usd_reader.threaded`, on by default.

### Fixed
- OMPE-101618: a file naming an unreachable server no longer freezes the scan for
  minutes.

## [1.6.6] - 2026-04-13
### Changed
- OMPE-80520: Do not show as material if no materials found in usd file

## [1.6.5] - 2025-08-27
### Changed
- Use local file for test

## [1.6.4] - 2025-08-01
### Changed
- Set pick model to "type:ALL" for "Select Bound Objects" test with GeomSubSet

## [1.6.3] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [1.6.3] - 2025-04-14
### Changed
- Fix doc build issues.

## [1.6.2] - 2025-04-14
### Removed
- Usage and checks for legacy Viewport

## [1.6.1] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [1.6.0] - 2024-08-29
### Change
- OMPE-20088: Subscribe to enabled setting to enable/disable window and menu item

## [1.5.4] - 2024-08-19
### Change
- Use omni.usd.is_prim_material_supported before binding material to prim

## [1.5.3] - 2024-08-19
### Change
- OMPE-15107: Bind material if necessary when dropping to stage

## [1.5.2] - 2024-04-08
### Change
- OM-80960: Drag and drop UX improvement for multiple descendent objects
- Version 1.5.2 has discontinued support for kit-105 and works with kit-106.x or later versions

## [1.5.1] - 2024-03-22
### Change
- OM-78918: Show single usd material with material name instead of file name

## [1.5.0] - 2024-03-06
### Change
- Use omni.kit.widget.stage.DragAndDropRegistry.register_drop_handler to handle drag/drop from material browser

## [1.4.9] - 2024-02-19
### Change
- OMPRW-834: There could be @ in file url, so use ? instead for sub material when dragging

## [1.4.8] - 2023-12-14
### Change
- Remove FSD flag from test arguments

## [1.4.7] - 2023-12-13
### Change
- Limit test window size to make sure the viewport position is fixed in Teamcity test machines

## [1.4.6] - 2023-12-13
### Change
- Workaround: Use fixed position since get_ui_position_for_prim returns wrong position when /app/useFabricSceneDelegate=True in Apollo ETM tests

## [1.4.5] - 2023-10-16
### Change
- Add more test coverage for omni.kit.browser.material, bringing it up to 85%

## [1.4.4] - 2023-10-11
### Change
- OM-108958: do not set donot cast_shadows for materials by default
- If defined folders for donot cast shadows, only set materials in defined folders. otherwise keep no change.

## [1.4.3] - 2023-08-25
### Change
- OM-89797: Update test to get item position from omni.ui widget instead of fixed value

## [1.4.2] - 2023-06-27
### Change
- OM-101709: Support material which has one sub material with a different name from file name

## [1.4.1] - 2023-06-27
### Change
- Cache new root folders during warmup

## [1.4.0] - 2023-06-14
### Changed
- OM-98241: New default folder

## [1.3.8] - 2023-04-10
### Changed
- Add more default arguments to MaterialBrowserModel

## [1.3.7] - 2023-04-09
### Changed
- OM-89816: Disable UI test

## [1.3.6] - 2023-02-26
### Changed
- Add "Select Bound Objects"

## [1.3.5] - 2023-02-02
### Changed
- Add omni.kit.ui_test for test dependency

## [1.3.4] - 2023-01-30
### Changed
- Update golden image

## [1.3.3] - 2023-01-04
### Changed
- OM-63093: Remove dialog when "Apply To Selected" is chosen and instead simply assign the material to all of the selected objects

## [1.3.2] - 2023-01-03
### Changed
- OM-77206: Add "--no-window" otherwise test always failed in kit 105

## [1.3.1] - 2022-12-01
### Changed
- OM-74540: Create materials in default prim instead of always "/World"

## [1.3.0] - 2022-11-05
### Changed
- Use new tree style

## [1.2.20] - 2022-10-05
### Changed
- Use fast shutdown for ETM Linux test failure

## [1.2.19] - 2022-10-01
### Changed
- Change test to be faster and flexiable to remote material changes

## [1.2.18] - 2022-09-22
### Changed
- OM-60914: use Use omni.kit.material.library.get_subidentifier_from_mdl to parse mdl file (slower but can parse mdl file with invalid chars)

## [1.2.17] - 2022-09-14
### Fixed
- Fix test_ui test from max recursion error

## [1.2.16] - 2022-09-09
### Fixed
- Use ui_test.emulate_mouse_drag_and_drop to fix ETM test failures

## [1.2.15] - 2022-08-30
### Fixed
- Removed unused viewport_legacy import as it may be causing problems with ETM

## [1.2.14] - 2022-08-29
### Fixed
- Refactored drag and drop tests to support both viewports

## [1.2.13] - 2022-08-03
### Fixed
- OM-56323: support model selection when drag and drop from material browser to VP2

## [1.2.12] - 2022-07-29
### Changed
- Use default strength when binding materials intead of "stronger than" always

## [1.2.11] - 2022-07-27
### Changed
- OM-56327: "/World/Looks" need be "Scope"

## [1.2.10] - 2022-06-25
### Changed
- Remove omni.kit.window.viewport

## [1.2.9] - 2022-06-19
### Added
- Drop to VP2

## [1.2.8] - 2022-05-27
### Fixed
- Apply to multiple selected prims from context menu
- DnD vMaterials to viewport

## [1.2.7] - 2022-05-03
### Changed
- Show selection dialog when drop to multiple descendents

## [1.2.6] - 2021-03-30
### Changed
- Republish for repo updates

## [1.2.5] - 2022-01-28
### Added
- Handle exception when parsing sub idendifiers
- Retry when timeout to get sub idendifiers

## [1.2.4] - 2021-10-12
### Changed
- Work for kit 102 release

## [1.2.3] - 2021-09-30
### Added
- Add setting for data timeout

## [1.2.2] - 2021-09-28
### Added
- Add timeout when reading sub material idendifiers

## [1.2.1] - 2021-09-03
### Added
- Show materials in sub folders

## [1.2.0] - 2021-08-18
### Added
- Make thumbnail generation and viewport be optional

## [1.1.6] - 2021-07-26
### Added
- Drag and drop kinds of material to viewport

## [1.1.5] - 2021-07-02
### Change window and menu name to "Material Browser"

## [1.1.4] - 2021-06-28
### Added
- Show "..." instead of category number after folder traverse done but sub material not loaded
- setting 'exts."omni.kit.browser.material".enabled' to show menu/window after startup

## [1.1.3] - 2021-06-17
### Added
- setting 'exts."omni.kit.browser.material".load_after_startup' to load data immediately after startup (for View)

## [1.1.2] - 2021-06-08
### Fixed
- Last 4 chars of sub material label are cropped

## [1.1.1] - 2021-05-29
### Added
- Export more interface
- Enable "Add to Stage"

## [1.1.0] - 2021-05-28
### Added
- Supprt vMaterials

## [1.0.9] - 2021-05-20
### Load folders after app startup

## [1.0.8] - 2021-05-14
### Removed
- Remove unused print

## [1.0.7] - 2021-05-12
### Added
- Settings for min/max thumbnail size

## [1.0.6] - 2021-05-11
### Added
- Support multi materials in usd file

## [1.0.5] - 2021-05-07
### Added
- Support usd material file
- Default material thumbnail
### Changed
- Match new omni.kit.browser.folder.core
- Change menu and window name
- Change dock position

## [1.0.4] - 2021-05-04
### Added
- Show/hide collection combobox and category view
- Options menu to add/remove collection, generate thumbnails for collection/category/detail

## [1.0.3] - 2021-05-01
### Added
- Search bar, require kit sdk 101.0+release.463.b7f1cf6f or later

## [1.0.2] - 2021-04-26
### Changed
- Use new zoombar

## [1.0.1] - 2021-04-23
### Added
- Thumbnail generation

## [1.0.0] - 2021-04-19
### Added
- First release

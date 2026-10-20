# CHANGELOG

This document records all notable changes to ``omni.kit.window.material`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.9.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: fall back to USD traversal when runtime material queries are unavailable.

## [1.9.0] - 2026-08-17
### Added
- OMPE-101618: the material library shows what a scan is doing - a spinner in the toolbar, and a
  progress window behind it.

## [1.8.0] - 2025-11-05
### Added
- Add setting "/exts/omni.kit.window.material/panel_mode" for current panel mode (readonly)

## [1.7.2] - 2025-09-06
### Changed
- OMPE-53325: More comamnds for creating reference/payload.

## [1.7.1] - 2025-08-20
### Changed
- OMPE-53325: Update stage materials when reference/payload created.

## [1.7.0] - 2025-08-14
### Changed
- OMPE-58000: Use Event 2.0

## [1.6.4] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [1.6.3] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [1.6.2] - 2024-08-29
### Changed
- OMPE-20088: Disable material browser window by default

## [1.6.1] - 2024-07-23
### Changed
- OMPE-14781: Added missing dependency "omni.kit.notification_manager"

## [1.6.0] - 2024-06-07
### Changed
- UsdMaterialAttributeWidget is changed to UsdShadeMaterialWidget in latest kit 107

## [1.5.7] - 2024-04-15
### Fix
- Replace MaterialLibraryExtension.create_material_and_assign with action for kit 107

## [1.5.6] - 2024-03-21
### Fix
- OM-122420: Replace deprecated API from omni.kit.UsdContext.get_layers to omni.kit.usd.layers.

## [1.5.5] - 2023-12-02
### Fix
- Disable usdrt test since it always failed in kit 105.2 integ-master in Linux (OM-116097)

## [1.5.4] - 2023-12-01
### Fix
- Add stdoutFailPatterns.exclude for test failures

## [1.5.3] - 2023-12-01
### Fix
- Skip usdrt stage mode test in Linux because it failed in kit 105.2 integ-master ETM test due to crash when exiting if run more than one test cases

## [1.5.2] - 2023-12-01
### Fix
- Fix ETM test failure with /app/useFabricSceneDelegate=1

## [1.5.1] - 2023-11-29
### Fix
- Broken extension when not run with UsdRt enable

## [1.5.0] - 2023-10-26
### Changed
- OM-83663: Optimize scene traversal for stage materials with usdrt

## [1.4.6] - 2023-10-26
### Fixed
- Disable any default ui.RasterPolicy that omni.ui is opting into.

## [1.4.5] - 2023-10-24
### Fixed
- Update to newer APIs to avoid using expired GPU texture.

## [1.4.4] - 2023-10-19
### Changed
- Updates menus to use actions

## [1.4.3] - 2023-10-20
### Changed
- OM-112613: Fix ETM failure in USD Explorer where FSD enabled by default

## [1.4.2] - 2023-10-18
### Changed
- Added settings to show/hide Capture thumbnail menu option.

## [1.4.1] - 2023-10-06
### Changed
- OMFP-1282: Increase code coverage to 87%.

## [1.4.0] - 2023-07-17
### Changed
- OM-92142: Material Property panel visible by default

## [1.3.6] - 2023-06-14
### Changed
- OM-98241: New default folder

## [1.3.5] - 2023-06-08
### Changed
- Added ability to pass custom root folder path into MaterialBrowserModel

## [1.3.4] - 2023-06-06
### Changed
- OM-97348: Fix search error when stage mode not enabled

## [1.3.3] - 2023-06-02
### Changed
- OM-96989: Default not build ui when startup

## [1.3.2] - 2023-04-12
### Changed
- Make stage_options_menu in extension instance work

## [1.3.1] - 2023-03-13
### Changed
- Export MaterialBrowserWidget to use in other window or ui.scene

## [1.3.0] - 2023-03-13
### Changed
- OM-85649: support of lazy load workflow in Create

## [1.2.0] - 2023-02-27
### Changed
- OM-83662: Only create stage widget in stage mode

## [1.1.4] - 2023-01-20
### Changed
- OM-78907: Fix typo of "materail"

## [1.1.3] - 2022-12-14
### Changed
- Added [[test]] arguments

## [1.1.2] - 2022-11-16
### Changed
- OM-72818: Adjust layout since default docked to Content

## [1.1.1] - 2022-11-10
### Changed
- Do not show window immediately after docked

## [1.1.0] - 2022-11-05
### Changed
- Update tests for new tree style

## [1.0.21] - 2022-09-21
### Changed
- Updated golden image because of Zoombar change.

## [1.0.20] - 2022-09-19
### Changed
- Renamed 2nd test class to not get stomped on by 1st one, adding more test coverage.

## [1.0.19] - 2022-06-15
### Changed
- OM-53298: Add library_options_menu/stage_options_menu to access options menu in material window

## [1.0.18] - 2022-06-02
### Added
- Add "Duplicate" in stage material context menu

## [1.0.17] - 2022-04-07
### Changed
- Reduce time to load stage materials in a large scene
### Added
- Add tests to stage material model

## [1.0.16] - 2022-03-30
### Changed
- Republish for repo updates

## [1.0.15] - 2022-03-16
### Fixed
- Add settings for main window, to configurate if it is visible at startup

## [1.0.14] - 2022-03-14
### Fixed
- Fix spell

## [1.0.13] - 2022-03-08
### Changed
- Show correct material menu with new omni.kit.material.library

## [1.0.12] - 2022-02-16
### Changed
- Remove print

## [1.0.11] - 2022-02-15
### Changed
- Use setting for include children in selected mode

## [1.0.10] - 2022-02-15
### Added
- OM-44819: Add option to show materials assigned to children

## [1.0.9] - 2021-12-14
### Changed
- OM-42125: rename "CUrrent Scene" to "Current Stage"

## [1.0.8] - 2021-12-08
### Added
- Fix destory to destroy typo

## [1.0.7] - 2021-10-26
### Changed
- Do not show instanceproxy materials

## [1.0.6] - 2021-09-30
### Added
- Add setting for data timeout

## [1.0.5] - 2021-08-21
### Fixed
- OM-37932: Hide material preview when nothing selected in SELECTED mode

## [1.0.4] - 2021-08-21
### Changed
- OM-36123: Need to wait for widgets with popup window (for example color picker) end edit before showing new materials

## [1.0.3] - 2021-08-19
### Changed
- Match omni.kit.widget.material_preview v1.0.2

## [1.0.2] - 2021-08-09
### Changed
- Popup and center material graph instead of dock if it is invisible

## [1.0.1] - 2021-07-23
### Removed
- Remove warning message when startup

## [1.0.0] - 2021-07-14
### Added
- Tooltips for toolbar buttons
### Changed
- Use onmi.kit.widget.material_preview instead of omni.kit.window.material_preview

## [1.0.0-beta.4.2] - 2021-07-08
### Added
- setting 'exts."omni.kit.browser.material".enabled' to show menu/window after startup
### Changed
- Change menu from “Window/Materials" to "Window/Browsers/Materials"

## [1.0.0-beta.4.1] - 2021-07-01
### Changed
- "Graph" button always unselected status
- Always popup material graph window
- Categorize the create new material menu
- Show different message in selected mode when asset without materials selected
- Window and menu name change to "Materials"

## [1.0.0-beta.4] - 2021-06-24
### Added
- Capture stage material thumbnail

## [1.0.0-beta.3.2] - 2021-06-22
### Changed
- Keep property visible/invisible even materials in stage changed
- Update navigation button text and image in stage view mode
- Show material graph editor in stage view mode if navigation button clicked (must enable omni.kit.window.material_graph first)

## [1.0.0-beta.3.1] - 2021-06-17
### Fixed
- Widgets size when resizing window
- Auto show/hide property when material selected/unselected

## [1.0.0-beta.3] - 2021-06-15
### Added
- Landscape mode
- Button in toolbar to show/hide property
- Empty notification in Selected mode if no materials selected

## [1.0.0-beta.2] - 2021-06-10
### Changed
- Window changed to "Material Editor"
- Always show property editor in "Current Scene" and "Selected" mode
- Always select an existing material in "Current Scene" and "Selected" mode
- Change the full-switch icon
- Use omni.kit.window.material_preview to show material thumbnail in full window mode with dynamic updating

## [1.0.0-beta.1] - 2021-05-29
### Added
- First beta

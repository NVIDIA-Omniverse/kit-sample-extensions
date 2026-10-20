# CHANGELOG

This document records all notable changes to ``omni.kit.window.section`` extension.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [107.2.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: release observer guards and stage listeners before shutdown.

## [107.2.0] - 2026-04-30
### Added
- Exposed `get_section_widget_prim` and `set_widget_position` as public API on extension instance
- Users can now call these methods via `get_instance()` without needing to know about SectionManager

## [107.1.3] - 2025-12-09
### Changed
- Fix issue where live session users were getting cross contaminated section placements
- Fix issue with selection state.
- Fix issue where the section plane model was not resetting properly.

## [107.1.2] - 2025-09-23
### Changed
- Remove unused test dependency omni.hydra.iray

## [107.1.1] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [107.1.0] - 2025-08-20
## Changed
- Update to event 2.0

## [107.0.6] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [107.0.5] - 2025-05-29
### Changed
- Fix "SyntaxWarning: invalid escape sequence" for python 3.12 used in kit 108

## [107.0.4] - 2025-05-22
### Fixed
- OMPE-47775: Disable denoiser, otherwise there will be error in ARM tests

## [107.0.3] - 2025-01-06
### Added
- Update public api

## [107.0.2] - 2024-11-28
### Fixed
- OMPE-27978: Update kit sdk to 107.

## [107.0.1] - 2024-04-10
### Fixed
- OMPE-1444: When hiding section manipulator, must clear selection state, otherwise viewport context menu may not work

## [107.0.0] - 2024-04-02
### Fixed
- Update for changes of SettingsWidgetBuilder in kit 107

## [105.1.11] - 2024-01-17
### Fixed
- OMFP-4068: Restore the correct context menu state

## [105.1.10] - 2023-11-16
### Changed
- OMFP-3552: Set current tool setting when Section window is shown.

## [105.1.9] - 2023-10-20
### Changed
- OMFP-2998: Restore the correct selection state when selection gets enabled and disabled again

## [105.1.8] - 2023-10-19
### Changed
- OMFP-2769: Section Tool Widget Is Visible To Others During Live, Should Not Be The Case

## [105.1.7] - 2023-10-19
### Changed
- OMFP-2711: Added tooltip for the Set Rotation

## [105.1.6] - 2023-10-17
### Changed
- Hide section tool prims in stage

## [105.1.5] - 2023-10-16
### Changed
- Hide the section window when tools are turned off

## [105.1.4] - 2023-10-13
### Changed
- Set default value of "Set Rotation" in "Quick Move" to 45 instead of rotation in new section

## [105.1.3] - 2023-10-12
### Changed
- OMFP-2189: Continue refine section window
- Update switch icons
- Remove the invert direction widget on the viewport gizmo
- Set default rotation to 45
- OMFP-2361: Section Manipulator should work with reset button

## [105.1.2] - 2023-10-11
### Changed
- Relocate changelog

## [105.1.1] - 2023-10-11
### Changed
- Section tool is not closed when another tool gets active

## [105.1.0] - 2023-10-10
### Changed
- OMFP-2189: Refine UI

## [105.0.11] - 2023-10-09
### Changed
- OMFP-1965: section tool must exit context entirely upon dialog closing

## [105.0.10] - 2023-10-05
### Changed
- OMFP-752: Disable section when deleting from stage panel and re-enable when first section added

## [105.0.9] - 2023-09-29
### Changed
- OMFP-1292 - Increase code coverage. Added additional tests and golden images.

## [105.0.8] - 2023-08-15
### Fixed
- OM-105218 - Updated golden images for testing.

## [105.0.7] - 2023-08-11
### Fixed
- OM-104863 - Set the scroll frame to generate via build_fn.

## [105.0.6] - 2023-08-10
### Fixed
- OM-104863 - Define Base size of window to prevent undocked window creation from improper sizing.

## [105.0.5] - 2023-07-31
### Fixed
- OM-102415 - Add scrollingframe to ui panel.

## [105.0.4] - 2023-07-26
### Fixed
- OM-102758 - Fixed Section tool showing in a newly opened scene regardless if a section is available.
### Changed
- Refactored Scene code to only require a single model -- refreshes on stage open event.

## [105.0.3] - 2023-05-10
### Fixed
- OM-95365 - Allow for slice options to function correctly when the manipulator visibility is disabled.

## [105.0.2] - 2023-05-10
### Fixed
- OM-93367 - Decoupled manipulator `visibility` and section `slice enabled` states.

## [105.0.1] - 2023-04-26
### Added
- OM-92222 - Added a toggle to only change the display of the maniulator plane and buttons while keeping the slice.

## [105.0.0] - 2023-04-18
### Fixed
- OM-90916 - Fixed Section tool appearing in next stage if open in previous stage
- OM-90917 - Fixed Section tool prims only appearing in Layers panel.
- OM-90919 - Fixed the ability to delete the section tool prims.

## [104.2.11] - 2023-03-30
### Fixed
- OM-85959 - Fixed Moving to Selection. Required Computing world bound versus local bound.
- OM-88315 - Fixed Rename issue when name change is made as a part of an upcoming sequence ID number.

## [104.2.10] - 2023-03-10
### Fixed
- OM-85153 - Fixed Section cloning. Additional case where cloning was broken after deleting a section.
- Fixed identifying unsupported characters in section rename. Automatically convert spaces to "_".
- Fixed typo in warning message when attempting to delete last remaining section.
- OM-85955 - Fixed using the Delete hotkey. Using this is not the intended way to remove a section.
- Fixed IndexError issue trying to delete a section after multiple are added.
- Fixed IndexError after deleting sections and pressing previous/next.
- Fixed ability to resize the section window when undocked.

## [104.2.9] - 2023-03-09
### Fixed
- OM-85152 - Fixed serialization of the section transforms
- Fixed Deleting a section auto creating a new one, and not transitioning to the next available section

## [104.2.8] - 2023-03-08
### Fixed
- OM-74950 - Hiding the grid for 104.2 ETM

## [104.2.7] - 2023-03-07
### Fixed
- OM-84284 - Fixed Snap to selected functionality
### Changed
- Prevented removal of section if it is the only section available. The tool relies on a section existing to operate.
- Golden Images updated for tests.

## [104.2.6] - 2023-02-27
### Changed
- OM-74183 - Updating test parameters to pass on windows (hopefully).

## [104.2.5] - 2023-02-23
### Changed
- Updated golden imgs for 105 update

## [104.2.4] - 2023-02-18
### Changed
- Changed to using `auto_resize` which means we don't have to prebuild the UI during startup.

## [104.2.2] - 2023-02-15
### Changed
- Removed frame scroll window as it was causing issue drawing the window at full size.

## [104.2.1] - 2023-02-14
### Fixed
- OM-82357: Section creation is now created based on the center view vector of the camera
- OM-82356: Transform gizmo now appers immediately after creation of a new section
- OM-82355: Updated ui scene visuals and made picking more responsive for the section

## [104.2.0] - 2023-01-30
### Changed
- Do not make stage dirty after stage opened

## [104.1.2] - 2022-12-12
### Changed
- Updated golden images and increased threshold

## [104.1.1] - 2022-11-24
### Changed
- Added test for iray mode

## [104.1.0] - 2022-11-11
### Changed
- Delay create window until show it, make extension startup faster

## [104.0.0] - 2022-10-19
### Fixed
- Fixed checkbox widgets

## [103.3.3] - 2022-08-08
### Fixed
- OM-58229: add setting for menu path

## [103.3.2] - 2022-08-01
### Fixed
- Compatiable old verison section widget

## [103.3.1] - 2022-07-21
### Fixed
- Fix remove section error message

## [103.3.0] - 2022-07-11
### Changed
- Support VP1/VP2
- test coverage

## [103.2.11] - 2022-07-06
### Changed
- Migrated to Tools menu

## [103.2.10] - 2022-06-30
### Fixed
- Fixed section cut direction combox width

## [103.2.9] - 2022-06-06
### Changed
- New section at center of selections

## [103.2.8] - 2022-06-06
### Fixed
- Fixed default cut direction
- Fixed section bar not move when rotate camera

## [103.2.7] - 2022-05-09
### Fixed
- Fixed position when changed active camera
- Hide section prim in stage window

## [103.2.6] - 2022-04-13
### Changed
- use existing transform manipulators on section widget

## [103.2.5] - 2022-03-30
### Changed
- Update repo_build and repo_licensing

## [103.2.4] - 2022-02-12
### Fixed
- fixed section widget fly away issue

## [103.2.3] - 2021-12-28
### Changed
- scale the section widget to same size

## [103.2.2] - 2021-12-22
### Changed
- Add current tool setting to make it cooperation with other tools

## [103.2.1] - 2021-12-14
### Changed
- fix some issues

## [103.2.0] - 2021-12-13
### Changed
- rewrite the section widget with ui.scene (need kit sdk 103.1.x)

## [103.1.2] - 2021-12-09
### Changed
- Updated the use of omni.kit.viewport to omni.kit.viewport_legacy

## [103.1.1] - 2021-11-26
### Removed
- Remove omni.kit.settings.

## [103.1.0] - 2021-09-27
### Fixed
- Update version.

## [102.1.8] - 2021-09-27
### Fixed
- Fix a crash issue with new kit sdk.

## [102.1.7] - 2021-09-22
### Fixed
- Fix a crash issue.

## [102.1.6] - 2021-08-23
### Changed
- Fix issue that rotation colokwise not work.

## [102.1.5] - 2021-08-20
### Changed
- Fix issue that cut direction is not loaded correctly.

## [102.1.4] - 2021-07-30
### Changed
- Build with kit 102.1.0+release.46052 since IViewport updated

## [102.1.3] - 2021-07-26
### Changed
- Default cut direction when new section

## [102.1.2] - 2021-07-26
### Changed
- Default setting of cut diretion and alignment

## [102.1.1] - 2021-06-30
### Fixed
- Enabled transform operator when press select section button

## [102.1.0] - 2021-06-28
### Changed
- Changed name to omni.kit.window.section
- Remove dependence of omni.kit.widgets.custom
- Support Create

## [0.1.0] - 2020-08-31
### Added
- Initial section tool implementation

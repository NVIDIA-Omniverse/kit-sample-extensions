# CHANGELOG

This document records all notable changes to ``omni.kit.waypoint.core`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.6.11] - 2026-10-15
### Changed
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then `pump_apply_usd_changes failed (12)` and `PUMP apply_usd_changes ... failed`). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

## [1.6.10] - 2026-07-06
### Fixed
- OMPE-100254, OMPE-95471, OMPE-95473, OMPE-100249: Prevented empty waypoint thumbnail data from being uploaded to `ByteImageProvider`, resolving the error introduced by OMPE-51864.

## [1.6.9] - 2026-04-09
### Fixed
- OMPE-74953: Prevented waypoint camera recall from copying internal `omni:ignorePrim` and camera exposure attributes such as `fStop` and `exposure:*` onto `/OmniverseKit_Persp`.

## [1.6.8] - 2026-02-06
### Changed
- OMPE-77101: Adding tests

## [1.6.7] - 2026-02-19
### Changed
- Changed ui.Image creation to fix flaky test

## [1.6.6] - 2026-02-23
### Fixed
- OMPE-81496: Fixed TypeError when building thumbnail with None image path

## [1.6.5] - 2026-02-04
### Changed
- OMPE-77101: Tweaking success check to avoid spurious warning

## [1.6.4] - 2026-01-30
### Changed
- OMPE-74953: omni.kit.waypoint.core capturing Render Settings.

## [1.6.3] - 2025-09-22
### Changed
- OMPE-64399: omni.kit.waypoint.core needs ui.Menu & ui.Separator to use menu_compatibility=False

## [1.6.2] - 2025-08-29
### Changed
- OMPE-63235: Fixed issue with crash in tests, don't check checkpoints dirtyness if stage is closing.

## [1.6.1] - 2025-08-29
### Changed
- Fixed issue with test failures when other extensions set "omni:rtx" or "exposure:" attributes on a camera

## [1.6.0] - 2025-08-21
### Changed
- Update to event 2.0

## [1.5.3] - 2025-08-18
### Changed
- Fix ETM test again.

## [1.5.2] - 2025-08-18
### Changed
- Fix ETM test.

## [1.5.1] - 2025-07-20
### Added
- Added thumbnail_path option

## [1.5.0] - 2025-07-11
### Changed
- Back to event 1.0 for kit 106 for remix toolkit and remove kit writeTarget

## [1.4.63] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [1.4.62] - 2025-05-07
### Changed
- OMPE-46767: ETM fixes

## [1.4.61] - 2025-05-02
### Changed
- Checking attribute validity before use, not sure why changing the renderer seems to have caused this to break.

## [1.4.60] - 2025-04-28
### Changed
- Set kit writeTarget and remove failing golden image tests due to RTX renderer.

## [1.4.59] - 2025-04-24
### Changed
- Changing renderer from PXR to RTX for OVC2 ETM support.

## [1.4.58] - 2025-01-06
### Added
- Update public api

## [1.4.57] - 2024-11-28
### Fixed
- OMPE-27978: update kit 107.

## [1.4.56] - 2024-10-10
### Added
- REMIX-3072: Fix for late `hide_in_stage_window` set

## [1.4.55] - 2024-08-30
### Added
- REMIX-3072: Added optional edit target for waypoints that overrides edit contexts

## [1.4.54] - 2024-07-29
### Changed
- OMPE-12031: Waypoint visibility on rename

## [1.4.53] - 2024-07-24
### Changed
- OMPE-15732: Remove "/app/useFabricSceneDelegate=1" from test args

## [1.4.52] - 2024-01-29
### Changed
- Updating waypoints to use have the option to use the viewport widget instead of window

## [1.4.51] - 2024-01-16
### Changed
- Fix test

## [1.4.50] - 2023-12-11
### Changed
- OMFP-3846: Fix markup rename and delete when live

## [1.4.49] - 2023-11-29
### Changed
- OMFP-3933: Fix waypoint rename and delete when live

## [1.4.48] - 2023-11-29
### Changed
- Always force to recall waypoint if active in playlist

## [1.4.47] - 2023-11-16
### Added
- OMFP-3552: State management fixes.

## [1.4.46] - 2023-11-07
### Fixed
- lack of stage was failing tests

## [1.4.45] - 2023-11-07
### Added
- OMFP-3464: Tests setting window UI and function.
- OMFP-3468: Tests the case that active camera is deleted.

## [1.4.44] - 2023-11-04
### Added
- OMFP-3471: Increase unit test coverage for the sunstudy setting is_dirty
- OMFP-3472: Increase unit test coverage for the sunstudy setting recall

## [1.4.43] - 2023-11-03
### Added
- OMFP-3469: Increase unit test coverage
- OMFP-3470: Increase unit test coverage

## [1.4.42] - 2023-11-03
### Added
- OMFP-3465: Increase unit test coverage
- OMFP-3474: Increase unit test coverage

## [1.4.41] - 2023-11-01
### Added
- OMFP-3458: Add tests for WaypointListWindow on_click and on_double_click
- OMFP-3457: Add test of clicking close button on WaypointListWindow

## [1.4.40] - 2023-11-01
### Fixed
- OM-106468: Turn off fast shutdown to fix test failed in linux with kit 105.2

## [1.4.39] - 2023-10-31
### Added
- OMFP-3459: Separate click and double-click tests in TestListWindow

## [1.4.38] - 2023-10-31
### Added
- Add action display name to show well in Actions/Hotkeys window

## [1.4.37] - 2023-10-27
### Fixed
- OMFP-3306: Automated Test: [waypoint] user cannot create notes in live session

## [1.4.36] - 2023-10-26
### Fixed
- OMFP-1021: Hotkey fixes.

## [1.4.35] - 2023-10-25
### Fixed
- OMFP-1287: Increase unit test coverage.

## [1.4.34] - 2023-10-24
### Fixed
- OMFP-3172: Remove prim visibility feature.

## [1.4.33] - 2023-10-24
### Fixed
- OM-106468: Attempting to fix some ETM tests.

## [1.4.32] - 2023-10-24
### Fixed
- OMFP-2645: Fix Add Waypoint whilst in edit mode

## [1.4.31] - 2023-10-23
### Fixed
- OMFP-1021: Hotkey updates

## [1.4.30] - 2023-10-23
### Fixed
- OMFP-2024: User message for duplicate waypoints

## [1.4.29] - 2023-10-20
### Fixed
- Fixed tests; moved waypointcard into core.

## [1.4.28] - 2023-10-20
## Fixed
- OMFP-2898: [waypoint] user cannot create notes in live session

## [1.4.27] - 2023-10-20
## Changed
- OMFP-2912 - Fixed bug where waypoints icons where not removed properly if the prim was deleted.

## [1.4.26] - 2023-10-20
## Changed
- OMFP-1021 - Added hotkeys.

## [1.4.25] - 2023-10-19
## Changed
- OMFP-2669 - Adjust button icons, layout and colors.

## [1.4.24] - 2023-10-18
## Changed
- OMFP-2558: Fix waypoint sync for participants

## [1.4.23] - 2023-10-17
## Changed
- OMFP-2699 - Simpler list window layout logic.

## [1.4.21] - 2023-10-17
## Fixed
- OMFP-2669: Adjusting button layout.

## [1.4.20] - 2023-10-17
## Fixed
- OMFP-2619: Fix duplicate waypoints

## [1.4.19] - 2023-10-16
## Fixed
- OMFP-2532: Fix failure to create initial waypoint

## [1.4.18] - 2023-10-13
## Fixed
- Test fix - check for valid stage.

## [1.4.17] - 2023-10-13
## Fixed
- OMFP-2125 - Tracking distance from edge of viewport for list windows.

## [1.4.16] - 2023-10-13
## Fixed
- Icon visibility

## [1.4.15] - 2023-10-13
## Fixed
- OMFP-2317 - Changed ignorePrimType type on data prims to ignorePrim attribute

## [1.4.14] - 2023-10-12
## Changed
- OM-112001 - Fix golden images for FSD (only)

## [1.4.13] - 2023-10-11
## Changed
- OMFP-2125 - Reseting the list window position when swapping between app modes.

## [1.4.12] - 2023-10-11
## Changed
- "OM-106439 & OM-106468 - Fixing an attribute change from PIL"

## [1.4.11] - 2023-10-10
## Changed
- OMFP-2241: Do not skip updating thumbnails during live.

## [1.4.10] - 2023-10-10
## Changed
- OMFP-747: Fix icon alignment

## [1.4.9] - 2023-10-10
## Changed
- Hide waypoint list window when tools are disabled

## [1.4.8] - 2023-10-10
## Changed
- OMFP-1287: Unit test coverage.

## [1.4.7] - 2023-10-09
## Changed
- OMFP-2212: add exception handling with baking prewview on an out-dated prim or stage

## [1.4.6] - 2023-10-06
## Changed
- OMFP-749: Manage playback state between Markup and Waypoint

## [1.4.5] - 2023-10-06
### Fix
- OMFP-1007 - Changed markup prim types to omni::ignorePrimType to avoid expensive FSD update

## [1.4.4] - 2023-10-04
## Changed
- OMFP-1025: Implement extensions state management for Waypoint

## [1.4.3] - 2023-10-03
## Changed
- OMFP-746: Allow resize of Waypoint list window

## [1.4.2] - 2023-09-29
## Changed
- OMFP-745: Save position of Waypoint list window

## [1.4.1] - 2023-09-29
### Fix
- Multiple crash fixes OMFP-1353, OMFP-1522

## [1.4.0] - 2023-08-30
## Changed
- OM-107163: Waypoint should be in Show By Type

## [1.3.35] - 2023-08-14
## Fix
- OM-105317 - Ensuring icon's are created even when they aren't visible.

## [1.3.34] - 2023-07-10
## Fix
- Fixed name of USD Presenter's sidecar extension.

## [1.3.33] - 2023-06-14
## Fix
- OM-98339 - Setting the rename window's raster policy to never.

## [1.3.32] - 2023-05-23
## Fix
- OM-95754 - Waypoint should ensure that the cameraLock attribute is disabled when saving or recalling a waypoint.

## [1.3.31] - 2022-04-24
## Fix
- OM-91910 - Adjusting the raster policy for the waypoint and markup thumbstrip.

[1.3.30] - 2022-04-18
## Fix
- OM-89920 - Fixing the waypoint and markup windows such that they don't keep recreating their playbars

[1.3.29] - 2022-04-18
## Removed
- Skip some unstable Linux tests

[1.3.28] - 2022-04-17
## Fix
- OM-90490: Remove positioner since it will block Viewport in USD Composer

[1.3.27] - 2022-03-09
## Fix
- OM-82418: Use the show/hide prim icon interface to show/hide all waypoint icons.

[1.3.26] - 2022-03-08
## Fix
- Version bumping because of publishing issues.

[1.3.25] - 2022-03-08
## Fix
- Ensuring that refreshed icons are clickable.

[1.3.24] - 2022-03-08
## Fix
- OM-79712 - Grabbing the user name, either from the current file, or `getpass.getuser()`

[1.3.23] - 2022-03-08
## Fix
- OM-84954 - Fix for waypoint icons being cleared constantly

[1.3.22] - 2023-03-06
## Fixed
- OM-83297 - Using proper highlight color when editing a waypoint.

[1.3.21] - 2023-02-27
## Improved
- OM-83104 - icons should refresh after leaving a live session.

[1.3.20] - 2023-02-27
## Changed
- Add argument to enable/disable recalling timeline when recalling waypoint

[1.3.18] - 2022-02-24
## Improved
- OM-84028 - Caching the thumbnail data to improve live sync times.

[1.3.17] - 2023-02-16
## Changed
- OM-82912 - Fixing a bunch of issues with the list window.

[1.3.16] - 2023-02-15
## Changed
- OM-80840 - Adding rename support to list window.

[1.3.15] - 2023-02-13
## Changed
- OM-80840 - Moved notes from waypoint browser into waypoint list window.

[1.3.14] - 2023-02-02
## Changed
- OM-80451: Do not recall new waypoint if created via Live mode

[1.3.13] - 2023-02-01
## Changed
- OM-80451: Live support for large scene

[1.3.12] - 2023-01-31
## Changed
- OM-80341: If waypoint root prim removed, need to refresh all waypoints
- OM-80331: Waypoint icon need to update while waypoint camera may changed

[1.3.11] - 2023-01-27
## Changed
- OM-77383: Notes should work again with waypoints.

[1.3.10] - 2023-01-20
## Changed
- OM-79083: Update checkbox style to be same as viewport menubar

[1.3.9] - 2023-01-18
## Changed
- Do not monitor prim change during waypoint creating
- Add more logs to recall and current waypoint change

[1.3.8] - 2023-01-11
- OM-53986: Remove defualt prim type of "Camera" for camera settings in waypoint
- OM-78104: Update waypoint settings window style

[1.3.7] - 2022-12-13
- Fix for None frame value, should default to zero in this case.

[1.3.6] - 2022-12-08
- Add sidecar reaonly logic

[1.3.5] - 2022-12-05
- Add sync mode to create waypoint

[1.3.4] - 2022-11-29
- Refactored sidecar support, hopefully to better leverage the sidecar extension.

[1.3.3] - 2022-11-21
## Changed
- Updated the base name for waypoints so they match markups.

[1.3.2] - 2022-11-15
## Changed
- Update golden images

[1.3.1] - 2022-11-10
## Changed
- OM-53986: Update waypoint settings default and reset button on prim visibility

[1.3.0] - 2022-11-03
## Added
- Support sidecar for View

[1.2.1] - 2022-09-28
## Updated
- Updated tests, and golden images.

[1.2.0] - 2022-09-14
## Improved
- OM-54871: Checking prim visibility changes on stage update callback instead traverse all prims to improve performance

[1.1.5] - 2022-09-06
## Improved
- Setting the scrollbars to be "as needed" instead of "always"

[1.1.4] - 2022-08-08
## Changed
- OM-59113: donot save/recall prim visibilities by default
- Remove unnecessary sleep

[1.1.3] - 2022-07-16
## Fixed
- File name error.

[1.1.2] - 2022-07-04
## Fixed
- OM-53033: thumnail error when resolution is not 16:9

[1.1.1] - 2022-07-02
## Fixed
- When open a stage, set editing waypoint to None
## Added
- VP2 tests

[1.1.0] - 2022-06-21
## Changed
- VP2 support

[1.0.4] - 2022-01-04
## Changed
- Changed the format to save/load data for waypoint/sunstudy

[1.0.3] - 2021-09-17
## Added
- Add waypoint settings window

[1.0.2] - 2021-09-16
## Changed
- Use omni.kit.viewport.deferred_capture to do viewport capture for latest kit

[1.0.1] - 2021-09-15
## Changed
- Use capture_next_frame_rp_resource_callback for viewport capture

[1.0.0] - 2021-09-06
## Changed
- Rename to omni.kit.waypoint.core
-
[0.3.0] - 2021-08-04
========================
Changed:
- Save waypoint thumbnail in usd file

[0.2.5] - 2021-03-25
========================
Added:
- Added notes for waypoints

[0.2.4] - 2021-03-23
========================
Changed:
- Added active waypoint setting to notify interested extensions on the active waypoint change

[0.2.3] - 2021-03-12
========================
Fixed
- Fixed the issue the waypoint icon in dashboard is not updated correctly sometimes
Changed:
- Rotate camera will stop the recall of a waypoint now
- Hide waypoints in the stage window to avoid it is modified or deleted by users
- and now you can drag a waypoint into a playlist from waypoint manager instead of from the stage window.


[0.2.2] - 2021-03-02
========================
Fixed
- Make sure waypoint manager is refreshed at creating a new project


[0.2.1] - 2021-02-22
========================
Changed
- Updated icons for waypoints as they were the same to Location; also revised the icon for Location


[0.2.0] - 2021-02-05
========================
Added
- Added support to save thumbnails to proper local or remote folders


[0.1.7] - 2021-02-04
========================
Added
- Added support of user name in waypoints


[0.1.6] - 2021-02-02
========================
Added
- Renamed Bookmark to the new name Waypoint
- Added support of store and recall to Sunstudy date time and location


[0.1.5] - 2021-01-22
========================
Added
- Support to rename a viewport bookmark from UI.
- Support to load viewport bookmarks at stage open event

[0.1.4] - 2021-01-21
========================
Added
- Save the render preset at creating a bookmark, and set it back at recalling.
- Save active camera name in the bookmark


[0.1.3] - 2021-01-19
========================
Added
- Save the camera prim at creating a bookmark, and set it back at recalling.


[0.1.2] - 2021-01-18
========================
Added
- Save bookmark info, including camera position/target, created time, and thumbnail path into the scene's usd.


[0.1.1] - 2021-01-14
========================
Added
- Added capture of the screenshot and simple camera params of a bookmark.

[0.1.0] - 2021-01-12
========================
Added
- Initial kit bookmark window implementation

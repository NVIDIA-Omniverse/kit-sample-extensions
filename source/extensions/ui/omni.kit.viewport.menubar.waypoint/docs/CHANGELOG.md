# CHANGELOG

This document records all notable changes to ``omni.kit.viewport.menubar.display`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [104.2.16] - 2023-10-17
### Changed
- OMFP-2692 - Fixed checked state when the window was created by another extension.

## [104.2.15] - 2023-10-10
### Changed
- OMFP-2300 - Unit test coverage.

## [104.2.14] - 2023-10-09
### Changed
- OMFP-2205 - Left click opens the list_window. Right click does nothing.

## [104.2.13] - 2023-10-09
### Changed
- OM-111590: Disable golden image tests until a fix is found

## [104.2.12] - 2023-02-17
### Changed
- OM-80840: Update to use newer list window

## [104.2.11] - 2023-01-31
### Changed
- OM-80333: Show waypoint list window again after waypoint edit done

## [104.2.10] - 2023-01-12
### Changed
- OM-53986: Update waypoint list window style to be same as other menus in viewport menubar
- Auto change waypoint list window height when waypoints changed

## [104.2.9] - 2023-01-05
### Changed
- OM-74227: Create waypoint in async mode

## [104.2.8] - 2022-12-01
### Changed
- OM-53986: Remove omni.kit.browser.waypoint

## [104.2.7] - 2022-11-10
### Changed
- OM-53986: update waypoint icon and change close icon size

## [104.2.6] - 2022-11-08
### Changed
- Reverting. This extension is no longer used in View.

## [104.2.5] - 2022-11-08
### Changed
- Hide popup and list window on file load.

## [104.2.4] - 2022-10-26
### Changed
- Update test for kit 105

## [104.2.3] - 2022-09-30
### Changed
- Updating for ETM

## [104.2.2] - 2022-09-21
### Changed
- Updated the order value to separate it from Markup. The last update was lost.

## [104.2.1] - 2022-09-21
### Changed
- Updated the order value to separate it from Markup.

## [104.2.0] - 2022-09-16
### Removed
- Remove play bar
### Changed
- Use PlayManager to sync with other extensions

## [104.1.12] - 2022-09-06
### Changed
- OM-62234: Create waypoint list window when extension startup for play controls in navigation

## [104.1.11] - 2022-09-06
### Changed
- Improve the way to re-position the list window

## [104.1.10] - 2022-09-02
### Added
- More Events and settings for play
- Hide play bar (show in navigation now)

## [104.1.9] - 2022-08-29
### Added
- Event to play next
- Setting for play next available

## [104.1.8] - 2022-08-23
### Removed
- Remove "Waypoint Manager" button from the list window

## [104.1.7] - 2022-08-22
### Changed
- Adjust the list window position
### Added
- Add post message when open a document with waypoints

## [104.1.6] - 2022-08-18
### Changed
- Add play buttons

## [104.1.5] - 2022-08-06
### Changed
- Remove unnecessary debug message

## [104.1.4] - 2022-08-05
### Changed
- Implement OM-58122 more requirements:
- The Waypoint UI should not dismiss after a Waypoint is selected
- Dock the panel to the right of the screen on open, only if the active document has waypoints.
- -If the doc is opened that does not have waypoints after first opening one that does, don’t show the waypoint UI
- Maintain consistent position of the panel
- - Resizing the window width currently leaves the Waypoint in the incorrect position


## [104.1.3] - 2022-08-03
### Changed
- When a USD contains Waypoints is opened in View, display the Waypoints drop down panel floating over the UX.

## [104.1.2] - 2022-07-26
### Changed
- Show triangle in button

## [104.1.1] - 2022-07-24
### Changed
- Update icon

## [104.1.0] - 2022-06-16
### Added
- Ability to add/remove custom display setting


## [104.2.12] - 2023-02-17
### Changed
- OM-80840: Update to use newer list window

## [104.2.11] - 2023-01-31
### Changed
- OM-80333: Show waypoint list window again after waypoint edit done

## [104.2.10] - 2023-01-12
### Changed
- OM-53986: Update waypoint list window style to be same as other menus in viewport menubar
- Auto change waypoint list window height when waypoints changed

## [104.2.9] - 2023-01-05
### Changed
- OM-74227: Create waypoint in async mode

## [104.2.8] - 2022-12-01
### Changed
- OM-53986: Remove omni.kit.browser.waypoint

## [104.2.7] - 2022-11-10
### Changed
- OM-53986: update waypoint icon and change close icon size

## [104.2.6] - 2022-11-08
### Changed
- Reverting. This extension is no longer used in View.

## [104.2.5] - 2022-11-08
### Changed
- Hide popup and list window on file load.

## [104.2.4] - 2022-10-26
### Changed
- Update test for kit 105

## [104.2.3] - 2022-09-30
### Changed
- Updating for ETM

## [104.2.2] - 2022-09-21
### Changed
- Updated the order value to separate it from Markup. The last update was lost.

## [104.2.1] - 2022-09-21
### Changed
- Updated the order value to separate it from Markup.

## [104.2.0] - 2022-09-16
### Removed
- Remove play bar
### Changed
- Use PlayManager to sync with other extensions

## [104.1.12] - 2022-09-06
### Changed
- OM-62234: Create waypoint list window when extension startup for play controls in navigation

## [104.1.11] - 2022-09-06
### Changed
- Improve the way to re-position the list window

## [104.1.10] - 2022-09-02
### Added
- More Events and settings for play
- Hide play bar (show in navigation now)

## [104.1.9] - 2022-08-29
### Added
- Event to play next
- Setting for play next available

## [104.1.8] - 2022-08-23
### Removed
- Remove "Waypoint Manager" button from the list window

## [104.1.7] - 2022-08-22
### Changed
- Adjust the list window position
### Added
- Add post message when open a document with waypoints

## [104.1.6] - 2022-08-18
### Changed
- Add play buttons

## [104.1.5] - 2022-08-06
### Changed
- Remove unnecessary debug message

## [104.1.4] - 2022-08-05
### Changed
- Implement OM-58122 more requirements:
- The Waypoint UI should not dismiss after a Waypoint is selected
- Dock the panel to the right of the screen on open, only if the active document has waypoints.
- -If the doc is opened that does not have waypoints after first opening one that does, don’t show the waypoint UI
- Maintain consistent position of the panel
- - Resizing the window width currently leaves the Waypoint in the incorrect position


## [104.1.3] - 2022-08-03
### Changed
- When a USD contains Waypoints is opened in View, display the Waypoints drop down panel floating over the UX.

## [104.1.2] - 2022-07-26
### Changed
- Show triangle in button

## [104.1.1] - 2022-07-24
### Changed
- Update icon

## [104.1.0] - 2022-06-16
### Added
- Ability to add/remove custom display setting

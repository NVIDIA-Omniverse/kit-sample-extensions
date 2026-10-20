# CHANGELOG

This document records all notable changes to ``omni.kit.viewport.menubar.display`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [104.1.26] - 2023-10-17
### Changed
- OMFP-2692 - Fixed checked state when the window was created by another extension.

## [104.1.25] - 2023-10-09
### Changed
- OMFP-2205 - Left click only opens the list window. Right click does nothing.

## [104.1.24] - 2023-10-09
### Changed
- OM-111590: Disable golden image tests until a fix is found

## [104.1.23] - 2023-04-28
### Changed
- Indentation broke.

## [104.1.22] - 2023-04-26
### Changed
- Updating tests, and removing dead code.

## [104.1.21] - 2023-03-15
### Changed
- Updating test arguements

## [104.1.20] - 2023-03-15
### Changed
- Adding the `omni.kit.markup.playlist` extension.

## [104.1.19] - 2023-02-17
### Changed
- OM-80840: Update to use newer list window

## [104.1.18] - 2022-11-08
### Changed
- Reverting changes. This isn't the extension used in View.

## [104.1.17] - 2022-11-08
### Changed
- Hiding thumbnail list on file load.

## [104.1.16] - 2022-10-26
### Changed
- Update test for kit 105

## [104.1.15] - 2022-10-25
### Changed
- Adjusting markup delegate to ask the extension for the markup instance.

## [104.1.14] - 2022-10-25
### Changed
- Add failure exclude pattern for test.

## [104.1.13] - 2022-09-30
### Changed
- Updated golden images for ETM failures.

## [104.1.3] - 2022-09-26
### Changed
- Lock markup.core version to 1.0.5 to fix import issue after updating kit sdk to 104

## [104.1.2] - 2022-07-29
### Changed
- Add triangle to button to align with menubar style

## [104.1.12] - 2022-08-31
### Fixed
- Tests were failing on CI because of weird crosstalk between two tests, broke into two files.

## [104.1.11] - 2022-08-31
### Fixed
- Menubar icon would not update properly when markup was deactivated.

## [104.1.10] - 2022-08-26
### Fixed
- Settings name in .toml file.

## [104.1.7] - 2022-08-26
### Changed
- Aligning markup window to the top of the frame and aligned with waypoint.

## [104.1.6] - 2022-08-26
### Improved
- State behavior changes when using new play list window

## [104.1.5] - 2022-08-25
### Changed
- Revamped the markup listview to be in line with the new waypoint changes.
- Removed the extra Apply/Cancel hover windows in favor of unified toolbar UX.

## [104.1.4] - 2022-08-03
### Changed
- Removed some dead code.

## [104.1.3] - 2022-08-02
### Changed
- Fixed dependency list

## [104.1.7] - 2022-08-22
### Changed
- Adjust the list window position
### Added
- Add post message when open a document with markups

## [104.1.6] - 2022-08-18
### Changed
- Add play buttons

## [104.1.5] - 2022-08-06
### Changed
- Remove unnecessary debug message

## [104.1.4] - 2022-08-05
### Changed
- Implement OM-58122 more requirements:
- The Markup UI should not dismiss after a Markup is selected
- Dock the panel to the right of the screen on open, only if the active document has markups.
- -If the doc is opened that does not have markups after first opening one that does, don’t show the markup UI
- Maintain consistent position of the panel
- - Resizing the window width currently leaves the Markup in the incorrect position


## [104.1.3] - 2022-08-03
### Changed
- When a USD contains Markups is opened in View, display the Markups drop down panel floating over the UX.

## [104.1.2] - 2022-07-26
### Changed
- Show triangle in button

## [104.1.1] - 2022-07-24
### Changed
- Update icon

## [104.1.0] - 2022-06-16
### Added
- Ability to add/remove custom display setting

## [104.0.4] - 2022-05-31
### Changed
- Visibilty of Skeleton and Mesh to work with instances if possible.
- Split visibility logic into separate test-able module.
- Make any usage of legacy displayOptions bitmask private and do not expose an API for it.
### Fixed
- Startup visibility for grid and selection.
- Make "Selection" item toggle "Selection Outline", not "Selection Box".
- Restoration of various show/hide items that should be persistent.
- Reset Show/Hide values/types that are scene/stage dependent to keep UI and render in Sync.

## [104.0.3] - 2022-05-04
### Changed
- Imported to kit repro and bump version to match Kit SDK

## [1.0.3] - 2022-03-28
### Added
- Setting for visible and Order

## [1.0.2] - 2022-03-16
### Fixed
- OM-46224: Fix camera manipulation lock out and legacy Camera frustum drawing.

## [1.0.1] - 2022-03-16
### Changed
- Move print to carb.log_info

## [1.0.0] - 2022-03-11
### Added
- Split from omni.kit.viewport.menubar

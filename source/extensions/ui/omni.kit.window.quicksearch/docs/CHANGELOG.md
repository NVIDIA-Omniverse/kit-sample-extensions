# Changelog

## [2.4.5] - 2024-03-01
### Fixed
- OM-121112: Fix for quicksearch items disappearing in Action Graph when expanded.

## [2.4.4] - 2024-02-22
### Fixed
- OMPRW-886: Dragging and dropping quicksearch nodes to another widget creates a duplicate.

## [2.4.3] - 2024-02-06
### Changed
- OMPRW-776: Don't show the quicksearch window when there are no items.

## [2.4.2] - 2023-12-07
### Changed
- OM-114155: Increased code coverage to 87%.

## [2.4.1] - 2023-06-28
### Changed
- OM-98697: Registry hotkey with omni.kit.hotkeys.core if enabled to rebound key when required

## [2.4.0] - 2023-06-26
### Changed
- `request_to_execute` removes `FLAG_WANT_CAPTURE_KEYBOARD` bits from key `modifier`

## [2.3.5] - 2023-07-06
### Fixed
- Don't allow the root item to be collapsed if the TreeView was built with root_visible=False

## [2.3.4] - 2023-05-23
### Changed
- Changed tree view interaction to click on sub category to open/close without clicking expansion arrow.

## [2.3.3] - 2022-11-10
### Fixed
- remove omni.kit.test dependency

## [2.3.2] - 2022-09-28
### Fixed
- disable cursor blink in tests

## [2.3.0] - 2022-02-25
### Changed
- Use search field
- conform the style with the graph core's treeview style

## [2.2.1] - 2022-02-23
### Changed
- fix the issue that selection was not cleared when the window is brought up again

## [2.2.0] - 2022-02-22
### Added
- add style to quick search registry keyword so that users can have customized tree view look

## [2.1.0] - 2022-02-21
### Added
- Exclusion API, the way to hide all the models except the specific one

## [2.0.6] - 2021-10-15
- add tests

## [2.0.5] - 2021-06-15
- Add feature flag

## [2.0.4] - 2021-05-16
### Fixed
- Added Search Clear Button

## [2.0.3] - 2021-05-07
### Fixed
- Added priority to the registry, so it's possible to control the order of the items
- Up/down keys

## [2.0.2] - 2021-04-29
### Changed

- Fix Keyboard Inputs
## [2.0.1] - 2021-04-08
### Changed
- Update golden image to fix test


## [2.0.0] - 2021-03-28
### Changed
- Refactor on the Delegate to make it easier to write extensions

## [1.0.0] - 2021-02-10
### Added
- The initial implementation. It shows the window when the use presses TAB.

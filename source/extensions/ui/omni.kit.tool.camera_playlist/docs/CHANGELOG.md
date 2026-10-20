# CHANGELOG

This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.4.1] - 2025-09-22
### Changed
- OMPE-64397: omni.kit.tool.camera_playlist needs ui.Menu & ui.Separator to use menu_compatibility=False

## [1.4.0] - 2025-08-21
### Changed
- Update to event 2.0

## [1.3.5] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [1.3.4] - 2025-05-29
### Changed
- Fix "SyntaxWarning: invalid escape sequence" for python 3.12 used in kit 108

## [1.3.3] - 2025-02-19
## Changed
- Replace `omni.kit.window.viewport` with `omni.kit.viewport.window` in test dependencies

## [1.3.2] - 2025-01-06
### Added
- Update public api

## [1.3.1] - 2023-10-12
## Added
- OMFP-1265: added test cases

## [1.3.0] - 2023-09-25
## Added
- OM-41439: Smooth navigate in playlist when item clicked

## [1.2.4] - 2023-07-10
## Fix
- Fixed name of USD Presenter's sidecar extension.

## [1.2.3] - 2023-03-15
### Changed
- OM-55996: Enable dropping to the header area above playlist view.

## [1.2.2] - 2023-03-14
### Changed
- OM-80113 - Fixing "All Markups" section of the playlist tool.

## [1.2.1] - 2023-02-23
### Changed
- Ignoring IToken testing error message that appears to be unrelated to the tests passing

## [1.2.0] - 2023-02-10
### Changed
- OM-79084: Default do not show window after afterup to speed scene laoding time for Factory Explorer

## [1.1.5] - 2022-12-08
### Updated
- Fix Tests

## [1.1.4] - 2022-12-08
### Added
- Add sidecar reaonly logic.

## [1.1.3] - 2022-11-29
### Changed
- Fixing playlist sidecar code to only trigger the edit_context when writing to a file.

## [1.1.2] - 2022-11-17
### Changed
- Fix issue some playlist properties do not loaded from stage file

## [1.1.1] - 2022-11-15
### Changed
- Update test and removed image comparison test, improve test coverage

## [1.1.0] - 2022-11-15
### Added
- Ability to save playlist in sidecar file if omni.view.sidecar enabled

## [1.0.5] - 2022-09-16
### Changed
- MARKUP is not member of PlaylistCard anymore

## [1.0.4] - 2022-09-16
### Changed
- Use PlayManager from omni.kit.playlist.core for playing to sync with other extensions
### Added
- API to append playlist from other extensions

## [1.0.3] - 2022-09-07
### Changed
- OM-62076: use app menu instead of editor menu to make hotkey CTRL+P for menu work

## [1.0.2] - 2022-08-17
### Changed
- Use omni.kit.playlist.core

## [1.0.1] - 2022-08-03
### Changed
- When creating a new playlist, show it in list view.

## [1.0.0] - 2022-07-24
### Changed
- Use latest omni.anim.curve for omni.timeline v1.0

## [0.1.5] - 2022-07-23
### Changed
- use omni.anim.curve v104.10.0 since v104.11.1 requires omni.timeline v1.0 which not in kit 103.5 yet

## [0.1.4] - 2022-07-08
### Fixed
- Make hotkey work

## [0.1.3] - unreleased
### Changed
- VP2 support

## [0.1.2] - unreleased
### Changed
- Viewport Interface

## [0.1.1] - unreleased
### Added
- Interface to play by other extensions

## [0.1.0] - unreleased
### Added
- Initial camera playlist implementation
- Remove omni.kit.editor/update-event

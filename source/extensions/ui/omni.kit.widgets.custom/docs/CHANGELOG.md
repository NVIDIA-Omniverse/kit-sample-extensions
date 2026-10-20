# CHANGELOG

This document records all notable changes to ``omni.kit.widgets.custom`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.1.4] - 2026-07-17
### Fixed
- test_TitleWindowBase: use capture_and_compare for the intermediate capture so finalize_test's window restore no longer shrinks the second capture.

## [1.1.3] - 2026-02-18
### Fixed
- Fixed git URL

## [1.1.2] - 2025-11-06
### Changed
- Update timer test

## [1.1.1] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.1.0] - 2025-08-20
### Changed
- Update to event 2.0

## [1.0.13] - 2025-05-12
### Changed
- Update to use python 3.12.

## [1.0.12] - 2025-03-18
### Changed
- enable checkapi for omni.kit.widgets.custom which are needed for many extensions in kit-windows

## [1.0.11] - 2025-03-18
### Fixed
- Fix repo docs issue

## [1.0.10] - 2025-01-08
### Added
- Update public api.

## [1.0.9] - 2024-11-27
### Fixed
- OMPE-27977: update kit sdk to 107

## [1.0.8] - 2024-02-20
### Fixed
- OM-99859: Fix ETM test failures (for kit-sdk 106.x)

## [1.0.7] - 2023-10-24
### Fixed
- OMFP-1291: Add more tests (code coverage up to 85%+)

## [1.0.6] - 2023-10-09
### Fixed
- OMFP-1889: Remove usage of pipapi.install in comment in test

## [1.0.5] - 2023-06-29
### Fixed
- Fixed OM-99859

## [1.0.4] - 2022-07-11
### Fixed
- Fixed combobox drop list width

## [1.0.3] - 2022-04-27
### Added
- Add pause/resume for Timer

## [1.0.2] - 2022-04-25
### Changed
- Update version to trigger auto-publish

## [1.0.1] - 2022-04-13
### Changed
- Move to new repository

## [0.6.4] - 2022-03-10
### Changed
- Republish

## [0.6.3] - 2021-10-15
### Added
- Test dependency

## [0.6.2] - 2021-09-07
### Added
- More API of ViewUsd
- Change params of collapsableframe

## [0.6.1] - 2021-05-07
### Added
- Arg to use editor menu when creating window

## [0.6.0] - 2021-03-24
### Changed
- update the version for automatic update

## [0.5.7] - 2021-03-24
### Added
- SimpleGridView
### Fixed
- the issue when uninstall Paint tool on Create

## [0.5.6] - 2021-03-11
### Added
- get_ext_instance to get extension 2.0 instance by name
- enable editor menu if required

## [0.5.5] - 2021-02-09
### Changed
- Rebuild menus with asyncio, otherewise view may crash

## [0.5.4] - 2021-02-09
### Changed
- Input(mouse/keyboard) subscription in popup WindowExtension
- Use 'NvidiaDark' as default UI style if failed to get from settings (for kit)
### Added
- Timer class

## [0.5.3] - 2021-02-05
### Removed
-Remove omni.kit.editor/update-event

## [0.5.2] - 2021-01-26
### Added
- always_trigger_event for FloatSliderEx, in order to provent from trigging event when set the value in code

## [0.5.1] - 2021-01-25
### Added
- API to get current app is view or kit
### Changed
- Remove round corner of list view scroolbar

## [0.5.0] - 2021-01-21
### Added
- SimpleListView and samples
- CustomComboBox with delegate and samples
- DashRectangle
- WindowExtension
### Changed
- Remove old file picker and always use new one

## [0.4.1] - 2020-12-11
### Added
- New file picker and relate file

## [0.4.0] - 2020-11-27
### Added
- SimpleCollapsableFrame
- ExpandPanel
- IntSpinner
### Changed
- Unify font size


## [0.3.9] - 2020-11-24
### Fixed
- Fix the issue that "dictionary changed size during iteration"
### Added
- Add feature: automatically hide the close button when docked.
### Changed
- Changed color/style definitions

## [0.3.8] - 2020-11-09
### Fixed
- Fix the issue that Dialog has no default image for the default final Close button

## [0.3.7] - 2020-11-08
### Changed
- Change the titlewindow's title lines.
- Support image in the buttons of a Dialog

## [0.3.6] - 2020-11-04
### Added
- Move some duplicate code uniform_absolute_path and etc

## [0.3.5] - 2020-10-29
### Changed
- Change folder structure and include licenses
### Added
- InputDialog

## [0.3.2] - 2020-10-24
### Added
- SwitchOrCheckbox
### Changed
- Update UI in kit

## [0.3.0] - 2020-10-20
### Added
- Export delay run functions

## [0.1.0] - 2020-08-03
### Added
- Initial custom widgets implementation

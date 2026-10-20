# CHANGELOG

This document records all notable changes to ``omni.kit.browser.asset`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.3.17] - 2026-10-06
### Changed
- Asset folders use the S3 regional endpoint `omniverse-content-production.s3.us-west-2.amazonaws.com` instead of the legacy `s3-us-west-2` form. Under an Omniverse Storage API sign-in, omni.client 2.75 serves the regional endpoint directly and denies the legacy form.

## [1.3.16] - 2026-01-26
### Changed
- Styling update using centralized global styling

## [1.3.15] - 2025-10-10
### Changed
- OMPE-64394: Added menu_compatibility=False

## [1.3.14] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [1.3.13] - 2025-03-25
### Fixed
- Fix doc build issues

## [1.3.12] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [1.3.11] - 2024-11-18
### Changed
- Updated the omni.kit.asset.browser URLs to point to current data.

## [1.3.10] - 2024-06-05
### Changed
- Fix test failure that module 'omni.kit' has no attribute 'ui'

## [1.3.9] - 2024-03-20
### Changed
- Add omni.kit.context_menu to test dependencies.

## [1.3.8] - 2024-03-06
### Changed
- OMFP-1262: Re-enabling disabled test for copying clipboard on Linux.

## [1.3.7] - 2023-10-05
### Fixed
- Switched to omni.kit.clipboard instead of pyperclip.

## [1.3.6] - 2023-10-03
### Changed
- OMFP-1262: Increase code coverage to 90%.
### Fixed
- Fix for attribute error in ContextMenu._collect.

## [1.3.5] - 2023-06-27
### Changed
- Remove duplicated run_warmup argument

## [1.3.4] - 2023-06-27
### Changed
- Cache new root folders during warmup

## [1.3.3] - 2023-06-02
### Changed
- OM-96989: Default not build ui when startup

## [1.3.2] - 2023-05-23
### Changed
- OM-88159: Change collect default folder to content folder which set in launcher.

## [1.3.1] - 2023-04-03
### Changed
- OM-84608: When double click on asset item to add into viewport, respect payload options in Preferences

## [1.3.0] - 2023-03-13
### Changed
- OM-85649: support of lazy load workflow in Create

## [1.2.4] - 2023-02-21
### Changed
- Fix errors for python 3.10

## [1.2.3] - 2023-01-04
### Added
- Add properties for window and browser widget

## [1.2.2] - 2022-12-06
### Changed
- OM-75191: For folders in default settings, hide file without thumbnail, otherwise show all files

## [1.2.1] - 2022-11-10
### Changed
- Do not show window immediately after docked

## [1.2.0] - 2022-10-31
### Changed
- Use TreeFolderBrowserModel

## [1.1.18] - 2022-10-18
### Changed
- OM-66917: Make sure valid name used to create stage prim

## [1.1.17] - 2022-10-17
### Changed
- Update test for ETM failure

## [1.1.16] - 2022-10-11
### Added
- Enable summary
- Caching all asset folders during warmup

## [1.1.15] - 2022-10-10
### Added
- OM-63647: New context menu to add/replace asset to stage and copy asset url

## [1.1.14] - 2022-10-06
### Changed
- Only test one category

## [1.1.13] - 2022-10-03
### Changed
- Select a category after startup

## [1.1.12] - 2022-09-30
### Changed
- OM-64030: Make asset browser UX category tree same as sample browser

## [1.1.11] - 2022-08-29
### Added
- Add local cache file path to use local cache feature to avoid folder traverse when close and open the app again

## [1.1.10] - 2022-08-22
### Added
- Increase test coverage
### Fixed
- Fix tests with newer kit-sdk

## [1.1.9] - 2022-06-25
### Added
- Remove omni.kit.window.viewport

## [1.1.8] - 2022-06-19
### Added
- Drop to VP2

## [1.1.7] - 2022-04-13
### Changed
- Rename Assets to NVIDIA Assets

## [1.1.6] - 2022-03-30
### Changed
- Republish for repo updates

## [1.1.5] - 2022-03-17
### Added
- Add settings for main window: if the window is visible at startup

## [1.1.4] - 2021-12-08
### Added
- Move to utility function for viewport interface query for 102, 103 tests

## [1.1.3] - 2021-12-08
### Added
- Move to omni.kit.viewport_legacy

## [1.1.2] - 2021-09-30
### Added
- Add setting for data timeout

## [1.1.1] - 2021-09-12
### Added
- Collet asset (required omni.kit.tool.collect v2.0.5 or later)

## [1.1.0] - 2021-08-24
### Changed
- Allow user define asset categories to set instanceable flag after dragging to viewport (require kit 103)

## [1.0.4] - 2021-05-28
### Added
- Predownload in options menu

## [1.0.4] - 2021-05-24
## Changed
- Change dependencies for tests

## [1.0.3] - 2021-05-20
### Load folders after app startup

## [1.0.2] - 2021-05-17
### Add

- support for show_category_subfolders ( True )
- support for hide_file_without_thumbnails (True )

## [1.0.1] - 2021-05-07
### Add
- Window loaded on startup

## [1.0.0] - 2021-05-06
### Add
- First Release

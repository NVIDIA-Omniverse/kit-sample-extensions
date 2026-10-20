# CHANGELOG

This document records all notable changes to ``omni.kit.browser.core`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [2.4.0] - 2026-08-25
### Added
- OMPE-101618: `TreeCategoryDelegate.build_loading_overlay`, for putting a control over a loading
  row's spinner. Empty by default.

### Fixed
- OMPE-101618: the detail view no longer stalls the main thread while a scan reports progress.

## [2.3.18] - 2026-01-19
### Changed
- Styling update using centralized global styling

## [2.3.17] - 2025-09-03
### Changed
- OMPE-56748: omni.kit.browser.core ETM needs ui.Menu & ui.Separator to use menu_compatibility=False

## [2.3.16] - 2025-07-16
### Changed
- Replace omni.renderer_capture to omni.kit.renderer_capture

## [2.3.15] - 2025-06-30
### Changed
- OMPE-53344: Fix Kit browsers thumbnail warning log spam.

## [2.3.14] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [2.3.13] - 2025-04-01
### Changed
- Make getter and setter methods for url and thumbnail properties

## [2.3.12] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [2.3.11] - 2024-04-24
### Changed
- Possible to have multiple columns for detail view

## [2.3.10] - 2023-10-07
### Changed
- OMFP-1303: Increase code coverage to 91%

## [2.3.9] - 2023-05-25
### Changed
- OM-95405: Make spinner height to fit item

## [2.3.8] - 2023-05-23
### Changed
- OM-88159: Add item right click function for tree category delegate.

## [2.3.7] - 2023-05-09
### Changed
- OM-93878: Fix issue when changing thumbnail size for items without thumbnail

## [2.3.6] - 2023-04-12
### Changed
- OM-75191: Make spinner faster (1.5x speed)

## [2.3.5] - 2023-03-22
### Changed
- OM-75191: Make spinner bigger

## [2.3.4] - 2023-03-22
### Changed
- Right-click does not select the clicked item

## [2.3.3] - 2023-03-22
### Changed
- When multiple selection, only select visible items

## [2.3.2] - 2023-03-18
### Changed
- Notify selection changed while right click on items

## [2.3.1] - 2023-03-17
### Changed
- OM-86101: New argument "multiple_drag" to support multiple drag. Default False.

## [2.3.0] - 2023-03-08
### Changed
- OM-75191: Show loading animation while category in loading progress
- OM-83328: Tree lines for multi level categories

## [2.2.3] - 2022-12-14
### Changed
- OM-82767: If options menu item appended, always refresh menu

## [2.2.2] - 2022-12-14
### Changed
- Added [[test]] arguments

## [2.2.1] - 2022-11-13
### Changed
- Use content_clipping and frame build_fn to reduce drawing detail items

## [2.2.0] - 2022-11-03
### Added
- Add function for CategoryDelegate to get item count
- Add TreeBrowserWidget/TreeCategoryDelegate for treeview mode

## [2.1.5] - 2022-10-02
### Changed
- Update test for ETM failure

## [2.1.4] - 2022-09-30
### Changed
- Add more arguments to config browser widget

## [2.1.3] - 2022-09-30
### Changed
- Line align for categories with level > 2

## [2.1.2] - 2022-09-21
### Changed
- Update golden img for Zoombar change

## [2.1.1] - 2022-09-12
### Changed
- Make browser widget category splitter narrower

## [2.1.0] - 2022-09-01
### Added
- Add branching styles to styles.py

## [2.0.15] - 2022-08-31
### Added
- Fix error when build thumbnail returns ui.ImageWithProvider

## [2.0.14] - 2022-08-12
### Added
- An image placeholder to show before the actual thumbanil is downloaded

## [2.0.13] - 2022-06-19
### Added
- Drop to VP2

## [2.0.12] - 2021-03-31
### Added
- H center for overview view

## [2.0.11] - 2021-03-30
### Changed
- Republish for repo updates

## [2.0.10] - 2021-01-21
### Changed
- Increase width of category view scrollbar to same as detail view

## [2.0.9] - 2021-01-21
### Added
- Properties of ThumnnailView to change thumbnail padding

## [2.0.8] - 2021-01-20
### Added
- API to clear search words

## [2.0.7] - 2021-01-17
### Added
- Variable of detail scoll frame

## [2.0.6] - 2021-01-14
### Added
- Arg 'show_category_splitter' to show dragable splitter between category and detail view (default False)

## [2.0.5] - 2021-01-13
### Added
- More args for browser model and search bar

## [2.0.4] - 2021-12-10
### Added
- Viewport interface for 102 release

## [2.0.3] - 2021-10-20
### Changed
- Do not show header in overview is no title

## [2.0.2] - 2021-10-20
### Added
- More APIs for overview

## [2.0.1] - 2021-10-13
### Added
- More thumbnail arguments for overview

## [2.0.0] - 2021-10-11
### Added
- New UI style for overview

## [1.1.9] - 2021-09-30
### Changed
- Check menu item visibility before show options menu

## [1.1.8] - 2021-09-08
### Changed
- Donot show zoombar if max_thumbnail_size <= min_thumbnail_size

## [1.1.7] - 2021-07-20
### Removed
- Remove detail item Tooltips

## [1.1.6] - 2021-06-30
### Added
- Hovered and pressed status for search bar buttons

## [1.1.5] - 2021-06-28
### Added
- Export navigation button in search bar

## [1.1.4] - 2021-06-15
### Added
- Width property of searchbar

## [1.1.3] - 2021-06-10
### Added
- Callback for filter Changed
### Changed
- Background color of image button
- Remove from selection if a detail item invisible

## [1.1.2] - 2021-06-09
### Added
- Multi line for detail label enabled

## [1.1.1] - 2021-05-29
### Added
- Extra filter function
- Mouse hover event of detail item
- Cutsom click callback for navigation button in search bar

## [1.1.0] - 2021-05-28
### Add more arugments to OptionsMenu

## [1.0.9] - 2021-05-19
### Changed
- Donot clear item selection if click on selected item again. To clear, click on a unselected item or empty space.

## [1.0.8] - 2021-05-12
## Changed
- Default max thumbnail size from 256 to 512

## [1.0.7] - 2021-05-10
## Changed
- Chagne browser widget ui to display well in view

## [1.0.6] - 2021-05-07
## Added
- Execute in model
- Default options menu

## [1.0.5] - 2021-05-04
## Added
- API to show/hide collection and categories
-
## [1.0.4] - 2021-05-01
## Add
- Filter detail items as required

## [1.0.3] - 2021-04-26
## Changed
- Use new zoombar

## [1.0.2] - 2021-04-21
## Changed
- Change UI layout and style of browser widget

## [1.0.1] - 2021-04-19
## Changed
- Change default thumbnail size to 128

## [1.0.0] - 2021-04-19
### Added
- First release

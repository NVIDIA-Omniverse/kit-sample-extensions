# CHANGELOG

This document records all notable changes to ``omni.kit.widget.searchfield`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.0.31] - 2025-04-09
### Fixed
- Fix doc build errors

## [1.0.30] - 2025-01-08
### Added
- Update public api.

## [1.0.29] - 2024-11-19
### Fixed
- OMPE-27977: Compatible with Kit 107 (USD 24 / Python 3.11)

## [1.0.28] - 2024-05-23
### Fixed
- Additional incorrect imports from  omni.kit.window.filepicker
### Changed
- Move deepsearch and search_grammar to omni namespace rather than global one

## [1.0.27] - 2024-04-03
### Updated
- Changed SearchDelegate source from omni.kit.window.filepicker to omni.kit.widget.search_delegate

## [1.0.26] - 2023-10-11
### Added
- Updated PIL anti-aliasing filter name for compatibility with Python PIL 10.0+

## [1.0.25] - 2023-08-31
### Added
- possibility to customize search engine button

## [1.0.24] - 2023-07-11
### Updated
- Search engines are now pre-filtered for Nucleus servers. Updated the test case to support that.

## [1.0.23] - 2023-07-06
### Updated
- search grammar package
### Fixed
- OM-100941: added query parsing before search request is submitted

## [1.0.22] - 2023-07-06
### Fixed
- OM-100426: Get prefixes for S3 buckets (URL schema - https)

## [1.0.21] - 2023-06-02
### Fixed
- OM-93913: Don't show search service menu when it not available in current folder.

## [1.0.20] - 2023-05-11
### Updated
- latest kit tools update

## [1.0.19] - 2023-05-05
### Added
- Limit on the maximum token length
### Updated
- Deepsearch helper package
- improved test coverage

## [1.0.18] - 2023-03-14
### Updated
- Show an error when search dates are out of order.

## [1.0.17] - 2023-01-12
### Updated
- Add `search_grammar` to python modules

## [1.0.16] - 2022-12-20
### Updated
- Do not show hint container when building search field ui if there are already search tokens.

## [1.0.15] - 2022-11-23
### Added
- Added more image file formats.
- Added no-window to test args.

## [1.0.14] - 2022-07-20
### Added
- Option to hide image menu

## [1.0.13] - 2022-07-19
### Fixed
- Fixed duplicationg of image when tokens are disabled.
- Fixed example

## [1.0.12] - 2022-05-31
### Fixed
- Used search_grammar package for prefixes and parsing.
- Changed date field to be modified date not created date.
- Enable comma separated fields (OR syntax)
- Decouple search engine selection from search field.
- Make search button optional.

## [1.0.11] - 2022-05-13
### Fixed
- Fix bug where the search button remains open.
- Fix bug with image search not being cancelled.
- Fix bug with image and text bubbles combining into one.
- Fix bug where pressing escape clears the searchfield.
- Fix bug where clearing the last bubble does not clear the search result.

## [1.0.10] - 2022-04-20
- Add search button.
- Parse search field input and populate search menu.
- Show max 5 tokens at once.
- Single click to edit query text.
- Adjust calendar popup location.
- Allow external image drag and drop onto popup window.

## [1.0.9] - 2022-03-31
- Aligned Search UI to better match navigator.
- Fixed searching by date off-by-one error.

## [1.0.8] - 2022-03-30
- Disable automatic search while typing to reduce server load.

## [1.0.7] - 2022-03-23
### Fixed
- UI Button sizes are consistent across different display zoom settings on Windows.
- Deselect searchfield when closing the last word bubble.

## [1.0.6] - 2022-03-22
### Fixed
- Fixed examples and tests.
- Updated README.

## [1.0.5] - 2022-03-18
### Added
- Refresh prefixes every minute in case server status changes.
- Search engine choice is now persistent.

## [1.0.4] - 2022-03-16
### Added
- Fixed error where search window sometimes appears in wrong position.
- Color word bubbles with unsupported prefixes in red.

## [1.0.3] - 2022-03-11
### Added
- Description search added.
- 'Me' buttons added for created and modified fields.

## [1.0.2] - 2022-03-10
### Added
- UI will change depending on server search capabilities
- Context menu to find similar items with thumbnails, also supports drag-drop within omniverse.
- Fixes incompatibility with File Search.
- Clearing a search now shows the selected folder contents.

## [1.0.1] - 2022-03-02
### Update
- Added external drag drop handler.
- Resizes local images and converts to base64 for image search.
- Renamed field `tags` to `tag` and `type` to `ext` to match deepsearch.

## [1.0.0] - 2022-01-14
### Added
- Initial version implementation

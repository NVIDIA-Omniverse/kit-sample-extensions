# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.3.4] - 2026-10-16
### Fixed
- The tests no longer depend on `omni.hydra.usdrt_delegate`, which Kit 111 does not have. The published 0.3.3 still
  required it.
- Also versions the existing USD collection query fallback for OVStage-backed USDRT.

## [0.3.3] - 2025-10-22
### Changed
- OMPE-65187: Don't process prototype path updates in collection model notice handler.

## [0.3.2]
Bump patch version to re-publish after the move to kit-sample-extensions repo

## [0.3.1] - 2025-07-22
### Changed
- Add target kit and bump version.

## [0.3.0] - 2025-07-16
### Changed
- Add collection watch to speed up init for big usd scene.
- Merge filters into one to speed up init.

## [0.2.7] - 2025-07-10
### Changed
- Fix crash caused by usdrt stage write.

## [0.2.6] - 2025-06-16
### Changed
- Bump version for republish after yank.

## [0.2.5] - 2025-06-11
### Fixed
- Improve the start up performance, and improve the create/delete collections in big scene.

## [0.2.4] - 2025-05-16
### Fixed
- Fixed model leaks in tests

## [0.2.3] - 2025-05-07
### Fixed
- Bumped version as 0.2.2 was previously published

## [0.2.2] - 2025-04-09
### Changed
- Add widget-related unit test to increase code coverage.

## [0.2.1] - 2023-11-29
### Changed
- Add write target to extension so it doesn't break previous Kit versions (<107.0)

## [0.2.0] - 2023-11-26
### Changed
- Upgrade to Kit SDK 107 with USD 24.05 and python 3.11

## [0.1.18] - 2024-05-07
### Changed
- Reformat all source with repo format.

## [0.1.17] - 2024-02-13
### Fixed
- Updated menus

## [0.1.16] - 2023-09-020
### Fixed
- OM-107744: Visibility function determines visibility state depending on collection content.

## [0.1.15] - 2023-09-07
### Fixed
- OM-107738: Dragging and dropping prims from a stage window now parses and applies multiple items correctly.

## [0.1.14] - 2023-09-05
### Fixed
- OM-107743: Removing a collection entirely now correctly refreshes and reflects the proper state.

## [0.1.3] - 2023-05-11
- Version bump to force republish

## [0.1.12] - 2023-04-28
### Changed
- Replaced error prints with carb warnings

## [0.1.11] - 2022-11-23
### Changed
- Fixed widget refreshing

## [0.1.10] - 2022-09-19
### Changed
- Extracted the USD Commands to `omni.kit.core.collection`
- Extracted the Collection Helper to `omni.kit.core.collection`

## [0.1.9] - 2022-08-29
### Changed
- added return values to the CreateCollection and RenameCollection commands
- added name validation in the RenameCollection command

## [0.1.8] - 2022-04-01
### Changed
- use identifier to make nicer names when using UI Inspector

## [0.1.7] - 2021-07-30
### Changed
- allow prim to be dragged and dropped when source is a string

## [0.1.6] - 2021-07-30
### Changed
- added renderer dependency to tests

## [0.1.5] - 2021-05-05
### Changed
- rename extension (add preview)
- add default/clear of filters
- collection property change (e.g expansion state) AND collection rename/delete/duplicate now all work
- get expansionRule update working, fix up prop handling which was bad
- cache collectionitems in prims properly so state (including expansion) gets stored and reused on widget redraw
- support drag and drop from material library
- allow removal of multiples, correctly filter create collection
- drag from prim in stage onto collection directly
- dont allow prims to be dropped onto prims unless have collection parent
- allow drag/drop between different collections
- filtering of non-collection owning prims nwo works correctly at startup


## [0.1.4] - 2021-04-01
### Changed
-  allow us to single select collections and have property widgets appear
-  set widget to filter prims with collections by default
## [0.1.3] - 2021-04-01
### Changed
- Fix up commands/undo, get tests working
## [0.1.0] - 2021-03-18
### Added
- Initial release

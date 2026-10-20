# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [107.1.8] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: return an empty child list for leaf items to match the current UI model contract.

## [107.1.7] - 2026-07-27
### Fixed
- NVBUG 6243017: Defer stage-change listener setup until a stage exists when Variant Presenter opens during startup.

## [107.1.6] - 2026-04-24
### Fixed
- OMPE-80476: Fixed variant presenter combobox not updating when variant selection changes externally (Stage panel, Variant Editor, etc.). Register the stage-change listener at window construction when a stage is already loaded; fix `ObjectsChanged` filter to match `'variantSelection'` in `notice.GetChangedFields()` instead of the never-emitted `p.name == "set()"`; fix `Sdf.Path` vs `str` cache-key mismatch; clear `_vset_cache` on refresh. Added regression tests.

## [107.1.5] - 2026-04-22
### Fixed
- OMPE-87827: Fixed `AttributeError: module 'pxr.Vt' has no attribute 'Cat'` raised by `set_variant_lock_metadata` when locking a variant on a prim whose `variant_sets_ui_hints` metadata already existed but did not list that vset. Replaced the invalid `Vt.Cat(...)` call with `Vt.StringArray(list(...) + [...])`, mirroring the idiom used by the sibling unlock branch. Added regression test.

## [107.1.4] - 2026-02-18
### Changed
- Fix for flaky test

## [107.1.3] - 2025-12-22
### Changed
- OMPE-73440: Addressed performance issues when interacting with complex stages

## [107.1.2] - 2025-12-08
### Changed
- OMPE-73414: deferred creation of modal dialog until it's actually needed

## [107.1.1] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [107.1.0] - 2025-08-22
### Changed
- OMPE-57990: Update to use Events 2.0

## [107.0.2] - 2025-08-13
### Changed
- Refactor to use updated omni.kit.menu.utils

## [107.0.1] - 2025-08-01
Bump patch version to re-publish after the move to kit-sample-extensions repo

## [107.0.0] - 2023-11-26
### Changed
- Upgrade to Kit SDK 107 with USD 24.05 and python 3.11

## [106.0.0] - 2024-06-14
### Changed
- Fixed issue where extension was not correctly remembering tree expansion.

## [105.1.2] - 2024-05-07
### Changed
- Reformat all source with repo format.

## [105.1.1] - 2023-07-10
- Fixed issue where window visibility can be double-triggered in certain cases

## [105.1.0] - 2023-05-25
- Added option to filter locked variants
- Reworked and optimized UI structure
- Updated tests

## [105.0.8] - 2023-05-02
- New feature: variant sets can now be locked

## [105.0.7] - 2023-05-01
- Adding toolbar icon
- Now loads undefined prims with variants

## [105.0.6] - 2023-04-26
- Updating icon and readme
- Fixed issue where tree expansion was not preserved if window was not being drawn

## [105.0.5] - 2023-04-25
- List now updates appropriately on updates to prims with multiple variant sets

## [105.0.4] - 2023-04-24
- Group list now correctly updates when empty
- Branches correctly expand when switching focus

## [105.0.3] - 2023-04-20
- Update extension icon and readme
- Improved stage updates (more accurate and performant)
- Search now includes current variant of variant set
- Expanded status is no longer reset when list refreshes
- Code cleanup

## [105.0.2] - 2023-04-18
- Updating variant editor entry point

## [105.0.1] - 2023-04-17
- Updating extension path for combobox model

## [105.0.0] - 2023-04-17
- Releasing Variant Presenter extension

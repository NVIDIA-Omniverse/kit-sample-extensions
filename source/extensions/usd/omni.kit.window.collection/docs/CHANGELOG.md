# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.3.7] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: use composed USD queries when runtime collection queries are unavailable or incomplete.

## [0.3.6] - 2026-10-01
### Fixed
- Use ObserverGuard.reset() when cleaning up collection and selection observers to prevent AttributeError during graceful shutdown.

## [0.3.5] - 2026-02-25
### Changed
- OMPE-72501: Check validity of stage ID before calling usdrt.Usd.Stage.Attach().

## [0.3.4] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [0.3.3]
OMPE-57966: update to use Event 2.0.

## [0.3.2]
Bump patch version to re-publish after the move to kit-sample-extensions repo

## [0.3.1] - 2025-07-22
### Changed
- Add target kit and bump version.

## [0.3.0] - 2025-07-16
### Changed
- Add collection watch to speed up init for big usd scene.

## [0.2.5] - 2025-06-16
### Changed
- Bump version for republish after yank.
- roll back collection window's show window to keep backward compatibility

## [0.2.4] - 2025-06-12
### Fixed
- Improve the performance of initial window.

## [0.2.3] - 2025-04-30
### Fixed
- Bumped version as 0.2.2 was previously published

## [0.2.2] - 2025-04-24
### Fixed
- Fixed AttributeError self._tree_view

## [0.2.1] - 2025-04-09
### Changed
- Move widget-related unit test to omni.kit.widget.collection.

## [0.2.0] - 2024-11-26
### Changed
- Upgrade to Kit SDK 107 with USD 24.05 and python 3.11

## [0.1.22] - 2024-05-07
### Changed
- Reformat all source with repo format.

## [0.1.21] - 2024-02-26
- more test fixes. prevent windows from overlapping and breaking drag/drop tests

## [0.1.20] - 2024-02-16
- test fixes for non-standard ui_test.find() syntax that no longer supported

## [0.1.19] - 2024-02-14
- More ETM test fixes

## [0.1.18] - 2024-02-10
- Fix ETM tests

## [0.1.17] - 2023-05-31
- Use custom PrimSelectionPayload to avoid clashing with other USD Property Handlers (which normally support only prims)

## [0.1.16] - 2023-05-11
- Version bump to force republish

## [0.1.15] - 2023-04-11
### Changed
- fixed _notify_property_window to it doesn't pass invalid prim paths

## [0.1.14] - 2023-04-11
### Changed
- added no-window to tests

## [0.1.13] - 2023-04-10
### Changed
- Fixed unreliable tests

## [0.1.12] - 2022-08-03
### Changed
- Added missing test dependency

## [0.1.11] - 2022-12-02
### Changed
- Fixed tests

## [0.1.10] - 2022-11-23
### Changed
- Fixed None exception on exit

## [0.1.9] - 2022-09-27
### Changed
- Updated test dependencies to point to new collection core extension

## [0.1.8] - 2022-03-31
### Changed
- added tests

## [0.1.7] - 2021-07-30
### Changed
- updated renderer dependency in tests

## [0.1.6] - 2021-07-28
### Changed
- add renderer dependency to keep ETM happy

## [0.1.5] - 2021-05-05
### Changed
- rename extension (add preview)
- don't show window on startup

## [0.1.4] - 2021-05-03
### Changed
- Update to use new Payload class

## [0.1.3] - 2021-04-01
### Changed
- Fix up commands/undo, get tests working

## [0.1.0] - 2021-03-18
### Added
- Initial release

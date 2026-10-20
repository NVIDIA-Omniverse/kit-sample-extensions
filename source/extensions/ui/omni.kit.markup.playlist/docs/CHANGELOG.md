# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.2] - 2026-10-15
### Changed
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then `pump_apply_usd_changes failed (12)` and `PUMP apply_usd_changes ... failed`). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

## [0.1.1] - 2026-05-05
### Fixed
- OMPE-92578 - Stop playback in `TestPlayControl.tearDown` so the play_manager's update timer doesn't leak into the next test and emit `IndexError` tracebacks that fail the CI fail-pattern matcher.

## [0.1.0] - 2026-03-31
### Changed
- Fully updated to events 2.0

## [0.0.9] - 2026-02-18
### Changed
- Fix for flaky test
- Fix to prevent `check_update` from resetting index_model during test

## [0.0.8] - 2025-05-02
### Added
- Updating to events 2.0

## [0.0.7] - 2025-04-18
### Added
- Changing renderer from PXR to RTX for OVC2 ETM support.

## [0.0.6] - 2025-01-06
### Added
- Update public api

## [0.0.5] - 2023-11-02
### Added
- OMFP-2213 - improved test coverage

## [0.0.4] - 2023-10-11
### Fixed
- OMFP-2424 - check for null prim.

## [0.0.3] - 2023-03-16
### Changed
- OM-80113 - Ensuring that the markup tool pulls in the playlist extension.
- Updated unit tests to ensure only the viewport window is visible.

## [0.0.2] - 2023-03-15
### Added
- Moved `MarkupCard` to `omni.kit.markup.core` to resolve circular dependency issue.

## [0.0.1] - 2023-03-14
### Added
- OM-80113 - Fixing "All Markups" section of the playlist tool.

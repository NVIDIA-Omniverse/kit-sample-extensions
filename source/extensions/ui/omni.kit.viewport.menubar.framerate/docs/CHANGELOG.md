# CHANGELOG

This document records all notable changes to ``omni.kit.viewport.menubar.framerate`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.0.12] - 2026-10-15
### Fixed
- "Cycle frame-pacing presets" (action `FramePacingCyclePresets`, SHIFT+ALT+P) no longer freezes the app when the current
  preset is not one the menu offers: a DLSS-G "x2" preset (for example `60x2`) kept on a GPU without DLSS-G or with
  `showDLSSG` off, or a custom or empty value. The cycle searched an endless `cycle()` of the offered presets for the
  current one and never ended. It now goes to the offered preset with the nearest render rate (`60x2` to `60`), or to
  the first one when the current preset is not one of Kit's. Covered by `tests/test_cycle.py`.

## [1.0.11] - 2026-10-07
### Fixed
- With no preset selected, refreshing the presets (for example when the renderer reports DLSS-G support) no longer
  sets the menubar button's text to an empty string, which hid the FrameRate button. It keeps the name, as the first
  build does. Kit 111 exposed this once omni.kit.viewport.menubar.core 107.2.5 (Kit #1851) stopped rebuilding the
  menubars when the render backend is selected.

## [1.0.10] - 2025-04-09
### Changed
- Updated documentation with AI agent.

## [1.0.9] - 2023-12-06
### Fixed
- Fix issue with "x2" DLSS-G presets not enabled in some apps

## [1.0.8] - 2023-10-16
### Added
- Allow frame pacing presets to be cycled with a hotkey

## [1.0.7] - 2023-08-09
### Fixed
- Support thread presets on Kit 105.2

## [1.0.6] - 2023-05-15
### Fixed
- Rename Uncapped to No Pacing when switching to PathTracing too

## [1.0.5] - 2023-05-12
### Fixed
- Track dlssg/supported setting in case it changes after startup

## [1.0.4] - 2023-05-11
### Changed
- Changed default preset to "No Pacing"

## [1.0.3] - 2023-05-05
### Fixed
- Skip setting viewport tickrate to avoid issue creating second viewport

## [1.0.2] - 2023-05-03
### Changed
- Remove None preset
- Rename Precise to Uncapped
- Only show x2 presets when DLSS-G is available

## [1.0.1] - 2023-03-28
### Changed
- OM-87831: Sync with different viewports

## [1.0.0] - 2023-03-15
### Added
- Initial version.

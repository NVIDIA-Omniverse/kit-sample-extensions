# Changelog

omni.sample.ui_scene.slider_manipulator

## [2.0.4] - 2026-11-05

### Changed

- Remove the temporary `-ovrtx` tag from `omni.kit.hydra_texture` dependency requests.

## [2.0.3] - 2026-10-23

- Require Kit 111.0 or later to prevent compatibility collisions with Kit 110.4 packages.

## [2.0.2] - 2026-10-23
### Removed
- Legacy viewport registration and selection suppression, including the dependency on `omni.kit.manipulator.viewport`. The sample uses `omni.kit.viewport.registry` for viewport integration.

## [2.0.1] - 2026-01-14
### Fixed
- Add guard for zero width to prevent division by zero in slider drag
- Clamp slider value between 0.0 and 1.0
- Add guard for zero min/max range
- Clear manipulator properly when selection is empty or prim is not Imageable

## [2.0.0] - 2023-03-14
### Changed
- Update to Kit 105 SDK.

## [1.2.1] - 2022-06-17
### Added
- Documentation

## [1.2.0] - 2022-06-01
### Changed
- Full refactoring

## [1.1.1] - 2021-12-22
### Changed
- Fixes for tests on 103.0+release.679.1bc9fadb

## [1.1.0] - 2021-12-06
### Changed
- Using the model-based SceneView
### Added
- Support for HoverGesture

## [1.0.1] - 2021-11-25
### Changed
- Default aspect ratio to match Kit Viewport
- Renamed Intersection to GesturePayload (need omni.ui.scene 1.1.0)

## [1.0.0] - 2021-11-19
### Added
- The initial documentation

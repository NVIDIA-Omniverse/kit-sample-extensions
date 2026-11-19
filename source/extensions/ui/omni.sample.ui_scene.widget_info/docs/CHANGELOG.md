# Changelog

omni.sample.ui_scene.widget_info

## [2.0.3] - 2026-11-05

### Changed

- Remove the temporary `-ovrtx` tag from `omni.kit.hydra_texture` dependency requests.

## [2.0.2] - 2026-10-23

- Require Kit 111.0 or later to prevent compatibility collisions with Kit 110.4 packages.

## [2.0.1] - 2026-01-14
### Fixed
- Fixed incorrect extension name in changelog
### Added
- Added `__del__` destructor to `_ViewportLegacyDisableSelection` to properly re-enable selection rect on cleanup

## [2.0.0] - 2023-03-14
### Changed
- Update to and lock extension to USD-22.11.

## [1.0.1] - 2022-06-01
### Changed
- It doesn't recreate sc.Widget to avoid crash

## [1.0.0] - 2022-5-1
### Added
- The initial version

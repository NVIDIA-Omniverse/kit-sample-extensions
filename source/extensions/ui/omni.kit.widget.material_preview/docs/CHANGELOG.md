# Changelog

## [1.1.4] - 2026-08-26
### Fixed
- OMPE-80508: Fix two call sites that still used the deprecated `omni.kit.renderer_capture` module
  while the file already imported `omni.kit.renderer.capture`. They resolved only because the capture
  extension imported the deprecated alias at startup, which it no longer does.
  `convert_raw_bytes_to_list` is imported with a fallback, because the public package only re-exports
  it from the kit release that moved the capture bindings into it.

## [1.1.3] - 2026-03-18
### Changed
- change enable_emission from float to bool in local swatch files

## [1.1.2] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.1.1] - 2025-09-03
### Changed
- OMPE-57994: Update to use Events 2.0 for hydra texture events.

## [1.1.0] - 2025-08-29
### Changed
- OMPE-57994: Update to use Events 2.0

## [1.0.16] - 2024-03-04
### Fixed
- missing necessary import

## [1.0.15] - 2024-02-29
### Fixed
- RelevantStage doesn't have the same render setting as the source stage

## [1.0.14] - 2023-12-05
### Changed
- Support other renderers in MaterialPreviewProducer and test against Storm.

## [1.0.13] - 2023-12-05
### Changed
- Increase the test timeout to 1200

## [1.0.12] - 2023-12-05
### Changed
- Fix the flaky test due to timeout issue

## [1.0.11] - 2023-11-08
### Changed
- Fix the test. Remove omni.hydra.rtx dependency and increase the timeout to reduce the chance of timeout failure

## [1.0.10] - 2023-10-31
### Added
- Added tests to increase code coverage

## [1.0.9] - 2023-10-17
### Fixed
- Update to proper API calls instead of deprecated legacy versions.
- Make sure to use newer API's only when resource is valid, not at arbitrary times

## [1.0.8] - 2023-10-11
### Fixed
- Fix test when Fabric Scene Delegate is enabled

## [1.0.7] - 2022-09-07
### Fixed
- Fix test to not rely on renderer variations

## [1.0.6] - 2022-06-07
### Changed
- Handle runtime exception from hydra_texture.get_drawable_ldr_resource()

## [1.0.5] - 2022-04-25
### Added
- Test

## [1.0.4] - 2022-03-30
### Changed
update repo_build and repo-licensing

## [1.0.3] - 2021-10-26
- update repo in extension.toml

## [1.0.2] - 2021-08-03
### Changed
- Fixed secondary preview window not updated properly due to the same prim path for
source and target material. This is just a workaround, and the actual fix should be
in rendering

## [1.0.1] - 2021-07-28
### Changed
- Fixed material preview for mdl in the server which uses relative path as the asset path
- Fixed a small coding bug

## [1.0.0] - 2021-07-02
### Added
- Initial extension. Separated this plugin from omni.kit.window.material_preview
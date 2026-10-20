# Changelog

## [110.0.7] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: remove the optional dependency on the retired Substance file-format extension.

## [110.0.5] - 2026-07-03
### Changed
- OMPE-58591: Clarify the error shown when the Asset Path is not inside a collection folder and the process cannot run.

## [110.0.4] - 2026-06-25
### Changed
- OMPE-96692: Bump urllib3>=2.7.0.

## [110.0.3] - 2026-02-26
### Fixed
- OMPE-83346: Add missing `channel` parameter to `omni.log.error()` and `omni.log.warn()` calls in `_log_results()` so messages are logged as `[omni_asset_validator]` and matched by the existing `stdoutFailPatterns.exclude` filter.

## [110.0.2] - 2026-02-10
### Changed
- OMPE-78066: Bump certifi>=2023.7.22 and  urllib3>=2.6.3.

## [110.0.1] - 2026-01-19
### Changed
- Bump version.

## [1.4.0] - 2025-12-31
### Changed
- OMPE-73696: Update Kit SDK to version 110.

## [1.3.1] - 2025-12-12
### Changed
- OMPE-74615: Update to use urllib3 >= 2.6.0.

## [1.3.0] - 2025-06-11
### Changed
- Update Kit SDK to version 108.

## [1.2.2] - 2025-02-20
### Changed
- Update Kit SDK to fix registry issue.

## [1.2.1] - 2025-02-19
### Changed
- Change omni.usd.fileformat.sbsar to optional dependency.

## [1.2.0] - 2025-02-10
### Changed
- Update public API

## [1.1.3] - 2024-12-12
### Changed
- Make omni.configurator_publisher compatible with Kit 107

## [1.1.2] - 2024-10-17
### Changed
- Cache generation now has a Python fallback to the caching graph that will trigger all variants in the stage.
- Fix zip bloated file by providing the same compression as is default in 7 zip

## [1.0.2] - 2024-05-24
### Changed
- Added scrolling frame to asset validator options.

## [1.0.1] - 2024-05-15
### Changed
- Fix sbsar baking.

## [1.0.0] - 2024-05-07
### Changed
- Rename publisher to "Configurator Publisher".

## [0.9.26] - 2024-03-14
### Changed
- Only set kit application path before generating cache.

## [0.9.25] - 2024-03-13
### Changed
- Append ext cache directories to launch args to avoid syncing exts from registry.

## [0.9.24] - 2024-03-07
### Changed
- Improve the way to run validator to avoid blocking main thread.

## [0.9.23] - 2024-02-28
### Changed
- Fix cache generation issue that adds an additional space to writeWithAssetRoot argument.

## [0.9.22] - 2024-02-27
### Changed
- Add cancel button where the user could cancel the current task
- Add time elapsed information under progress bar, and change color to warn user when duration exceeds warning limit

## [0.9.21] - 2024-02-27
### Changed
- Disable "default prim only" option by default.

## [0.9.20] - 2024-02-26
### Changed
- Add optimizer.core and validator.core as requirements to kit profile.

## [0.9.19] - 2024-02-23
### Changed
- Fix f-string format issue.

## [0.9.18] - 2024-02-22
### Changed
- Fix test failures on TeamCity.

## [0.9.17] - 2024-02-22
### Added
- Close default stage if it's opened to avoid influencing cache generation.

## [0.9.16] - 2024-02-21
### Added
- Replace USD Layer folder with specifying kit application scripts/exe.
- Improve cache generation script for old kit that has issue to start with scripts.
- Improve UX to provide more log info, and separate validator/optimizer/cache log out of the host instance log.

## [0.9.15] - 2024-02-19
### Added
- Remove operation for removing primvar from default scene optimizer config.

## [0.9.14] - 2024-02-08
### Added
- Don't use customized max mean error if optimizer config is provided from UX.

## [0.9.13] - 2024-02-06
### Added
- Fix issue of copying optimizer config when optimization phase is not enabled.

## [0.9.12] - 2024-02-05
### Added
- Improve optimizer script to support optimizing meshes per USD file instead of stage.

## [0.9.11] - 2024-02-05
### Added
- More fix to copy optimizer configs.

## [0.9.11] - 2024-02-05
### Added
- Integrate validator into publisher.
- Use max mean value only when it's specified.
- Fix optimizer config copy issue.
- Improvements to ensure each phase can be ran separately.

## [0.9.9] - 2024-01-31
### Added
- Add unittest.

## [0.9.8] - 2024-01-30
### Changed
- Adds maxMeanError field in UI, it will override the default config json's maxMeanError value
- Now before scene optimize runs, it will try to copy over json files associated with payload usds and use those as
  scene optimizer config
- Fix issue with recursive glob in scene optimizer script

## [0.9.7] - 2024-01-29
### Changed
- Update kit sdk to support checkpoint time based collection.

## [0.9.6] - 2024-01-25
### Changed
- Added USD player installation location selection in main UI
- Changed UJITSO cache generation script, trigger action graph instead of doing variant permutation in script

## [0.9.5] - 2024-01-19
### Changed
- Removed load order for fileformat.sbsar.
- Changed default optimizer config mean error tolerance.

## [0.9.4] - 2024-01-15
### Added
- Clean up dependencies.
- Add customized app profile for running Kit instnace to generate cache.
- Window will not show on start up.

## [0.9.3] - 2024-01-12
### Added
- Fix possible hang caused during cache generation.

## [0.9.2] - 2024-01-12
### Added
- Improvements for UX.
- Renamed some UI elements and updated tooltips to be more accurate.
- Changed zip function from USD zip to python zip to fix zip preview and header file issue.
- Updated collected package name, new structure is `<stage_name>_collected_<uuid>`.
- Added default config json for scene optimizer.
- Added support for settings for collector.
- Added support for toggling phases on/off by directly clicking on the phase label in the main window.

## [0.9.1] - 2024-01-11
### Added
- Improvements for UX.
- Add scene optimization phase
- Hide upload phase for now

## [0.9.0] - 2024-01-09
### Added
- Improvements for UX.
- New processes that support UJITSO cache generation, and baking SBSAR materials.
- Code cleanup and fixes.

## [0.0.8] - 2023-09-20
### Added
- Step settings - makes it possible to run chosen or all steps (collect/zip/upload)
## [0.0.7] - 2023-09-12
### Added
- Added zip name to allow for versioning in the name before uploading.
## [0.0.6] - 2023-06-21
### Changed
- Put button to load token next to the token field.
## [0.0.5] - 2023-06-20
### Changed
- remove os rename and using omni.client instead
## [0.0.4] - 2023-06-20
### Added
- Utility to load token for OVC testing.
## [0.0.3] - 2023-05-16
### Added
- Progress meter to inform user of collection progress.
### Changed
- Zipping asynchronous
## [0.0.2] - 2023-05-15
### Added
- Extension documentation
### Changed
- Renamed Product Id to Title Id, because that is the parameter in the GDN portal

## [0.0.1] - 2023-05-12
### Added
- Collect asset
- After collection enforce "product_configurator_base" name of main file
- Zip with name based on asset
- Upload

# Changelog
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [5.0.2] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: remove the unavailable MDL baking dependency and report unsupported baking explicitly.

## [5.0.1] - 2026-06-02
- Update kit-kernel to version 110.1.1

## [5.0.0] - 2026-05-29
- Update Asset Converter dependency

## [4.0.7] - 2026-04-14
- Update kit-kernel version

## [4.0.6] - 2026-03-18
- Update kit-kernel version

## [4.0.5] - 2025-08-14
- Improve unit test code coverage

## [4.0.4] - 2025-07-31
- Add version constraint to omni.kit.asset_converter

## [4.0.3] - 2025-07-30
- Exclude omni.grpc.lib load error in test.

## [4.0.2] - 2025-07-01
- Build flavors

## [4.0.1] - 2025-06-13
- Clean up extension documentation

## [4.0.0] - 2025-05-14
- Update to Kit 108, USD 25.02, and Python 3.12

## [3.1.0] - 2025-04-29
- Add support for linux-aarch64

## [3.0.3] - 2025-03-21
- Update kit-kernel

## [3.0.2] - 2025-03-21
- Update Support Level from Enterprise to Core

## [3.0.1] - 2025-02-14
- Same as 3.0.0 but with clean record in packman

## [3.0.0] - 2025-02-05
- Switch to new ABI

## [2.0.6] - 2025-01-30
- Disable baking test

## [2.0.5] - 2025-01-29
- Disable neuray tests

## [2.0.4] - 2025-01-24
- Enable tests related to Neuray libs again
- Add test for baking MDL with texture

## [2.0.3] - 2025-01-03
- Update to kit-kernel 107.0.3

## [2.0.2] - 2025-01-02
- Disable tests related to Neuray libs

## [2.0.1] - 2024-12-13
- Update to Kit Kernel 107

## [2.0.0] - 2024-11-12
- Update to Kit 107

## [1.6.0] - 2024-11-26
- Update assimp to 5.4.3 and fix obj export.

## [1.5.0] - 2024-11-20
- Update to Kit-kernel 106.5

## [1.4.2] - 2024-11-14
- Add USDZ export through File/Export menu.

## [1.4.1] - 2024-10-18
- Target specific Kit version

## [1.4.0] - 2024-10-16
- Update to latest Kit 106.4

## [1.3.3] - 2024-03-13
- Fix 'bool' object is not callable error for material baking option

## [1.3.2] - 2024-01-17
- Mark test_export_from_menu test as flaky.

## [1.3.1] - 2023-12-15
- Improve tests to increase coverage.
- Replace customized filepicker as omni.kit.window.file_exporter.

## [1.3.0] - 2023-11-01
- Bump ext minor version.

## [1.2.14] - 2023-10-25
### Changed
- Make 'ProgressPopup' modal by default.

## [1.2.13] - 2023-10-19
### Changed
- Updated menus to use actions

## [1.2.12] - 2023-09-21
### Changed
- Add export option for gltf with NV_materials_mdl vendor extension.
- Bake materials to new materials when exporting to glTF with NV_materials_mdl.

## [1.2.11] - 2023-08-18
### Changed
- Don't show bake material option when import distill extension failed.

## [1.2.10] - 2023-07-28
### Changed
- Strip off `file:` prefix from path picked from file browser.

## [1.2.9] - 2023-07-25
### Changed
- Disable options that are not supported by obj exporter.

## [1.2.8] - 2023-07-14
### Changed
- Show gltf export option only for gltf export.

## [1.2.7] - 2023-07-11
### Changed
- Add export option to control gltf export separate bin file.

## [1.2.6]
### Changed
- Add bake material to export options.

## [1.2.5]
### Changed
- Fix file picker caused by behavior changes.

## [1.2.4]
### Changed
- Bump version to republish

## [1.2.3] - 2023-03-13
### Changed
- Fix issue when selected filebrowser item is not directly under current directory, the result file path
  didn't include the folder paths in between.

## [1.2.2] - 2023-02-01
### Changed
- Disable apply button if filename is not specified

## [1.2.1] - 2023-01-17
### Changed
- Update file picker apply button label to "Import/Export"

## [1.2.0] - 2022-12-21
### Changed
- Replace prompt to omni.kit.widget.prompt.

## [1.1.8] - 2022-08-08
### Changed
- Support export STL files.

## [1.1.7] - 2022-05-04
### Changed
- Support export lights for gltf.

## [1.1.6] - 2022-03-30
### Changed
- Bump version to update licensing build.

## [1.1.5] - 2022-03-08
### Changed
- Add options to export visible prims only.

## [1.1.4] - 2022-02-25
### Changed
- Add unittests for exporter.

## [1.1.3] - 2022-02-07
### Changed
- Fix compatibility issue of file picker between release and daily kit.

## [1.1.2] - 2021-12-29
### Changed
- Fix file browser to pick folder.

## [1.1.1] - 2021-12-17
### Changed
- Improve file picker to save file.

## [1.1.0] - 2021-12-16
### Changed
- Enable textures embedding by default.

## [1.0.8] - 2021-10-06
### Changed
- Improve exporter for better material export.

## [1.0.7] - 2021-07-22
### Changed
- Add support to submit to Omniverse Farm.

## [1.0.6] - 2021-05-07
### Changed
- Add glb export support.

## [1.0.4] - 2021-03-30
### Changed
- Update extension icon.

## [1.0.2] - 2021-02-07
### Fixed
- Fix packaging issue.

## [1.0.1] - 2021-01-26
### Added
- Add options dialog to control export.

## [1.0.0] - 2021-01-20
### Added
- Initialize exporter extension.

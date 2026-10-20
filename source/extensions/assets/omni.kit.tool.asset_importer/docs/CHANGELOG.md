# Changelog

## [6.0.3] - 2026-09-02
- Fix app hang/crash caused by blocking `omni.client.stat` call during drag/drop hover

## [6.0.2] - 2026-06-23
- Regression fix for filepicker 3.x options pane.
- Fix duplicate importer registration bug

## [6.0.1] - 2026-06-02
- Update kit-kernel to version 110.1.1

## [6.0.0] - 2026-05-29
- Update Asset Converter dependency

## [5.2.0]
- Add drag/drop import support for registered Asset Importer formats.

## [5.1.5] - 2026-04-14
- Update kit-kernel version

## [5.1.4] - 2026-03-18
- Update kit-kernel version

## [5.1.3] - 2025-10-24
- Import menu items now properly display on startup after content browser directory initialization

## [5.1.2] - 2025-10-10
- Fixed docs build

## [5.1.1] - 2025-09-29
- Fixed issue where the default output file name doesn't match the input file name stem

## [5.1.0] - 2025-09-19
- Sort registered converters by their priority in Converter Options UI when multiple converters support the same file type

## [5.0.5] - 2025-08-14
- Improve unit test code coverage
- Update scene optimizer option panel visibility based on the selected converter

## [5.0.4] - 2025-07-31
- Add version constraint to omni.kit.asset_converter

## [5.0.3] - 2025-07-04
- Don't support folder in importer delegate support format.

## [5.0.2] - 2025-07-01
- Build flavors

## [5.0.1] - 2025-06-13
- Clean up extension documentation

## [5.0.0] - 2025-05-14
- Update to Kit 108, USD 25.02, and Python 3.12

## [4.3.1] - 2025-06-02
- Resolved display name issue when importing converted assets as references

## [4.3.0] - 2025-04-29
- Add support for linux-aarch64

## [4.2.0] - 2025-04-23
- Add feature to export as .usdz

## [4.1.1] - 2025-04-21
- Fix omni.kit.tool.asset_importer test in OVC2.

## [4.1.0] - 2025-03-20
- Added converter select UI option
- Update kit-kernel

## [4.0.4] - 2025-03-21
- Update Support Level from Enterprise to Core

## [4.0.3] - 2025-03-21
- Fix doc build errors.

## [4.0.2] - 2025-03-13
- Don't show options pane for folder.

## [4.0.1] - 2025-02-14
- Same as 4.0.0 but with clean record in packman

## [4.0.0] - 2025-02-05
- Switch to new ABI

## [3.0.3] - 2025-01-15
- Resolve unit test failure.

## [3.0.2] - 2025-01-03
- Update to kit-kernel 107.0.3

## [3.0.1] - 2024-12-13
- Update to Kit Kernel 107

## [3.0.0] - 2024-11-12
- Update to Kit 107

## [2.12.0] - 2024-11-26
- Update assimp to 5.4.3.

## [2.11.0] - 2024-11-20
- Update to Kit-kernel 106.5

## [2.10.3] - 2024-10-21
- Replace info icon with text due to scaling issue.

## [2.10.2] - 2024-10-21
- Move quick link to right and add tooltip.

## [2.10.1] - 2024-10-18
- Target specific Kit version

## [2.10.0] - 2024-10-17
- Add optional scene optimizer config frame.

## [2.9.0] - 2024-10-16
- Update to latest Kit 106.4

## [2.8.0] - 2024-10-15
- Add support to convert PLY file to USD.

## [2.7.0] - 2024-10-04
- Add option to specify USD output file format.
- Add option to specify USD output file name.

## [2.6.0] - 2024-10-03
- Added stage up-axis options for using the imported asset's up-axis for the USD stage's up-axis or overriding it with Y-up or Z-up; added combobox (drop-down menu) for selecting the up-axis

## [2.5.7] - 2024-09-11
- Makes option panel's destination frame configurable from importer delegate.

## [2.5.6] - 2024-09-10
- Fix duplicated filter options in UI/UX.

## [2.5.5] - 2024-04-18
- Add enterprise tag.

## [2.5.4] - 2024-02-28
- More improvements to make valid identifier.

## [2.5.3] - 2024-02-19
- Unquote filename before making valid identifier.

## [2.5.2] - 2023-12-05
- Resolve issue with retrieving the input file's file stem

## [2.5.1] - 2023-11-28
- Set "Reference in Current Stage" UI checkbox to true by default. Persist user's last set value within the current session.

## [2.5.0] - 2023-11-01
- Bump ext minor version.

# [2.4.38] - 2023-11-01
- Fix ETM test failure.

# [2.4.37] - 2023-10-26
- Asset importer should respect reference default.

# [2.4.36] - 2023-10-25
- Make 'ProgressPopup' modal by default.

# [2.4.35] - 2023-10-19
- Update menus to use actions

# [2.4.34] - 2023-10-25
- Add test for filepicker should not return local paths with %20 instead of space

# [2.4.33] - 2023-10-18
- Make importer remember last path user used to import.

# [2.4.32] - 2023-10-16
- Remove unused code and improve test coverage

# [2.4.31] - 2023-10-16
- Refactored implementation of 2.4.29

# [2.4.30] - 2023-10-16
- Prevent users from importing to stage during live sessions.

# [2.4.29] - 2023-10-16
- Resolves issue with multiple file conversion via 'Convert-to-USD' workflow

# [2.4.28] - 2023-10-16
- Resolves issue with multiple file import dialogues open at same time
- Fixes issue with path extension

# [2.4.27] - 2023-10-13
## New
- Add a "Add Reference to Stage" checkbox available from all convert/import contexts.

## Fixed
- Can't Choose Folder for Import Path.
- CAD Converter is auto-filling output path.
- Create reference has an "ok" button.

- Note: changes from [2.4.26] were reverted.

# [2.4.28] - 2023-10-17
- Increase code coverage by testing disabling the extension.

# [2.4.26] - 2023-10-13
- Make importer remember last path user used to import.

# [2.4.25] - 2023-10-11
- Use urllib parse to unquote local paths which make by omni.client.utils.make_absolute_url_if_possible.

# [2.4.24] - 2023-10-09
- Align "Convert-to-USD" workflows such that they behave consistently whether workflow is via "Importer" or "Content" window. Update to unit tests

# [2.4.23] - 2023-09-25
- Shared import options bug fix and unit test.

# [2.4.22] - 2023-09-25
- Add omni.kit.menu to dependency to fix test failed.

# [2.4.21] - 2023-09-18
- Added shared import options and AbstractImporterDelegate with UsdStageCache support.

# [2.4.20] - 2023-09-06
- Fix Utils::list_folder_async issue to compute correct relative path.

# [2.4.19] - 2023-08-31
- Early out when destination path is not writeable.

# [2.4.18] - 2023-08-29
- Fix issue that cannot upload folder.

# [2.4.17] - 2023-08-26
- Avoid clipping options panel and other minor improvements.

## [2.4.16] - 2023-07-28
- Strip off `file:` prefix for `File -> Import` to keep back-compatibility.

## [2.4.15] - 2023-07-18
- Made import a publicly accessible Python function and also defined it as an Action.

## [2.4.14] - 2023-06-21
### Changed
- Fix upload files and asset import when they are called from context menu.

## [2.4.13] - 2023-06-07
### Changed
- Ability to preserve original skeleton when converting from FBX to USD

## [2.4.12]
### Changed
- Bump version to republish

## [2.4.11] - 2023-04-06
### Changed
- Fix ETM test failed for kit 104.2.

## [2.4.10] - 2023-03-30
### Changed
- Updated menu Import to after "Open Recent"

## [2.4.9] - 2023-03-21
### Changed
- Add ignore flip rotation to options.

## [2.4.8] - 2023-03-14
### Changed
- Updated menu Import as Reopen as been moved

## [2.4.7] - 2023-03-13
### Changed
- Fix issue when selected filebrowser item is not directly under current directory, the result file path
  didn't include the folder paths in between.

## [2.4.6] - 2023-02-01
### Changed
- Disable apply button if filename is not specified

## [2.4.5] - 2023-01-30
### Changed
- Tentative Fix unittests.

## [2.4.4] - 2023-01-30
### Changed
- Fix unittests.

## [2.4.3] - 2023-01-17
### Changed
- Update file picker apply button label to "Import/Export"

## [2.4.2] - 2023-01-17
### Changed
- Fix unittests.

## [2.4.1] - 2023-01-16
### Changed
- Remove debug log.

## [2.4.0] - 2022-12-21
### Changed
- Replace prompt to omni.kit.widget.prompt.

## [2.3.25] - 2022-12-20
### Changed
- Do not show upload options in read-only context.

## [2.3.24] - 2022-09-22
### Changed
- Skips re-import to avoid crash caused by multi-threads access if output layer is opened already in stage.

## [2.3.23] - 2022-09-08
### Added
- Add support for BVH files.
- Update OmniverseAssetConverter to 7.0.1293.

## [2.3.22] - 2022-09-06
### Changed
- Increase test coverage.

## [2.3.21] - 2022-08-08
### Changed
- Support for STL files.

## [2.3.20] - 2022-03-30
### Changed
- Bump version to update licensing build.

## [2.3.19] - 2022-03-29
### Changed
- Prompts if it's to import USD that's opened already, and more tests.

## [2.3.18] - 2022-03-08
### Changed
- Fix wording issues for importer options dialog.

## [2.3.17] - 2022-02-07
### Changed
- Fix compatibility issue of file picker between release and daily kit.

## [2.3.16] - 2021-12-29
### Changed
- Fix file upload.

## [2.3.15] - 2021-12-17
### Changed
- Improve file picker to select folder.

## [2.3.14] - 2021-12-16
### Changed
- Deprecates useless options.

## [2.3.13] - 2021-12-10
### Changed
- Add callbacks for when the "Import and Convert" dialog is either complete or canceled.

## [2.3.12] - 2021-09-09
### Changed
- Improve "Upload Folder and Files" experience to avoid long waiting before any UI pops up.s

## [2.3.11] - 2021-08-25
### Changed
- Enable UsdPreviewSurface support for importer.

## [2.3.10] - 2021-07-21
### Changed
- Add support to submit to Omniverse Farm when available.

## [2.3.9] - 2021-07-20
### Changed
- Fixes import for checkpoint file.

## [2.3.6] - 2021-07-12
### Changed
- Add optional parameters to `convert_assets` so it can be used to distinguish the called menu entrypoint.

## [2.3.5] - 2021-06-22
### Changed
- Add post-processing step `added_reference` to importer delegate for processing prims after imported into stage.

## [2.3.4] - 2021-05-18
### Fixes
- Fix folder selection if default folder is not existed.

## [2.3.3] - 2021-05-10
### Changed
- Improve alignment of options window.

## [2.3.2] - 2021-05-06
### Changed
- Add notification if import is failed.

## [2.3.1] - 2021-05-05
### Fixes
- Fix folder issue to import single asset from `File -> Import`.
### Changed
- More docs about how to register external importers.

## [2.3.0] - 2021-04-23
### Changed
- Re-org asset importer to support external importers.

## [2.2.6] - 2021-04-15
### Changed
- Add support to import assets directly into stage.

## [2.2.5] - 2021-04-12
### Changed
- Support to import asset by double click file directly.

## [2.2.4] - 2021-03-30
### Changed
- Update extension icon.

## [2.2.2] - 2021-03-29
### Changed
- Support to merge all static meshes during import.

## [2.2.0] - 2021-02-15
### Changed
- Separate importer from Kit as standalone repo.

## [2.1.1] - 2021-02-06
### Changed
- Remove old editor and content window dependencies.

## [2.1.0] - 2021-01-21
### Changed
- Seperates UI and library part by moving library API to omni.kit.asset_converter.

## [2.0.0] - 2020-10-14
### Changed
- Initial extension by moving original importer extension to Kit 2.0 extension.

# CHANGELOG

This document records all notable changes to ``omni.kit.environment.core`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.4.6] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: ignore runtime fallback lights and safely replace duplicate warning windows.

## [1.4.4] - 2026-10-15
### Changed
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then `pump_apply_usd_changes failed (12)` and `PUMP apply_usd_changes ... failed`). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

## [1.4.3] - 2026-08-11
### Fixed
- OMPE-64890: Apply sky changes immediately when the stage root layer is not writable. Scene
  templates are refused with a message on such a stage.

## [1.4.2] - 2025-12-04
### Changed
- Fix test_hdr_sky: verify sky prim instead of image comparison

## [1.4.1] - 2025-11-27
### Changed
- OMPE-72919: Fix test_hdr_sky: set rotation for UsdLux 25.05 dome light in CreateHdriSkyCommand

## [1.4.0] - 2025-08-20
### Changed
- Update to event 2.0

## [1.3.24] - 2025-08-19
- Set light intensity to zero in test asset.

## [1.3.23] - 2025-08-15
- Use local files for test

## [1.3.22] - 2025-07-30
- OMPE-55809: Exclude gpu.foundation error from test to fix ETM failed.

## [1.3.21] - 2025-06-25
- Support rt 2.0 for scene template render settings

## [1.3.20] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [1.3.19] - 2025-04-17
### Changed
- OMPE-43886: Do not copy material to /Environment/Looks when ground material changed

## [1.3.18] - 2025-04-14
### Removed
- Usage and checks for legacy Viewport

## [1.3.17] - 2025-04-09
### Changed
- OMPE-43108: Use TempDirectory for test because extension path is not writable in OVC2

## [1.3.16] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [1.3.15] - 2024-11-13
### Change
- Update for kit 107 with usd 24 and python 3.11

## [1.3.14] - 2024-07-23
### Change
- OMPE-13772: Added missing dependency "omni.kit.window.filepicker" for test

## [1.3.13] - 2024-07-23
### Change
- OMPE-14781: Added missing dependency "omni.kit.notification_manager"

## [1.3.12] - 2024-05-31
### Change
- OMPE-9282: Add hovered/pressed style to buttons in warning window

## [1.3.11] - 2024-05-31
### Change
- Remove printf

## [1.3.10] - 2023-10-17
### Change
- Increase code coverage to 87.6%

## [1.3.9] - 2023-08-16
### Change
- OM-100365: Set template shader Z up to match current stage axis

## [1.3.8] - 2023-08-15
### Change
- OM-89354: Set specular to 0 for default ground mdl
- Do not check ground material settings when startup (already done when apply)

## [1.3.7] - 2023-08-14
### Change
- Fix Reset Button status error for string model

## [1.3.6] - 2023-08-02
### Change
- OM-104065: Fix error if ENVIRONMENT_PRIM_ROOT becomes inactive

## [1.3.5] - 2023-07-26
### Change
- OM-103030: In living mode, add template in live layer

## [1.3.4] - 2023-07-25
### Change
- OM-101618: Custom notification for Presenter to indicate Sun Study only works with dynamic skies, no buttons to add one.

## [1.3.3] - 2023-06-27
### Change
- OM-97507: When ground material changed, bind it again with cloned material in same layer as old binding

## [1.3.2] - 2023-06-21
### Change
- OM-89354: Change "roughness amount" to 0.0 in default ground material

## [1.3.1] - 2023-06-12
### Change
- OM-66083: Restore all render settings to default before applying new render settings with scene templates.

## [1.3.0] - 2023-06-05
### Change
- OM-54602: Use sub layer to apply scene template to make variants work

## [1.2.23] - 2023-05-31
### Change
- OM-96740: Prevents _update_fog() from throwing an exception for a missing texture.

## [1.2.22] - 2023-05-29
### Change
- OM-66083: Apply render settings with float array value

## [1.2.21] - 2023-05-25
### Change
- OM-66083: Update message when applying template with render settings

## [1.2.20] - 2023-05-25
### Change
- OM-66083: Support templates with sub layers

## [1.2.19] - 2023-05-23
### Change
- OM-95581 & OM-95470: Do not always save ground type to stage file

## [1.2.18] - 2023-05-15
### Change
- OM-66083: Try loading render settings when applying a scene template

## [1.2.17] - 2023-05-09
### Change
- OM-93823: Do not create /Environment for a empty stage

## [1.2.16] - 2023-05-08
### Change
- OM-93590: Support payload in payload

## [1.2.15] - 2023-04-26
### Change
- OM-89354: Change default ground material
- OM-91494: Reset ground type when ground prim deleted

## [1.2.14] - 2023-03-23
### Change
- Use texCoord2f[] for primvars:st type.

## [1.2.13] - 2023-03-15
### Change
- Use texCoord2d[] for primvars:st type.

## [1.2.12] - 2023-03-06
### Change
- Fix bug OM-84062: Create crash to open a file if sunstudy is playing on the previous one.

## [1.2.11] - 2023-02-21
### Change
- Fix errors for python 3.10

## [1.2.10] - 2023-02-15
### Changed
- ETM: Wait for a few frames for perference page test

## [1.2.9] - 2023-02-14
### Changed
- OM-79422: set ground size when stage opened

## [1.2.8] - 2023-02-04
### Changed
- OM-80044: Only check prims under Environment root for better scene load time

## [1.2.7] - 2023-01-30
### Changed
- OM-79609: Do not make stage dirty after stage opened

## [1.2.6] - 2023-01-12
### Changed
- Update api usage for create_filepicker, use show_file_importer instead

## [1.2.5] - 2023-01-09
### Changed
- OM-77580: Ignore error message in Linux ETM tests with kit 105

## [1.2.4] - 2022-12-13
### Changed
- OM-75837: Custom notificaton for View to indicate Sun Study only works with dynamic skies, no buttons to add one.

## [1.2.3] - 2022-12-13
### Changed
- OM-73228: there may be a empty sky prim. Also need to clean up before creating new sky

## [1.2.2] - 2022-11-09
### Changed
- OM-71227: Handle error in broken stage file

## [1.2.1] - 2022-11-09
### Added
- OM-36606: Show warning dialog if extra lights already exist when applying environment
- OM-66383: Set /Environment to be Xform by default

## [1.2.0] - 2022-10-27
### Added
- Enable sky parameters for weather (cumulus enabled, cloud coverage and haze)
- Make actions be optional

## [1.1.8] - 2022-10-20
### Changed
- Update test for ETM failure

## [1.1.7] - 2022-10-19
### Changed
- Update test for ETM failure

## [1.1.6] - 2022-10-14
### Changed
- OM-65268: update prim payload when importing scene template

## [1.1.5] - 2022-10-12
### Changed
- Remove hang detector disabling

## [1.1.4] - 2022-10-12
### Changed
- Fix OM-64709: correct misspell (Helenzki=>Helsinki)

## [1.1.3] - 2022-10-01
### Changed
- Test skies on s3 instead of local to reduce ext size
- Test action instead of static functions

## [1.1.2] - 2022-09-23
### Added
- OM-58989: Convert more asset path when import scene

## [1.1.1] - 2022-09-13
### Changed:
- OM-62555 & OM-57577: Live mode, create ENV in .live file. Otherwise, in root layer.

## [1.1.0] - 2022-09-10
### Added
- OM-44838: Add action to import sky

## [1.0.36] - 2022-09-10
### Fixed
- Fix error when apply some env templates such as "display_pedestal"

## [1.0.35] - 2022-09-01
### Fixed
- OM-60964: Update texture files for shader when apply template

## [1.0.34] - 2022-08-30
### Fixed
- OM-61214/61213: Update ETM test failure, udpate preference test

## [1.0.33] - 2022-08-26
### Changed
- OM-60964: Update texture file for RectLight when apply template

## [1.0.32] - 2022-08-04
### Changed
- If sky file defined in persitent not found, change to the one in default setting

## [1.0.31] - 2022-07-17
### Fixed
- OM-53986: refresh sky data when stage opened to make sure env params are correctly configured

## [1.0.30] - 2022-06-25
### Changed
- Remove omni.kit.window.viewport

## [1.0.29] - 2022-06-22
### Add
- Add tests

## [1.0.28] - 2022-06-01
### Fix
- Fix typo of "Los Angeles"

## [1.0.27] - 2022-05-07
### Changed
- Verify default ground material. If not exists, clear and disable auto ground.

## [1.0.26] - 2021-04-19
### Changed
- Verify sub id exists when applying ground material

## [1.0.25] - 2021-04-19
### Changed
- Fix drop scene template issue

## [1.0.24] - 2021-04-11
### Changed
- Remove sync calls

## [1.0.23] - 2021-04-11
### Changed
- Fix sunstudy does not work if reopen stage

## [1.0.22] - 2021-04-07
### Changed
- Fix error if startup with no stage

## [1.0.21] - 2021-04-04
### Changed
- Set camera when applying template

## [1.0.20] - 2021-03-31
### Changed
- Update texture file path of domelight when applying template

## [1.0.19] - 2021-03-30
### Changed
- Republish for repo updates
- Update shader asset path when applying template

## [1.0.18] - 2022-03-18
### Added
- Add material sub identifier for ground
### Changed
- Default ground material

## [1.0.17] - 2022-03-17
### Changed
- Support tokens in env default url

## [1.0.16] - 2022-02-26
### Changed
- Make sure filename input when save as new template

## [1.0.15] - 2022-02-25
### Changed
- "Add Dynamic Sky" change to "Go to Dynamic Skies"
- Update preference page to remove env type

## [1.0.14] - 2022-02-15
### Changed
- Default scene template

## [1.0.13] - 2022-02-14
### Added
- Setting "/app/sunstudy/enable" to enable/disable sunstudy play button

## [1.0.12] - 2022-02-14
### Fixed
- Do not create default ground if applying template with ground to a empty stage

## [1.0.11] - 2022-02-10
### Fixed
- Create ground without /Environment defined

## [1.0.10] - 2022-02-10
### Fixed
- Update referene asset path when apply templates

## [1.0.9] - 2022-02-09
### Fixed
- Load env params from stage file

## [1.0.8] - 2022-01-26
### Fixed
- Load ground type correctly when import from scene template

## [1.0.7] - 2022-01-26
### Changed
- Use prim copy instead of sub layer for scene template to better save/save as

## [1.0.6] - 2022-01-24
### Changed
- Make sure ground material in /Environment/Looks

## [1.0.5] - 2022-01-24
### Changed
- Use sublayer for scene template

## [1.0.4] - 2022-01-18
### Changed
- Fix issue if no stage when startup

## [1.0.3] - 2022-01-07
### Added
- Add setting for current sky type in sunstudy

## [1.0.2] - 2022-01-04
### Changed
- Fix the issue for PropertyValueModel users

## [1.0.0-beta.13] - 2021-12-13
### Changed
- Clean old scene template before applying new one
- Change the way to apply scene template
## [1.0.0-beta.12] - 2021-12-07
### Changed
- Change ground shadow

## [1.0.0-beta.11] - 2021-12-04
### Added
- Add reset button

## [1.0.0-beta.10] - 2021-12-02
### Changed
- Update ground mesh uv when ground changed

## [1.0.0-beta.9] - 2021-12-01
### Changed
- Adjust transform for scene templates

## [1.0.0-beta.8] - 2021-11-26
### Fixed
- Fix clouds do not change when playing

## [1.0.0-beta.7] - 2021-11-25
### Added
- extra setting for VIEW to change sky material mdl param
### Changed
- Sunstudy time slider argument

## [1.0.0-beta.6] - 2021-11-25
### Added
- Min/max for environment location properties
### Changed
- Apply scene template

## [1.0.0-beta.5] - 2021-11-24
### Changed
- Use PropertyValueModel in sunstudy player

## [1.0.0-beta.4] - 2021-11-24
### Fixed
- Points for ground to 1 meter for 0-1 UV space

## [1.0.0-beta.3] - 2021-11-23
### Changed
- Ground for Z-up
- UV for ground
- Location edit works

## [1.0.0-beta.2] - 2021-11-22
### Changed
- Default enable "visible in primary Ray" for hdri skies
- Change the way to trace usd changes

## [1.0.0-beta.1] - 2021-10-29
### Added
- First beta

# Changelog

## [1.21.1] - 2026-10-06
### Fixed
- Do not ship a second copy of core's `pip_prebundle`. With two copies, `omni.asset_validator` had two origins
  and Kit 111's omni.kit.test refused to start its coverage, so no test ran.

## [1.21.0] - 2026-09-02
### Added
- Add the instance prototypes validation setting.

### Changed
- Update to core `1.21.0`.

## [1.20.2] - 2026-07-27
### Changed
- Update to core `1.20.2`.

## [1.20.1] - 2026-07-02
### Changed
- Update to core `1.20.1`.

## [1.20.0] - 2026-07-02
### Changed
- Update to core `1.20.0`.

## [1.19.7] - 2026-06-24
### Changed
- Update to core `1.19.7`.

## [1.19.6] - 2026-06-15
### Changed
- Update to core 1.19.6

## [1.19.5] - 2026-06-11
### Fixed
- Resolve requirement references before displaying feature and capability options

### Changed
- Update to core 1.19.5

## [1.19.4] - 2026-05-20
### Changed
- Update to core 1.19.4

## [1.19.3] - 2026-05-19
### Fixed
- Guard `AssetResultsModel.asset_name` against plain asset identifiers without `/` or `@`

## [1.19.2] - 2026-05-15
### Changed
- Update to core 1.19.2

## [1.19.1] - 2026-05-12
### Changed
- Update to core 1.19.1

## [1.19.0] - 2026-05-11
### Changed
- Update to core 1.19.0

## [1.18.1] - 2026-04-29
### Changed
- Update to core 1.18.1
### Fixed
- Select In Stage now selects the underlying prim for schema-typed issue locations instead of the stage root

## [1.18.0] - 2026-04-27
### Changed
- Update to core 1.18.0

## [1.17.0] - 2026-04-17
### Added
- Fix failure shown inline in issue info label; removed Fix Result column
### Changed
- Update to core 1.17.0

## [1.16.0] - 2026-04-14
### Added
- Add full Profile support to UI
### Changed
- Update to core 1.16.0

## [1.15.1] - 2026-03-24
### Added
- Extract UI commands into dedicated `commands/` package
### Fixed
- Collapse multi-location identifiers into a collapsible frame to avoid pushing the action button off-screen
- Restore Action column header and add text labels to Apply Fix and Select Object buttons

## [1.15.0] - 2026-03-22
### Added
- Replace Apply fix/Fix manually text with icons
- Hide Action column header and reduce column width
- Multiple suggestions per issue
- Merge Suggestion and Location columns into a single cascading selector
- Support multiple locations (`at=[prim1, prim2]`) — Asset column renders one label per identifier
### Changed
- Update to core 1.15.0

## [1.14.0] - 2026-03-16
### Added
- Add autovalidate setting to skip re-validation after fix
### Changed
- Update to core 1.14.0

## [1.13.0] - 2026-03-10
### Changed
- Report results on progress
- Update to core 1.13.0

## [1.12.0] - 2026-02-26
### Fixed
- `CapabilitiesModel`: Updates on both requirements and capability changes.
- `FeaturesModel`: Updates on both requirements and features changes.
- `ProfilesModel`: Updates on both requirements and profiles changes.
### Changed
- Update to core 1.12.0

## [1.11.2] - 2026-02-25
### Changed
- Update to core 1.11.2

## [1.11.1] - 2026-02-17
### Changed
- Update to core 1.11.1

## [1.11.0] - 2026-02-11
### Changed
- Update Python dependency 1.11.0

## [1.10.8] - 2026-02-08
### Changed
- Update Python dependency 1.10.8

## [1.10.7] - 2026-02-06
### Changed
- Update Python dependency 1.10.7

## [1.10.6] - 2026-01-27
### Changed
- Update to core 1.10.6

## [1.10.5] - 2026-01-15
### Changed
- Improve inheritance of widget components.
- Update to core 1.10.5

## [1.10.4] - 2026-01-14
### Changed
- Update to core 1.10.4

## [1.10.3] - 2026-01-09
### Changed
- Update to core 1.10.3.

## [1.10.2] - 2026-01-09
### Changed
- Update to core 1.10.2.

## [1.10.1] - 2026-01-08
### Changed
- Update to core 1.10.1.

## [1.10.0] - 2026-01-06
### Changed
- Update style of report labels.
- Update UI documentation to reflect latest changes.
- Update to core 1.10.0.

## [1.9.2] - 2025-12-11
### Changed
- Update to core 1.9.2.

## [1.9.1] - 2025-12-10
### Changed
- Update to core 1.9.1.

## [1.9.0] - 2025-12-09
### Added
- GroupByWidget: Group results by rules or requirements.
- ParametersWidget: Enable parameters selection in UI.
### Changed
- Model-View separation: Refactored UI to separate models and views.
- SettingsWidget: Keep settings widget on top.
- Update to core 1.9.0.

## [1.8.0] - 2025-11-20
### Added
- Parameters widgets added.
### Changed
- When requirements are enabled: Replace tabs with a drop down list.

## [1.7.1] - 2025-11-11
### Changed
- Fix successful and not implemented issues computation using non hashable requirements.
- Update to core 1.7.1

## [1.7.0] - 2025-11-06
### Changed
- Updated to core 1.7.0

## [1.6.0] - 2025-10-20
### Added
- Validate Prim mode: A new UI to validate prims.
### Changed
- Validate URI mode: Allow selecting folders in the UI
- AssetWidget: Inject model in the constructor.
- Updated to core 1.6.0

## [1.5.0] - 2025-10-10
### Added
- Context menus: Add prim validation.

## [1.4.3] - 2025-10-01
### Fixed
- ProgressModel: Fix bug when progress does not start at 0%

## [1.4.2] - 2025-09-24
### Changed
- Updated to core 1.4.2

## [1.4.1] - 2025-09-19
### Fixed
- Fixes a bug that ignores the selection in the 'features' panel of the UI
### Changed
- Update to core 1.4.1

## [1.4.0] - 2025-09-15
### Changed
- CapabilitiesModel, CapabilitiesWidget: Refresh upon requirement registration.
- Update to core 1.4.0

## [1.3.1] - 2025-09-01
### Changed
- Update to core 1.3.1

## [1.3.0] - 2025-08-21
### Changed
- Update to core 1.3.0.

## [1.2.1] - 2025-08-19
### Changed
- Update to core 1.2.1

## [1.2.0] - 2025-08-18
### Changed
- Update to core 1.2.0

## [1.1.6] - 2025-08-07
### Changed
- Update to core 1.1.6

## [1.1.5] - 2025-08-04
### Changed
- Update to core 1.1.5

## [1.1.4] - 2025-07-30
### Changed
- Update to core 1.1.4

## [1.1.3] - 2025-07-29
### Changed
- Update to core 1.1.3

## [1.1.2] - 2025-07-29
### Changed
- Update to core 1.1.2

## [1.1.1] - 2025-07-28
### Changed
- Update to core 1.1.1

## [1.1.0] - 2025-07-23
### Added
- Features Tab: An additional class to Requirements, Capabilities and Profiles
### Changed
- Update License to Apache 2
- Update to core 1.1.0

## [1.0.0] - 2025-07-16
### Changed
- OAV used in production should be marked as 1.0.0.
- Update to core 1.0.0

## [0.31.0] - 2025-07-15
### Fixed
- Update to core 0.31.0

## [0.30.1] - 2025-07-14
### Fixed
- Update to core 0.30.1

## [0.30.0] - 2025-07-10
### Fixed
- Update to core 0.30.0

## [0.29.1] - 2025-07-03
### Fixed
- Update to core 0.29.1.

## [0.29.0] - 2025-06-30
### Fixed
- Show when a requirement is not implemented.
- Fix filtering of succesful issues.
- Update to core 0.29.0.

## [0.28.1] - 2025-06-19
### Fixed
- Update to core 0.28.1.

## [0.28.0] - 2025-06-18
## Fixed
- Extension failed to refresh Window menu
### Added
- Support for Kit 108

## [0.27.1] - 2025-05-30
### Fixed
- Update to core 0.27.1.
- UI: Add link to documentation.

## [0.27.0] - 2025-05-27
### Fixed
- Update to core 0.27.0.
- UI: Improve performance.

## [0.26.0] - 2025-05-27
### Fixed
- Update to core 0.26.0.

## [0.25.3] - 2025-05-13
### Fixed
- Update to core 0.25.3.
- Fix categories not refreshing when rules are added/removed.

## [0.25.2] - 2025-05-09
### Fixed
- Update to core 0.25.2.

## [0.25.1] - 2025-05-07
### Fixed
- Update to core 0.25.1.
- Hide capabilities and profiles by default.

## [0.25.0] - 2025-05-06
### Fixed
- Update to core 0.25.0.
- Show capabilities and profiles by default.
- Window: Load lazily.
- Filters: Filter issues by tags.
- Filters: Show issues by issue severity, including Success.
- Profile view: Allow selection of incomplete capabilities.
- Profile view: Group issues by requirement.
- Widgets: Add add_registry_rule_callback to embedded widgets.

## [0.24.1] - 2025-05-02
### Fixed
- Update to core 0.24.1.

## [0.24.0] - 2025-04-29
### Fixed
- Update to core 0.24.0.
- Extensions could not add/remove rules and categories from UI upon startup/shutdown.

## [0.23.1] - 2025-04-22
### Fixed
- Update to core 0.23.1
- Fixed Report UI
- Added setting to control experimental capabilities features

## [0.22.1] - 2025-04-13
### Fixed
- Update to core 0.22.1.

## [0.22.0] - 2025-04-11
### Added
- Add Capabilities to User Interface.
- Search field to filter issues.
- Filter menu to filter issues.
- Updated documentation.
### Fixed
- Update to core 0.22.0.

## [0.21.0] - 2025-04-01
### Fixed
- Handlers are changed to carbonite subscriptions.
- Update to core 0.21.0.

## [0.20.0] - 2025-03-18
### Added
- Expose Asset Validator as widget.
- Add Commands Widget.
- Add Tabs Widget.
### Fixed
- Update to core 0.20.0

## [0.19.0] - 2025-03-11
### Fixed
- Update to core 0.18.4
- StageModel: Object has no attribute `__stage`

## [0.18.3] - 2025-02-27
### Fixed
- Update to core 0.18.3
- Fix context menu registration for stage window for kit 107

## [0.18.2] - 2025-02-17
### Fixed
- Update to core 0.18.2

## [0.18.1] - 2025-01-30
### Fixed
- Update to core 0.18.1

## [0.18.0] - 2025-01-28
### Fixed
- Update to core 0.18.0

## [0.17.0] - 2025-01-08
### Fixed
- Update to core 0.17.0
- Update menu implementation to avoid warnings.
- `Copy Selected Issues` produces the same CSV format as `Save Selected Issues` command.

## [0.16.2] - 2024-12-11
### Fixed
- Update to core 0.16.2

## [0.16.1] - 2024-12-10
### Fixed
- Update to core 0.16.1

## [0.16.0] - 2024-12-03
### Fixed
- Update to core 0.16.0

## [0.15.0] - 2024-11-20
### Fixed
- Update to core 0.15.0

## [0.14.2] - 2024-10-17
### Fixed
- Update to core 0.14.2
- USD Composer Missing Asset Validator When Right-Clicking Stage Panel

## [0.14.1] - 2024-10-16
### Fixed
- Update to core 0.14.1

## [0.14.0] - 2024-10-15
### Fixed
- Update to core 0.14.0

## [0.13.3] - 2024-09-10
### Fixed
- Update to core 0.13.3.
- Run-time error when pressing "Select in stage" button.

## [0.13.2] - 2024-08-29
### Fixed
- Update to core 0.13.2

## [0.13.1] - 2024-08-20
### Fixed
- Update to core 0.13.1

## [0.13.0] - 2024-08-15
### Fixed
- Update to core 0.13.0

## [0.12.0] - 2024-08-02
### Fixed
- Update to core 0.12.0

## [0.11.8] - 2024-07-23
### Fixed
- Update to core 0.11.8.

## [0.11.7] - 2024-07-17
### Fixed
- Update to core 0.11.7.

## [0.11.6] - 2024-07-08
### Fixed
- Remove `attrs` python dependency

## [0.11.5] - 2024-05-29
### Fixed
- Center align button icon and text.
- Gather all settings into the upper right panel.
- Update documentation to reflect latest changes.

## [0.11.4] - 2024-05-13
### Fixed
- Selecting a property in stage should use the Prim path.
- Updated the style of Suggestion widgets as a Button.

## [0.11.3] - 2024-04-24
### Fixed
- ReportSection: Display `No issues found` when no errors.

## [0.11.1] - 2024-04-09
### Fixed
- Update to core 0.11.1.
- ReportSection: Asyncio error when validating folders after fixing.

## [0.11.0] - 2024-02-27
### Added
- Variants: Option to enable/disable checking all variants.
### Fixed
- Update to core 0.11.0.
- "Authoring Layer has been changed" toast fixed (i.e. no longer appearing).
- No side effect rendering when validating.
- No side effect UI when validating.

## [0.10.3] - 2024-02-15
### Fixed
- UI error when applying fixes on URI mode.
- Improve UI to make it clear to the user there is currently no fix available.

## [0.10.2] - 2024-01-30
### Fixed
- Update to core 0.10.2.
- UI implementation of progress indicator.
- Asset validator error when validating via URL mode, with unauthorized files.

## [0.10.1] - 2023-12-15
### Fixed
- Update to core 0.10.1.

## [0.10.0] - 2023-12-14
### Fixed
- Update to core 0.10.0.

## [0.9.5] - 2023-12-05
### Fixed
- Update to core 0.9.5.

## [0.9.4] - 2023-12-04
### Fixed
- Update to core 0.9.4.

## [0.9.3] - 2023-11-22
### Fixed
- Update to core 0.9.3.

## [0.9.2] - 2023-11-14
### Fixed
- Update to core 0.9.2.

## [0.9.1] - 2023-11-01
### Fixed
- Update to core 0.9.1.

## [0.9.0] - 2023-10-12
### Fixed
- Update to core 0.9.0.

## [0.8.1] - 2023-08-18
### Fixed
- Improve of UI flow
  - One click to fix a single issue.
  - Move Fix and Save selected to an option.
  - Update documentation.

## [0.8.0] - 2023-08-08
### Fixed
- Update to core 0.8.0.

## [0.7.6] - 2023-08-02
### Fixed
- Update Kit SDK.

## [0.7.5] - 2023-08-02
### Fixed
- Publishing process.

## [0.7.1] - 2023-08-01
### Fixed
- PrimEncapsulationChecker, NormalMapTextureChecker: Ability to select prims.
- When a fix is propossed do not select prims.

## [0.7.0] - 2023-07-13
### Fixed
- DefaultPrimChecker: Suggestion has been removed for now (we need support for active / de-active prims in Kit first).
- All Validators besides the Schema validators have been disabled by default.
- Explicit Saving of Fixes: Applying has been separated into two buttons. One that fixes the issues in memory only, the other that fixes them and save their edit targets.

## [0.6.2] - 2023-06-20
### Fixed
- Update to core 0.6.2
- Update the documentation images. Some images did not reflect the status of the new UI.

## [0.6.1] - 2023-05-25
### Fixed
- Update to core 0.6.1
- Change the order of categories: `Usd:Schema` is first.

## [0.6.0] - 2023-05-19
### Added
- A new UI
### Fixed
- Update to core 0.6.0
- Change location in UI: `Stage` -> `Layer <>` and `Root Layer` -> `Layer <>`

## [0.5.1] - 2023-05-10
### Fixed
- Fixing publishing of extension.

## [0.5.0] - 2023-05-10
### Fixed
- Opening non-empty stage warns about no stage selected.
- Update to core 0.5.0
- Update documentation to reflect latest changes.
- Update to Kit 105

## [0.4.0] - 2023-04-27
### Added
- Auto fixing, adding the ability to fix a specific layer via drop down.
### Fixed
- Update to core 0.4.0

## [0.3.3] - 2023-03-28
### Added
- Enable pyCoverage.
### Fixed
- Added missing documentation for Copy, Dry Run and Fix actions.
- Redesign Asset Mode Widget and validate correct selection.
- Add dependency exact=true, remove option from menu when UI is disabled.

## [0.3.2] - 2023-03-09
### Fixed
- Update to 0.3.2

## [0.3.1] - 2023-03-07
### Fixed
- Update to 0.3.1

## [0.3.0] - 2023-02-07
### Fixed
- Update to 0.3.0

## [0.2.4] - 2023-01-31
### Fixed
- Update to 0.2.4

## [0.2.3] - 2023-01-26
### Fixed
- Asset Validator re-runs even disabled rules after user asks to fix issues.
- Update to 0.2.3.

## [0.2.2] - 2023-01-23
### Fixed
- Update to 0.2.2.

## [0.2.1] - 2022-11-21
### Fixed
- Correct reference to core component.

## [0.2.0] - 2022-10-28
### Added
- Improved Report UI
  - New tree interface allows collapsing, selecting, & copying individual (or several) Assets & Issues
  - Suggestions can be applied interactively via Dryrun & Fix buttons
    - This applies only to a limited set of Issues that report suggestions
    - Dry-run will apply the changes in-application without saving, while the Fix button will attempt to save the changes to the relevant layer
    - Note this is experimental, the logic for locating the best layer and saving is not yet solidified.

## [0.1.2] - 2022-09-15
### Fixed
- Fixed stage-level rule failures when validating in-memory layers from the Layers Window

## [0.1.1] - 2022-09-14
### Fixed
- Updated extension registry details and documentation.

## [0.1.0] - 2022-09-13
### Added
- _Asset Validator Window_ for initiating validation runs on individual USD layer files, recursively searching an OV folder for layer files and validating them all, or validating a live / in-memory `Usd.Stage`, such as the main stage in OV Create or other USD based applications.
- _Content Browser_ context menus to launch the _Asset Validator Window_ preset to the selected file/folder.
- _Layer Window_ context menus to launch the _Asset Validator Window_ preset to either the in-memory layer or the selected layer's file URI.
- _Stage Window_ context menus to launch the _Asset Validator Window_ preset to the currently open stage (e.g the main stage of the application).

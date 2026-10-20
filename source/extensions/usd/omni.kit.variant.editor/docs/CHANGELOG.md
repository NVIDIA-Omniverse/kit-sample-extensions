# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [107.5.13] - 2026-09-11
### Fixed
- OMPE-89478: test_variant_content waited a fixed delay for the reference/payload rows, so `find_all` could run before the tree rebuilt and see one row instead of two; it now waits for the expected count
- test_variant_content drove the asset picker without waiting for it to open, which silently picked nothing and left the arc unauthored

## [107.5.12] - 2026-09-08
### Fixed
- OMPE-105547: Guard against `get_layers()` returning None so opening a stage no longer raises AttributeError
- Guard the same unresolved-interface case in the reference/payload widget and the property model's spec-lock subscription
- Clear `_layer_event_sub` before resolving the Layers interface so a stale subscription is never left in place

### Changed
- Resolve the Layers context via `omni.usd.get_context_from_stage()` instead of the cached context, so layer events keep working even if `omni.usd.get_context` is replaced at the Python level (OMPE-105547)

## [107.5.11] - 2026-08-25
### Fixed
- StageWindowButton, PropertySelectorButton and RootSelector leaked a ui.Window per click, making
  lookups by window title ambiguous; each now tracks its live owner weakly and has it tear the window down
- PropertySelectionListView.bind_to de-duplicates observers and gains a matching unbind_from
- Re-query stale WidgetRefs after UI rebuilds in the UI tests, fixing flaky test_variant_content

## [107.5.10] - 2026-04-13
### Fixed
- OMPE-89478: Fixes for test failures when run in random order

## [107.5.9] - 2026-02-26
### Fixed
- OMPE-81467: test_commands.TestCommands.test_commands_usdlux_2505 should not run when Kit SDK version is < 109 because UsdLux 25.05 is not supported

## [107.5.8] - 2025-02-10
### Fixed
- OMPE-80785: Fix method for retrieving inputs from shader nodes

## [107.5.7] - 2025-12-12
### Added
- OMPE-43404: Run omni.kit.variant.editor.tests.test_commands.TestCommands both with legacy and UsdLux-compliant lights

## [107.5.6] - 2025-09-22
### Fixed
- OMPE-64616: Fixed  ui.Menu & ui.Separator to use menu_compatibility=False

## [107.5.5] - 2025-09-15
### Fixed
- Use correct golden image for 'test_variant_content' test when testing redoing prim removal

## [107.5.4] - 2025-09-05
### Fixed
- OMPE-59943: Removing prim from variant now clears metadata using root-relative paths to prevent prim card repopulation when reselecting a variant.
- Fixed typo in 'HasAuthroedVariant' invocation in commands.py

## [107.5.3] - 2025-08-28
### Fixed
- OMPE-61024: Fixed errors when clicking variants authored in non-current layers

## [107.5.2] - 2025-08-28
### Fixed
- OMPE-57990: Added backwards compatibility for timeline events 1.0

## [107.5.1] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [107.5.0] - 2025-08-22
### Changed
- OMPE-57990: Update to use Events 2.0

## [107.4.1]
Bump patch version to re-publish after the move to kit-sample-extensions repo

## [107.4.0] - 2025-06-12
### Added
- Added support for UTF-8 characters in variant names

## [107.3.0] - 2025-05-19
### Fixed
- Improve tests to avoid using golden images but instead use the UI query to verify the state of the editor

## [107.0.5] - 2025-05-16
### Fixed
- Update ndr_sdr_type_indicator to use GetSdfType() for compatibility with USD 25.02.

## [107.0.4] - 2025-04-28
- Automatically add `info:mdl:sourceAsset:subIdentifier` property to UI when `info:mdl:sourceAsset` is added

## [107.0.3] - 2025-04-24
- Updated repo_package to 6.0.0.

## [107.0.2] - 2025-04-24
### Fixed
- Added delay when retrieving Sdf.AttributeSpec for _test_shader_widget_source_asset
### Changed
- Updated repo tools

## [107.0.1] - 2025-04-16
### Fixed
- Add shader input properties to 'Select Properties' dialog

## [107.0.0] - 2023-11-26
### Changed
- Upgrade to Kit SDK 107 with USD 24.05 and python 3.11

## [106.1.1] - 2024-09-25
### Changed
- Disabled tooltips during UI tests

## [106.1.0] - 2024-08-16
### Changed
- Updated repo tools
- Updated SDK
- Fixes for a few golden image tests

## [106.0.3] - 2024-06-14
### Changed
- Stage updates no longer cause Variant Sets to expand
- Variants inside of reference layers can no longer be modified from the editor
- Updated UI so it is apparent when variants cannot be edited
- Fixed dependency issue
- Added unit test to ensure variants inside reference layers are correctly uneditable

## [106.0.2] - 2024-05-23
### Changed
- Reformat all source with repo format.

### [106.0.1] - 2024-05-17
### Fixed
- usd_prop_metadata was being referenced without necessarily being defined

## [105.1.44] - 2024-05-07
### Changed
- Reformat all source with repo format.

### [106.0.0] - 2024-04-10
### Changed
- Updated SDK

### Fixed
- Updated golden images

### [105.1.44] - 2024-03-11
### Changed
- Made the "clear local opinion" button clear only values instead of removing the def

### [105.1.43] - 2024-03-07
### Fixed
- Added copy/paste functionality to variant editor

### [105.1.42] - 2024-03-07
### Fixed
- Fixed a flaky payload/reference test

### Added
- Added preview.png for extension manager

### [105.1.41] - 2024-03-04
### Fixed
- Fixed `SdfAssetPathAttributeModelVariant` improper construction

### [105.1.40] - 2024-02-09
### Fixed
- Fixed a bug that relationships in a variant are not corectly displayed.

### [105.1.39] - 2024-02-03
### Added
- OMPRW-353 - Display read only variant content when the variant is authored in a remote layer.

### [105.1.38] - 2024-02-02
### Added
- OMPRW-347 - "Add Properties To All Prims" button added to property selection dialogue

### [105.1.37] - 2024-02-01
### Added
- OMPRW-466 - Add some test cases for payload/reference widgets

### [105.1.36] - 2024-01-30
### Changed
- "Add Properties to All Variants" option changed to "Add Prims/Properties to All Variants"

### Added
- Added empty prim cards to variantSpec customData so they can persist between refreshes

### [105.1.35] - 2024-01-24
### Fixed
- OM-119129 - Fixed a bug that sometimes a prim can't be removed from a variant.

### [105.1.34] - 2024-01-23
### Fixed
- OMPRW-435 - raise code coverage

### [105.1.33] - 2024-01-23
### Fixed
- OMPRW-685 - clear properties filter in new search

### [105.1.32] - 2024-01-22
### Fixed
- OM-118648 - Relationship doesn't displayed correctly

### [105.1.31] - 2024-01-18
### Changed
- OMPRW-517 - Highlights selected active variant set.

### [105.1.29] - 2024-01-15
### Fixed
- OMPRW-547 - Reference/Payload widget adds menu item in the usd property PrimPathWidget add button

### [105.1.28] - 2024-01-10
### Fixed
- OMPRW-438 - Reference/Payload widget implementation like the usd property page

### [105.1.27] - 2024-01-02
### Added
- Hotkey to duplicate variant and rename variant
-
### [105.1.26] - 2024-01-02
### Fixed
- OM-114490 - use EditVariant to ensure undo step recording of property's display name setting correct

### [105.1.25] - 2023-12-19
### Fixed
- OM-114490 - support colorspace of Shader attributes

### [105.1.24] - 2023-12-13
### Fixed
- OM-114474 - Refreshes UI for undo and redo.

### [105.1.23] - 2023-12-12
### Fixed
- OM-115393 - Fixed dragging multiple prims to property panel

### [105.1.21] - 2023-12-11
### Fixed
- OM-116905 - disable undo step recording during editing

### [105.1.20] - 2023-12-06
### Changed
- OM-92919 - create derived class of UsdBindingAttributeWidget for consistency of material binding editing

### [105.1.19] - 2023-11-30
### Fixed
- OM-115635: Fixed ETM failure of 105.1.

### [105.1.18] - 2023-11-24
### Fixed
- OM-102181: Uses commands to do authoring with undo.

### [105.1.17] - 2023-11-23
### Changed
- OM-114476: share the same logic with kit's property widget builder

### [105.1.16] - 2023-11-23
### Fixed
- OM-113459: display renaming invalid input warning bubble only if it's meaningful

### [105.1.15] - 2023-11-22
### Fixed
- OM-114160: when "Add Property to All Variants" is on, adding property does not refresh all variants' UI

### [105.1.14] - 2023-11-22
### Fixed
- OM-101603: Variant Set Card and Prim Card not collapsable

### [105.1.13] - 2023-11-17
### Fixed
- OM-110039: fix error log when creating VariantSet from file

### [105.1.12] - 2023-11-08
### Changed
- OM-98009: filter prim picker's scene tree with target prim path

### [105.1.11] - 2023-11-07
### Fixed
- OM-109471: use type's default value when property spec doesn't exist

### [105.1.10] - 2023-11-06
### Fixed
- OM-106810: fix visibility of properties is inconsistent in Select Properties list

### [105.1.9] - 2023-10-31
### Fixed
- OM-106810: fix visibility of properties is inconsistent in Select Properties list

### [105.1.8] - 2023-10-17
### Fixed
- UI string/token/path properties do not return VariantLabel and cause error

### [105.1.7] - 2023-10-11
### Fixed
- UI PropertyWatchButton does not reflect local opinion or not correctly

### [105.1.6] - 2023-10-11
### Fixed
- UI not refresh when setting default on variant property( for example float type)

### [105.1.5] - 2023-09-27
### Fixed
- UI not showing variant property when first and payload variant is added

### [105.1.4] - 2023-09-21
### Fixed
- Kit frozen when selecting multiple target prim
- Warning log from the variant context menu in the viewport
-
### [105.1.3] - 2023-09-11

### Fixed
- Fixed some variant properties not actually setting a default value when created
### [105.1.2] - 2023-09-08

### Fixed
- OM-98804: Only create variant set on usd and mdl files in Content browser

### [105.1.1] - 2023-08-29

### Fixed
- Fixed a rare crash when using drag and drop with payloads

### [105.1.0] - 2023-08-04

### Added
- Variants can now be selected from the Stage Context Menu
- Added Prim Card Context Menu item to select the Prim in the Stage
- Added a search filter to property picker
- Added options menu
- Added new option to propagate newly created properties into all variants within a given set
- Added new option to toggle whether usd assets dropped into variant editor should create visibility or payload/reference variants

### Changed
- Changed "Add" text to "Select" when selecting Target Prim
- "Add Variant" button now duplicates the bottom variant if one exists
- Dropping assets from the content browser into the variant set area now creates visibility variants by default instead of payload/reference variants

### Fixed
- Renaming variants now properly checks to see if a given variant name is available
- "Variant Set Prim Location" string field now properly checks for manual string changes

### [105.0.4] - 2023-06-12

### Fixed
- Fixed an issue where prim cards could not be added to variants

### [105.0.3] - 2023-06-05

### Added
- Newly added prim cards are briefly highlighted
### Fixed
- Prim cards now sort alphabetically


### [105.0.2] - 2023-05-02

### Added
- Added notifications when handling variants in non-authored layers
### Fixed
- Incorrect variant selection highlighting after switching authoring layer


### [105.0.1] - 2023-04-28
### Changed
- Updated Preview Image

### Fixed
- Editor no longer closes when changing stages
- Creating a variant set only automatically creates a variant when using the "Add New Variant Set" button
- Property widget not updating value when property is variant selection
- Property widget refrehsing issue after renaming variant or variant set

### Added
- Added guide text to the editor


### [105.0.0] - 2023-04-26
### Added
- Initial version

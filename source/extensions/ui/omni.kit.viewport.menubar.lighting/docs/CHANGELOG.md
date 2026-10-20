# CHANGELOG

This document records all notable changes to ``omni.kit.viewport.menubar.lighting`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [107.3.5] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: use USD query fallbacks and ignore the runtime fallback light.

## [107.3.4] - 2026-08-12
### Fixed
- OMPE-91882: Always initialize `MenuContext.__light_added_cb`, so `destroy()` cannot raise `AttributeError`.
- OMPE-91882: Do not build or query the menu of a Viewport that is gone, so a torn-down Viewport cannot
  raise `AttributeError` in `build_fn` or `KeyError` in the expand/contract queries.

## [107.3.3] - 2026-07-09
### Fixed
- OMPE-99588: Fixed viewport not updating after switching rigs to Stage Lights, incl. session-re-activated lights.

## [107.3.2] - 2025-11-07
### Changed
- Fix typo error in menu_container.py.

## [107.3.1] - 2025-08-07
### Changed
-

## [107.3.0] - 2025-04-30
### Changed
- Update to EventDispatcher-2

## [107.0.3] - 2025-04-11
### Changed
- Update light rigs to be use modern UsdLux input prefixes

## [107.0.2] - 2025-03-21
### Changed
- OMPE-40959: Update Support Level from Enterprise to Core

## [107.0.1] - 2025-02-11
### Changed
- target kit 107.0 with abi=1

## [107.0.0] - 2024-11-20
### Changes
- Update to Kit-107 with OpenUsd-24.05

## [106.0.2] - 2024-04-29
### Changes
- Make default dome-light hidden for primary rays.

## [106.0.1] - 2024-04-18
### Fixed
- Added Enterprise tag

## [106.0.0] - 2024-04-11
### Fixed
- Issue with "Stage" menu-item not staying selected (introduced in 105.0.9)

## [105.0.9] - 2023-12-29
### Added
- unique identifiers present for the Lights menu options in Viewport
- name property for stage lights in light menu

## [105.0.8] - 2023-10-24
### Added
- Setting to allow light rig to be applied to default UsdContext and Viewport whether menu item is loaded or not
### Fixed
- Make sure to clear any previous rig/scene up correction applied if new rig does not need a correction.

## [105.0.7] - 2023-10-04
### Changed
- Added setting to control root-location light rig is imported into

## [105.0.6] - 2023-08-22
### Changed
- Handle stage-up axis in case insensitive way

## [105.0.5] - 2023-05-30
### Changed
- Clear Sdf.References from Usd.Prim outside of the Sdf.ChangeBlock for UsdRt.
- Honor hide_in_stage_window metadata for Usd.Prim traversal with UsdRt.
### Added
- Setting to control traversal over Usd.Prim with hide_in_stage_window meta-data.

## [105.0.4] - 2023-05-12
### Changed
- Remove sphere from Grey Studio light rig.

## [105.0.3] - 2023-05-03
### Changed
- Use MaterialBindingAPI for Grey Studio light rig.

## [105.0.2] - 2023-04-28
### Changed
- Store rig applied in setting keyed on stage-id so re-application of current rig can be elided.
### Fixed
- Workaround issue in UsdRt possibly returning paths to invalid prims on the stage.
### Added
- Additional tests.

## [105.0.1] - 2023-03-23
### Changed
- Update ambient light test for changes to RTX render-setting no longer being applied without RTX loaded.

## [105.0.0] - 2023-03-14
### Changed
- Update to and lock extension to USD-22.11.
### Added
- Test suite running against UsdRT

## [104.0.11] - 2023-02-23
### Added
- Better performance for prim type queries when UsdRt is available.
### Fixed
- Performance issue when transitioning to same lighting mode on large scenes.

## [104.0.10] - 2023-02-17
### Changed
- OM-82556: Added super().__init__() calls to init overrides for Py 3.10.

## [104.0.9] - 2022-12-19
### Changed
- Make lighting rig a non-pickable object.

## [104.0.8] - 2022-11-29
### Added
- Switch to stage lighting when CreatePrimWithDefaultXform command is run with a light-type.

## [104.0.7] - 2022-11-16
### Added
- Switch to stage lighting when CreatePrim command is run with a light-type.

## [104.0.6] - 2022-10-31
### Changed
- Added stage load activity.

## [104.0.5] - 2022-10-28
### Fixed
- Setting key typo for golden image tests on 105

## [104.0.4] - 2022-10-20
### Added
- Setting and menu item to disable the feature.
- Command to make the enabling of the lighintg rig undoable.
- Setting to control whether to look for lights at defaultPrim or absolute-root.
### Changed
- Various UI labels.
- Make application of light rig part of the undo-stack.
- Only pop-up render settings change info when the setting has definitely been changed.

## [104.0.3] - 2022-10-17
### Fixed
- Issue with instanced lights picked up in mesh test from omni.kit.viewport.action implementation synch.

## [104.0.2] - 2022-10-13
### Added
- Ability to turn on/off Viewport sprites when switching to and away from light-rig.
- Create From Light Rig menu entry to import current light.
### Changed
- Only switch to default lighting rig when loading usd from disk that has no lights.
### Fixed
- Set light-rig prim to no delete.

## [104.0.1] - 2022-10-05
### Added
- Automatic lighting rig selection on stage open without any lights.
- Modes to adjust RTX ambient setting on stage open.
### Changed
- Add "Camera Light" mode into drop down menu.
### Removed
- Flash light toggle-button.

## [104.0.0] - 2022-09-28
### Added
- Initial version.

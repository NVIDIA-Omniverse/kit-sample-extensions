# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.7] - 2026-10-16
### Fixed
- Kit 111: the `stage:opened` handler (`extension.py`), `prepopulate_viewport_items` (`model.py`) and the OmniGraph event
  node lookup (`properties/prim_property_widget.py`) read the authored USD stage instead of `UsdRt.Stage.Attach(...)` and
  `GetPrimsWithTypeName`. On Kit 111 Runtime Core publishes the usdrt stage only after population, so `Attach` returned
  `None` at `stage:opened` and the published 1.1.4 raised `'NoneType' object has no attribute 'GetPrimsWithTypeName'`.
  (Code changes 3a7943393 and d5f550be6, 1 Oct; this version publishes them.)
- Tests no longer pass `--/app/useFabricSceneDelegate=true` (with it, `omni.hydra.rtx` asks for the missing
  `omni.hydra.usdrt_delegate`).

## [1.1.6] - 2026-10-15
### Changed
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then `pump_apply_usd_changes failed (12)` and `PUMP apply_usd_changes ... failed`). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

## [1.1.5] - 2026-10-01
### Fixed:
- Handle graceful shutdown when authoring was not initialized and optional property extensions are not loaded.

## [1.1.4] - 2025-07-04
### Changed:
- Enaling ARM builds

## [1.1.3] - 2025-07-04
### Fixed:
- OMPE-53951 - Fixing the invalid syntax in docstring which breaks the tests in Kit App Template

## [1.1.2] - 2025-04-22
### Fixed:
- OMPE-44166 - Removing rendering backend completely, because it shouldn't be needed for these extensions.

## [1.1.1] - 2025-04-21
### Fixed:
- OMPE-44166 - Swapping renderer backend to RTX for OVC2 ETM support.

## [1.1.0] - 2025-01-06
### Fixed:
- OMPE-27667 - Code tweaks for the public API checking tool.

## [1.0.27] - 2024-08-27
### Fixed:
- OMPE-19960 - Fixing some test errors on release/106.1

## [1.0.26] - 2024-05-29
### Added:
- OMPE-7959:
  - Made some tweaks to the startup behavior to remove authoring features when not needed.
  - This also includes a new `omni.no_code_ui.authoring` bundle extension that re-enables authoring support.

## [1.0.25] - 2024-05-13
### Added:
- OMPE-3994: Sample level support.

## [1.0.24] - 2024-04-30
### Added:
- Fixing the logic around glyph detection. Should now gracefully fail instead of throwing errors.

## [1.0.23] - 2024-04-17
### Added:
- OM-123507: Adding support level information.

## [1.0.22] - 2024-03-06
### Added:
- OMPRW-27: Swapping `ViewportButton` to `ViewportCircle`, `ViewportButton` is now more of an actual button class, rectangular and can accept images.

## [1.0.21] - 2024-02-21
### Fixed:
- OMPRW-27: Hooks for proper mouse input when using the UsdSceneView backend.

## [1.0.20] - 2024-02-14
### Fixed:
- OMPRW-878: Fixing style updates
- OMPRW-880: Improved style lookups
- OMPRW-884: Improving gesture prevention. This should now only trigger gestures on the closest shape if they happen to overlap.
- OMPRW-882: Adjusting the border outline to start outside of the background shape.

## [1.0.19] - 2024-02-14
### Added:
- OMPRW-883: Fix for event dropdowns failing to find events.

## [1.0.18] - 2024-02-08
### Added:
- OMPRW-829: Fix for no code widgets failing to render.

## [1.0.17] - 2024-01-26
### Added:
- OMPRW-27: Adding update in place support for 3d Hotspot buttons.

## [1.0.16] - 2024-01-03
### Added:
- Fixing type issue in `CreateWindowUIFrame` command.

## [1.0.15] - 2023-08-28
### Added:
- OM-96422 - Fixing readback and application of style properties that use enumerations.

## [1.0.14] - 2023-08-25
### Added:
- OM-101043 - UI Commands header only shown for UI primitives.

## [1.0.13] - 2023-08-07
### Added:
- OM-104416 - Adding a 'ToggleNoCode' command to the context menu, this disables the property and hides the field

## [1.0.12] - 2023-08-03
### Added:
- Fixing a bug with the properties panel wiping out button events.

## [1.0.11] - 2023-08-02
### Added:
- OM-101704 - Being a bit less thorough, as it breaks the SIGGRAPH demo.

## [1.0.10] - 2023-08-02
### Added:
- OM-103276 - Ensure that existing properties aren't stomped on.

## [1.0.9] - 2023-07-31
### Added:
- OM-101704 - Properly cleaning up the viewport UI elements when creating a new stage.

## [1.0.8] - 2023-07-28
### Added:
- Exposing `ui.Widget.selected` property so that the selected style selector can be used through no-code-ui
- Ensuring that all valid properties are applied to ui-primitives.

## [1.0.7] - 2023-06-21
### Fixes:
- No longer shows nocode menu items in viewport context menu
- Stage context menu properly filtering menu items to only appear when nocode primitives are selected.

## [1.0.6] - 2023-06-21

### Fixes:
- Should no longer break context menu in stage or viewport.
- Should properly resolve relative asset paths.

## [1.0.5] - 2023-06-20

### Changed:
- Using `ui.ImageWithProvider` in place of `ui.Image`

### Fixes:
- Block UI widget from displaying when no prims are selected

## [1.0.4] - 2023-06-14

### Fixes:
- Disabling the read only properties until a more performant solution can be found.

## [1.0.3] - 2023-06-13

### Added:
- Adding two new commands ParentToViewportCommand and RemoveViewportPrim

## [1.0.2] - 2023-06-09

### Added:
- bundle test waiver

## [1.0.1] - 2023-06-09

###
- Fixed: failure to create UIPrims when a non-UIPrim was selected.

## [1.0.0] - 2023-06-07

### Added
- Scrolling and Collapsable Frame primitives.
- Read only properties for retrieving the position and size of widgets.

## [0.7.2] - 2023-06-06

### Fixes
- Remove debug print

## [0.7.1] - 2023-06-05

### Fixes
- Guard clause for widget classes not of the correct type

## [0.7.0] - 2023-06-02

### Features
- USD Prims and Attribs now follow USD team prim/attribute naming conventions. (OmniUI{widget} + omni:ui:{widget}:{prop})

## [0.6.4] - 2023-05-19

### Fixes
- fn event lambdas pass the originating prim path properly

## [0.6.3] - 2023-05-17

### Fixes
- Make stage open/close destroy existing views/frames/windows

## [0.6.2] - 2023-05-12

### Fixes
- copyrights and docs updated for publish

## [0.6.1] - 2023-05-09

### Fixes
- tests for core
- small app and test settings adjustments
- address typo in core subscription method

## [0.6.0] - 2023-05-05

### Features
- implement tests
- rename codeless_ui to no_code_ui for bundle

### Fixes
- minor consistency fixes to enum variable naming

## [0.5.2] - 2023-04-27

### Fixes
- fix AssetPath handling in properties and styles

## [0.5.1] - 2023-04-26

### Fixes
- retention of picked event with proper reflection to model

## [0.5.0] - 2023-04-26

### Features
- asset Property Type support
- both prim and style url-properties are now Assets

## [0.4.0] - 2023-04-26

### Features
- re-enable reorder prim commands

## [0.3.0] - 2023-04-26

### Features
- re-enable content-clipping on Stack to allow user solve for stage click-through
- add circle, line, triangle to core and usd
- add codeless_ui bundle extension
- express state selector as tokens

### Fixes
- fix event prefix
- fix Add button in widget namespace
- fix Add menu appearing
- replace lightning icon with frame
- update search label color
- remove accidentally added snippet
- API name standardize

## [0.2.0] - 2023-04-24

### Features
- MVP implementation for user testing

## [0.1.0] - 2023-02-16

### Added
- Initial creation

# CHANGELOG

This document records all notable changes to ``omni.kit.tool.teleport`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [107.4.2] - 2026-10-15
### Fixed
- Kit 111: the teleport target follows the surface under the cursor again, through the viewport pick query (`request_query`) instead of the removed world-ray query; no dependency on omni.kit.raycast.query.

## [107.4.1] - 2026-09-14
### Fixed
- OMPE-106295: Scale the USD-prim widget gizmo (ring, denyring, mesh and pointer), its raycast lift-off offset and the post-teleport beam nudge by the stage metersPerUnit, so the non-ring-manipulator path (`ringManipulatorVisible=false`) also renders at the same physical size on stages not authored in centimeters
- OMPE-106295: Apply the widgetScale/units world scale to the deny ring, which previously received no scale at all
### Changed
- `TeleportWidget` reads the shared `TeleportModel.units_scale` (passed in at construction) instead of ignoring stage units; the metersPerUnit tracking removed from the widget in 107.4.0 stays centralized on the model
### Added
- Tests that the widget world scale and raycast offset are invariant across stage metersPerUnit

## [107.4.0] - 2026-08-11
### Fixed
- OMPE-12345: Scale the teleport gizmo, beam and position labels by the stage metersPerUnit so they render at the same physical size on stages not authored in centimeters (e.g. metersPerUnit=1.0, where the gizmo was pinned to ringManipulatorMaxSize at every camera distance)
### Changed
- Moved the stage units callback from `TeleportWidget` to `TeleportModel`, which exposes the shared `units_scale` now used for both the gizmo geometry and the eyeHeight conversion
### Added
- Test that the gizmo probe, beam arc bulge and label offset are invariant across stage metersPerUnit

## [107.3.5] - 2026-08-14
### Added
- OMPE-74317: Optional useWorldUp setting to keep teleport level and usable over surfaces with normals far from world up (e.g. point clouds)

## [107.3.4] - 2026-07-02
### Fixed
- OMPE-99144: Convert eyeHeight setting (centimeters) to stage units so teleport keeps the camera at eye height on stages not authored in centimeters (e.g. metersPerUnit=1.0)
### Added
- Test that teleport eye height scales with stage metersPerUnit

## [107.3.3] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [107.3.2] - 2025-10-01
### Fixed
- Uninitialized attribute usage

## [107.3.1] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [107.3.0] - 2025-06-13
### Changed
- OMPE-42900: Update teleport tool to events 2.0.

## [107.0.3] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [107.0.2] - 2025-03-06
### Added
- Update public api

## [107.0.1] - 2025-02-19
## Changed
- Replace `omni.kit.window.viewport` with `omni.kit.viewport.window` in test dependencies

## [107.0.0] - 2024-11-28
- OMPE-27978: Update kit sdk to 107.

## [106.1.0] - 2024-08-09
- OMPE-17503: Fix ETM failure for omni.kit.tool.teleport on release/106.1

## [104.2.15] - 2023-12-01
- OMFP-4011: Fix teleport gizmo disapearing when teleporting with section tool enabled

## [104.2.14] - 2023-11-28
- OMFP-3552: State management fixes

## [104.2.13] - 2023-11-28
- OM-106459: Fix ETM failure for omni.kit.tool.teleport on Kit 105.2

## [104.2.12] - 2023-11-16
- OMFP-3875: Make teleport tool aware of section plane

## [104.2.11] - 2023-11-06
- Unit Test Update

## [104.2.10] - 2023-11-03
- OMFP-3549: Reverted temporary fixes to prevent the flickering, due to `ui.scene` updates.
- Added a minimum and maximum size in screen space pixels for the Gizmo.
- Fixed Gizmo disappearing after manipulating the camera.
- Fixed a bug where the Gizmo got stuck when no geometry was underneath the mouse cursor.

## [104.2.9] - 2023-11-02
- OMFP-3549: Temporary improvement to the issue where the teleport puck could cover the full screen after a teleport.
- Added a maximum size for the puck
- Fixed an issue where the puck would stay hidden after a double click or drag action.

## [104.2.8] - 2023-10-31
- OM-106459: Fix test failed in linux with kit 105.2.

## [104.2.7] - 2023-10-26
- Fixed "Show Beam" toggle to update teleport manipulator appearance when toggled

## [104.2.6] - 2023-10-26
- Test Coverage

## [104.2.5] - 2023-10-24
- Test Coverage

## [104.2.4] - 2023-10-23
- small fix for OMFP-3080 set_direction_and_up(...)

## [104.2.3] - 2023-10-23
- OMFP-3081: Change teleport defaults, OMFP-3080: Teleport happens even if not supposed to with Gizmo Teleport

## [104.2.2] - 2023-10-20
- OMFP-2933: use grab cursor in camera lookup state.

## [104.2.1] - 2023-10-20
- OMFP-2890: Revert teleport cursor to default. At this time we don't have all states to remove it completely without causing it missing entirely when overlapping some viewport menus.

## [104.2.0] - 2023-10-19
- Added option to use `ui.scene` manipulator instead of the USD prim for the puck.

## [104.1.12] - 2023-10-19
- OMFP-604 Set Teleport cursor shape when it is active

## [104.1.11] - 2023-10-19
- Fixed Teleport test failure.

## [104.1.10] - 2023-10-18
- Renamed PreferencePage from Teleport to Navigation.

## [104.1.9] - 2023-10-17
- Hide teleport tool prims in stage

## [104.1.8] - 2023-10-13
- Updated teleport puck to load faster.

## [104.1.7] - 2023-10-13
- OMFP-2482 - Replace teleport USD

## [104.1.6] - 2023-10-13
- Test Coverage

## [104.1.5] - 2023-10-12
- Version bump.

## [104.1.4] - 2023-10-10
- Restored the behavior to be able to teleport on ground plane when no mesh is hit.

## [104.1.3] - 2023-10-10
- Changelog reformatting

## [104.1.2] - 2023-10-10
- OMFP-2201 - Teleport to not affect camera orientation

## [104.1.1] - 2023-10-10
- Changed how Welcome window visibility is detected.

## [104.1.0] - 2023-10-10
- Removed `omni.kit.mesh.raycast` usage. Used usdrt for widget update.

## [104.0.42] - 2023-10-10
- OMFP-1939: Get omni.kit.tool.teleport passing ETM + FSD

## [104.0.41] - 2023-10-09
- OMFP-2203 Teleport state during RMB hold (for AWSD fly mode)

## [104.0.40] - 2023-10-06
- Fixed slope angle calculation.

## [104.0.39] - 2023-10-05
- Disabling some of the tests until we get this repo publishing again.

## [104.0.38] - 2023-10-04
-  OMFP-728 Can't immediately teleport after previous teleport

## [104.0.37] - 2023-10-04
-  OMFP-617 Teleport - Should not be allowed for some surfaces
-  OMFP-618 Teleport - Puck art update
-  OMFP-1016 teleport arc hotkey

## [104.0.36] - 2023-10-04
- OMFP-650 - Puck should hide when welcome window is visible.

## [104.0.36] - 2023-10-03
- OMFP-620 - Making the arc toggleable, it is now part of the teleport settings.

## [104.0.35] - 2023-09-29
- Fixing Unit tests.

## [104.0.34] - 2023-09-28
- OMFP-599, OMFP-600, OMFP-601 - make camera default pan/zoom/look work in teleport mode

## [104.0.33] - 2023-09-28
- Remove dependencies of omni.kit.viewport_widgets_manager

## [104.0.32] - 2023-09-26
- OMFP-580 - Fix for exception when stage is None

## [104.0.31] - 2023-09-25
- OM-108288 - Fix for crash while trying to activate teleport while changing stages.

## [104.0.30] - 2023-09-25
- OM-110163 - Better gesture prevention logic, should unbreak the navigation gestures.

## [104.0.29] - 2023-08-08
- OM-102605 - Only blocking right click when the viewport has focus and teleport is active. Should unblock the filedialog.

## [104.0.28] - 2023-07-10
- OM-99523 - Ensuring that cursed DragGestures don't accidentally show the gizmo when teleport is inactive.

## [104.0.27] - 2023-06-30
- OM-95873 - After "Google Maps" style teleport, lock the camera eye height.

## [104.0.26] - 2023-06-29
- OM-99523 - Hide the teleport widget during "Google Maps" style mouse look.

## [104.0.25] - 2023-06-26
- OM-97980 - Blocking the right mouse button when using the simplified teleport camera manipulator.

## [104.0.24] - 2023-06-06
Adjusted the basic widget's scale and material properties.

## [104.0.23] - 2023-05-26
-OM-95938: Forgot to add the manipulator dependencies

## [104.0.22] - 2023-05-25
-OM-95938: Adjusting how we invert the camera, routing through the model instead of blasting over the settings.

## [104.0.21] - 2023-05-25
-OM-95938: Adding the simplified camera controls.

## [104.0.20] - 2023-05-24
-OM-95929: The basic gizmo has to be solid.

## [104.0.19] - 2023-05-23
-OM-95929: Options to disallow the teleport beam regardless of user choice and use a basic (circle) teleport gizmo.

## [104.0.18] - 2023-03-07
-OM-77060: Fix ETM failure for omni.kit.tool.teleport on Kit 104.2&105.

## [104.0.17] - 2023-03-01
-OM-73550: Fix test failed, use the pos check to instead of the img compare.

## [104.0.16] - 2023-02-27
-Fix test failed.

## [104.0.15] - 2023-02-27
-OM-84058:Fix sometimes camera move far away from scene with double click action.

## [104.0.14] - 2023-02-16
-Fix two clicks to teleport issue.

## [104.0.13] - 2023-02-13
-OM-73550: Fix ETM failed.

## [104.0.12] - 2023-02-10
-Remove all the BVH rebuild.

## [104.0.11] - 2022-08-16
-clean up print.

## [104.0.10] - 2022-08-15
-Remove omni.kit.window.viewport from dependencies.

## [104.0.9] - 2022-08-12
-OM-54872: Improve Teleport, add key word settings to make it start up faster.

## [104.0.8] - 2022-07-21
-OM-57260: Improve Teleport, fix it cause the incorrect camera's focusdistance issue.

## [104.0.7] - 2022-07-12
-OM-53836: Improve Teleport, make it work for VP1 and VP2.

## [104.0.6] - 2022-06-08
-OM-53156: Improve teleport camera focuse distance to avoid broken Pan in nav.

## [104.0.5] - 2022-06-08
 Improve teleport z up rotate and click.

## [104.0.4] - 2022-06-07
- OM-53061: Improve teleport operation, add eye height and scale settings.
- Improve teleport z up rotate and click.

## [104.0.3] - 2022-02-16
- Update the data/teleport_gizmo.usda

## [104.0.2] - 2022-02-10
- Add a setting to show/hide position

## [104.0.1] - 2022-01-21
- update to use new raycast with sdk 104

## [103.0.7] - 2021-12-28
- Improve the performance for teleport arc build
- Fix a current camera issue

## [103.0.6] - 2021-12-20
- Remove c++ part of teleport widget and  rewrite with python

## [103.0.5] - 2021-12-13
- Updated the use of omni.ui.scene

## [103.0.4] - 2021-12-09
- Updated the use of omni.kit.viewport to omni.kit.viewport_legacy

## [103.0.3] - 2021-11-29
- use ui scene

## [3.0.2] - 2021-10-14
- use different version for different sdk

## [103.0.2] - 2021-10-08
- use different version for different sdk

## [0.0.2] - 2021-10-08
- Add set_widget_usd_file interface
- update read me file

## [0.0.1] - 2021-09-27
- Publish omni.kit.tool.teleport first version

# CHANGELOG

This document records all notable changes to ``omni.curve.manipulator`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`.

## [110.0.2] - 2026-10-17

### Changed

- Republish through the verified Windows signing path with signed package metadata.

## [110.0.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: replace removed viewport utility headers with the supported viewport interface.

## [110.0.0] - 2025-12-10
### Changed
- Updated for Kit 110.

## [108.2.0] - 2025-09-10
### Changed
- Updated to Dictionary 2.0.

## [108.0.0] - 2025-06-24
### Changed
- Updated to 108.

## [107.0.4] - 2025-05-27
### Fixed
- Fixed viewport context menu.

## [107.0.3] - 2025-05-13
### Changed
- Disabled viewport_tests on aarch64.

## [107.0.2] - 2025-03-13
### Changed
- Enable Arm Builds

## [107.0.1] - 2025-02-18
### Changed
- Updated `omni.kit.viewport.window` dependency.

## [107.0.0] - 2025-02-05
### Changed
- Updated for Kit 107. Recompiled with ABI=1.

## [105.2.9] - 2024-09-09
### Fixed
- OMPE-20562: Fix deprecated usage for IStageUpdate interface.

## [105.2.8] - 2024-08-12
### Fixed
- Disallowed inserting CV on invalid curve.

## [105.2.7] - 2024-08-05
### Fixed
- Fixed interpolating primvars at the end of a periodic curve.
- Fixed crash when adding cv to an incomplete (2 points) periodic cubic bezier curve.

## [105.2.6] - 2024-04-18
### Changed
- Updated deprecated usage of `omni.usd.active_authoring_layer_context`.

## [105.2.5] - 2024-01-30
### Added
- Added CurveEdit event for CURVE_EDIT_MODE_CHANGED

## [105.2.4] - 2023-08-30
### Changed
- Update unittest to accommodate scale gesture change.

## [105.2.3] - 2023-08-22
### Added
- Added `Split at CV(s)`, `Split at CV(s) to new BasisCurves`, `Delete and Split at CV(s)`, `Delete and Split at CV(s) to new BasisCurves` to curve tool.

## [105.2.2] - 2023-08-03
### Changed
- Changed default purpose of curve to `guide`.

## [105.2.1] - 2023-07-26
### Changed
- Remove unused carb header and republish.

## [105.2.0] - 2023-07-25
### Fixed
- Fixed Freehand mode not respecting curve world transform when adding new points.
- Fixed sample point on curve not visible when RTX rendering is on.
- Fixed scene visualization wireframe being incorrectly turned off when start editing curves.
- Fixed BasisCurves Property Widget header state not refreshing.
### Changed
- Changed to `omni.kit.actions.core` and `omni.kit.hotkeys.core` for keyboard actions.
### Added
- Delete key now deletes selected CVs instead of selected prims.

## [105.1.8] - 2023-05-19
### Fixed
- Fixed issue where curves are not visible when first created

## [105.1.7] - 2023-05-08
### Added
- Added new button to exit curve mode
### Changed
- Changed message when exiting curve mode

## [105.1.6] - 2023-05-08
### Fixed
- Fixed setting interpolation on curve points

## [105.1.5] - 2023-05-02
### Fixed
- Fixed issue where curves are not visible when first created
- Assigning a default width value to newly-created curves

## [105.1.4] - 2023-04-03
### Fixed
- Fixed performance issue in Curve CV widgets when multiple CVs are being manipulated.

## [105.1.3] - 2023-03-22
### Changed
- Republish after USD/python update.

## [105.1.2] - 2023-03-21
### Changed
- Republish after USD/python update.

## [105.1.1] - 2023-03-14
### Changed
- Republish after USD/python update.

## [105.1.0] - 2023-03-07
### Changed
- Changed how periodic curve is created, manipulated and visualized. It now conforms to UsdBasisCurves standard without repeating the start vertex.
- Changed curve editing context menu styling to VP 2.0 style.
- Hid `omni.kit.manipulator.prim` when curve CV manipulation is in action.
### Added
- Added function to convert old incorrect periodic curve data to correct one.
### Fixed
- Minor fixes for tangent drawing.
- Fixed red-dot not visible when inserting new vertex to existing curve segments.

## [105.0.5] - 2023-01-03
### Changed
- Update kit-sdk and curve creator dependency version.

## [105.0.4] - 2022-12-14
### Fixed
- Fixed snap visual indicator and minor cleanups.

## [105.0.3] - 2022-11-22
### Changed
- Addressing feedback from UX Team

## [105.0.2] - 2022-11-18
### Changed
- Adding unit test for ALT+SHIFT mode

## [105.0.1] - 2022-11-16
### Changed
- Updated toolbar for editing curves

## [105.0.0] - 2022-11-16
### Changed
- Update for upstream dependencies.

## [104.8.1] - 2022-11-04
### Added
- Added support for other extensions to override control point properties
### Fixed
- Fixed issue where array elements that had a None value were not showing up as the default value

## [104.8.0] - 2022-11-03
### Added
- Showing control point properties when selected

## [104.7.3] - 2022-11-01
### Changed
- No longer skips RTX render during curve editing.
### Fixed
- Fixed pencil tool cannot create curve longer than 1024 points.

## [104.7.2] - 2022-09-30
### Changed
- Incrementing extension version.

## [104.7.1] - 2022-07-27
### Changed
- Prevented Curve snapping to itself during creation.
- Disabled snap on inserting CV mode.
### Fixed
- Included Z to ndc_location.

## [104.7.0] - 2022-07-21
### Changed
- Updated curve creation snap tools.

## [104.6.1] - 2022-07-21
### Changed
- OM-51358: Coverage for omni.graph.window.particle.system (fixing TeamCity)

## [104.6.0] - 2022-06-24
### Changed
- Integrated manipulator toolbar and new snap features.

## [104.5.5] - 2022-06-16
### Changed
- Fixed Viewport 1.0 context menu when FPS is low.

## [104.5.4] - 2022-06-14
### Changed
- Made tests pass for Viewport 2.0.

## [104.5.3] - 2022-06-06
### Changed
- Edit test based on kit-sdk changes.

## [104.5.2] - 2022-06-03
### Changed
- Removed incompatible dependency version for `omni.kit.manipulator.transform`.

## [104.5.1] - 2022-04-27
### Changed
- Fixed assert in debug build.

## [104.5.0] - 2022-04-20
### Added
- Supported free rotation.

## [104.4.1] - 2022-04-19
### Changed
- Fixed `transform_space` for marquee selection with new kit-sdk.

## [104.4.0] - 2022-04-13
### Changed
- Supported bezier tool in Viewport 2.0.
- Minor bugfixes and UX improvements.

## [104.3.0] - 2022-04-08
### Added
- Added tests.
- Supported curve manipulation in Viewport 2.0

### Changed
- Supported multiple context for curve manipulation.
- Fixed creation order of first pair of tangent and anchor cv.


## [104.2.0] - 2022-03-22
### Added
- Added marquee selection for CVs
### Changed
- Bezier Curve tangent is now always yellow regardless of selection state.
- Moved prompt message to floating window.
- Fixed CV Manipulator when snap to face may snap to invalid (nan) position.
- Exposed `Snap to Face` option in pencil and bezier tool.
- Delayed CV context menu for one frame to resolve conflict with default Viewport context menu.


## [104.1.0] - 2022-03-18
### Changed
- Updated the look of CVs.
- Tangents are now drawn with ui.scene, instead of IDebugDraw.
- Tangents are now highlighted when their CVs are selected.
- When pencil tool finishes, it switches to bezier tool mode.
### Added
- Added property widget fro BasisCurves.

## [104.0.1] - 2022-03-17
### Changed
- Updated menu.

## [104.0.0] - 2022-01-27
### Changed
- Bump version to 104.

## [2.2.2] - 2021-12-20
### Changed
- Removing event based subscriptions and using new Viewport-1 API to disable selection until mouse up.

## [2.2.1] - 2021-12-17
### Added
- Added Preferences page for default new UsdGeomBasisCurves purpose.
### Changed
- Fixed unreleased post-update event subscription in manipulator.

## [2.2.0] - 2021-12-08
### Added
- Added support for `Delete` CV on Linear curve.
### Changed
- Fixed out of sync transform between CV and curve.
- Fixed CV manipulator visibility when not in use.

## [2.1.0] - 2021-12-06
### Added
- Added `on_canceled` override on CV gesture and model.
### Changed
- Changed `omni.kit.viewport` to `omni.kit.viewport_legacy` due to kit-sdk API change.

## [2.0.2] - 2021-12-02
### Changed
- Made dependencies on `omni.kit.window.viewport` and `omni.scene.visualization` optional.

## [2.0.1] - 2021-12-02
### Changed
- Curve creation and manipulation should now update the `extent` attribute.

## [2.0.0] - 2021-11-30
### Changed
- Rebuilt CV manipulator with `omni.kit.manipulator.transform`, with various improvements.

## [1.6.0] - 2021-11-15
### Added
- Allow new CV to snap to surface when `Snap To Face` is enabled on Toolbar.
- Added `Pencil Tool` under `Create` -> `Curve`.

## [1.5.2] - 2021-10-25
- Force update of new version

## [1.5.1] - 2021-09-23
### Changed
- Fixed double removal of curve menubar menu.

## [1.5.0] - 2021-09-08
### Added
- Added `Open/Close Curve(s)` to create or break periodic curve from/to nonperiodic curve.

### Changed
- Curve created by Bezier Curve Tool by default has purpose of `guide`.
- Repeat widths and normals attributes when adding new CV.

## [1.4.2] - 2021-08-31
### Changed
- Switched to `omni.debugdraw` for tangents and points visualization.

## [1.4.1] - 2021-08-31
### Changed
- Fixed insert CV.
- Temporarily disable rtx curves ("omni:rtx:skip" to true) when editing curves to avoid crashes.

## [1.4.0] - 2021-08-26
### Added
- Supported append new CVs to existing Bezier curves.
- Supported creating Bezier curve from scratch (Create -> Curves -> Bezier Curve Tool).
- Added "Corner", "Bezier", "Bezier Corner" to context menu.

## [1.3.0] - 2021-08-23
### Added
- Supported insert CVs to existing Bezier curves.

### Changed
- Handle `normals` and `widths` attributes while deleting CV.


## [1.2.0] - 2021-08-18
### Added
- Supported deleting CVs from Bezier curves.


## [1.1.0] - 2021-08-16
### Changed
- Supported multi UsdGeomBasisCurves prim and multi CVs editing.


## [1.0.0] - 2021-08-06
### Added
- Initial commit.

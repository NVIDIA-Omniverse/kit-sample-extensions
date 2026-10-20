# CHANGELOG

This document records all notable changes to ``omni.kit.tool.markup`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.2.87] - 2026-10-15
### Changed
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then `pump_apply_usd_changes failed (12)` and `PUMP apply_usd_changes ... failed`). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

## [1.2.86] - 2026-08-27
### Fixed
- Switching markup tools while an element is selected now clears the selection, instead of leaving the
  element's transform controls on screen where they could neither resize the element nor draw.

## [1.2.85] - 2026-08-26
### Changed
- OMPE-80508: Import the renderer capture interface from `omni.kit.renderer.capture` instead of the deprecated `omni.kit.renderer_capture` module.

## [1.2.84] - 2026-08-11
### Fixed
- OMPE-101150, OMPE-100640: Fixed markup alignment in thumbnails captured after the viewport resizes.

## [1.2.83] - 2026-07-01
### Changed
- OMPE-98915: Prevented active markup tools from receiving input while moving or resizing a selected markup element.

## [1.2.82] - 2026-05-20
### Changed
- OMPE-94440: Fully skip `test_export_panel` in ETM environments (DGXC and standard ETM), in addition to OVC deployments.

## [1.2.81] - 2026-05-14
### Changed
- OMPE-93756, OMPE-93757: Disabled `test_export_panel` for ETM on DGXC.

## [1.2.80] - 2026-05-07
### Changed
- OMPE-87832: Removed OVC deployment gate on the export panel; allow Nucleus paths in the export directory picker; disable "View Exported Markups" while the destination is a Nucleus URL.

## [1.2.79] - 2025-11-14
### Changed
- Disabling the list window test on ETM DGXC

## [1.2.78] - 2025-10-28
### Changed
- Tweaking some test input to hopefully improve ETM stability

## [1.2.77] - 2025-10-10
### Changed
- OMPE-64552: Updating golden image to reflect some changes to UI from `omni.kit.markup.core`

## [1.2.76] - 2025-10-10
### Changed
- OMPE-64394: Added menu_compatibility=False

## [1.2.75] - 2025-10-07
### Changed
- OMPE-64552: Disabling export panel test when running in cloud.

## [1.2.74] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [1.2.73] - 2025-04-18
### Added
- Changing renderer from PXR to RTX for OVC2 ETM support.

## [1.2.72] - 2025-03-07
### Added
- Fix type error.

## [1.2.71] - 2025-01-06
### Added
- Update public api

## [1.2.70] - 2024-11-28
### Fixed
- OMPE-27978 - Update kit sdk to 107.

## [1.2.69] - 2024-04-11
### Fixed
- OMPE-1518 - Markups shift after adding comments.

## [1.2.68] - 2023-12-05
### Fixed
- OMFP-3955 - reset markup state when toolbar is clicked to prevent state/tool mismatches.

## [1.2.67] - 2023-11-16
### Added
- OM-89817 - Improving unit tests.

## [1.2.66] - 2023-11-16
### Added
- OMFP-3056 - Add tests for markup in an inserted layer

## [1.2.65] - 2023-11-02
### Added
- OMFP-3426 - Add tests for markup hotkeys

## [1.2.64] - 2023-10-31
### Changed
- OMFP-3412: Thumbnails for markups don't display in OVC (Test)

## [1.2.63] - 2023-10-31
### Fixed
- OMFP-3238 - Comment color picker behaves different than other objects

## [1.2.62] - 2023-10-30
### Changed
- OMFP-3412: Thumbnails for markups don't display in OVC

## [1.2.61] - 2023-10-30
### Changed
- OM-110920: ETM failure for omni.kit.tool.markup on release/105.1

## [1.2.60] - 2023-10-30
### Changed
- added identifiers to ui elements for easier query

## [1.2.59] - 2023-10-27
### Fixed
- OMFP-3276 - Markups are not consistent from machine to machine/aspect ratios

## [1.2.58] - 2023-10-27
### Fixed
- OMFP-3180 - Changed app name in one of the dialogs.

## [1.2.57] - 2023-10-26
### Fixed
- OMFP-3180 - Fix bug where new text in comment markup is lost when markup's style is changed.

## [1.2.56] - 2023-10-26
### Changed
- OMFP-2545 - [Mark Up] cant draw in top and bottom of screen (added test)

## [1.2.55] - 2023-10-25
### Fixed
- OMFP-3185 - Only require one 'undo' to remove a shape markup after it's created.

## [1.2.54] - 2023-10-24
### Added
- OMFP-2096 - Test for canceling out of a markup then hitting Undo.

## [1.2.53] - 2023-10-24
### Added
- OMFP-2906 - Added test for OMFP-2749.

## [1.2.52] - 2023-10-25
### Changed
- Changed tooltip for Exit markup button

## [1.2.51] - 2023-10-24
### Fixed
- OMFP-3098 - [markup] cannot start new element drawing if cursor overlaps exiting element

## [1.2.50] - 2023-10-19
### Fixed
- OMFP-2749 - fix for placement of markup toolbar when window is resized to be wide.

## [1.2.49] - 2023-10-19
### Changed
- Added test for OMFP-2672

## [1.2.48] - 2023-10-19
### Fixed
- Refactored MarkupRenderElement and repairs Comment markup behavior

## [1.2.47] - 2023-10-19
### Fixed
- Fixed test_toolbar_comment

## [1.2.46] - 2023-10-19
### Fixed
- Improved Comment Element creation and selection behavior

## [1.2.45] - 2023-10-17
### Fixed
- OMFP-2545: [Mark Up] cant draw in top and bottom of screen

## [1.2.44] - 2023-10-17
### Fixed
- OMFP-2488: Investigate test failures in omni.kit.tool.markup

## [1.2.43] - 2023-10-17
### Fixed
- updated golden images for tests

## [1.2.42] - 2023-10-17
### Fixed
- Markup element does full refresh when re-draw occurs

## [1.2.41] - 2023-10-17
### Changed
- OMFP-2393 Move the markup toolstrips down (where navbar is).

## [1.2.40] - 2023-10-17
### Fixed
- Element rendering was applying style to selection rectangle in transform

## [1.2.39] - 2023-10-17
### Fixed
- OMFP-2243 - Avoid complete rebuild on markup refresh as it kicks users out of live Markup viewing

## [1.2.38] - 2023-10-16
### Fixed
- OMFP-2406: [Markup] Selecting scrollbar in comments element will lock Markup into a dead state

## [1.2.37] - 2023-10-13
### Fixed
- OMFP-998: [OVC] Markup comments incomplete or missing

## [1.2.36] - 2023-10-13
### Fixed
- OMFP-2395 - workaround for problem when exiting the ColorWidget popup by clicking on the Markup Toolbar.
- OMFP-2485 - workaround for problem when creating an element but mousing up on the toolbar ColorWidget.

## [1.2.35] - 2023-10-13
### Fix
- OMFP-2393 - Forced Markup toolbar offset to desired default

## [1.2.34] - 2023-10-13
### Fix
- Reverted behavior of apply/cancel Markup to exit Markup Edit mode

## [1.2.33] - 2023-10-12
### Changed
- Increased test coverage

## [1.2.31] - 2023-10-12
### Fix
- OMFP-2405 - Deselect all markups on exit from the mode

## [1.2.30] - 2023-10-11
### Fix
- Fixing golden image.

## [1.2.29] - 2023-10-11
### Fix
- OMFP-1901: Markup element remains selected at end of edit

## [1.2.28] - 2023-10-10
### Fix
- Improved Markup element selection
- Improved Markup state transitions

## [1.2.27] - 2023-10-10
### Fix
- OMFP-2141: New Markup Element created when a Line is selected

## [1.2.26] - 2023-10-09
### Changed
- OMFP-1968 - Set "modal" flag when markup is active to suppress other conflicting UIs

## [1.2.25] - 2023-10-10
### Fix
- OMFP-2143 - Always draw selected element to the top of the ui stack

## [1.2.24] - 2023-10-07
### Fix
- OMFP: Export Mark UP should be on Mark UP thumbstrip

## [1.2.23] - 2023-10-06
## Changed
- OMFP-844: Support undo/redo of markup operations.

## [1.2.22] - 2023-10-07
### Fix
- Refactored internal tool state management.

## [1.2.21] - 2023-10-06
### Fix
- Fixing changelog.

## [1.2.20] - 2023-10-06
### Fix
- OMFP-1670 - Disable offset for free shape widgets

## [1.2.19] - 2023-10-06
### Fix
- OMFP-1007 - Changed markup prim types to omni::ignorePrimType to avoid expensive FSD update

## [0.2.17] - 2023-10-05
## Changed
- Disabling a test in linux

## [0.2.15] - 2023-10-05
## Changed
- OMFP-853: [Mark Up Export ] MArk Ups should not capture MarkUp Tool Bar or other none Mark Up Ui elements

## [0.2.14] - 2023-10-05
### Fix
- Updated golden images.

## [0.2.13] - 2023-10-05
### Fix
- OMFP-852 - Improvements to Edit Element Toolbar

## [0.2.12] - 2023-10-04
### Fix
- OMFP-1487: Dragging Markup drawing outside viewport causes scaling problem

## [0.2.11] - 2023-10-04
### Fix
- Fixed ETM tests

## [0.2.10] - 2023-10-04
### Fix
- Fixed typos and misnamed constants

## [0.2.9] - 2023-10-04
### Fix
- Fixing multiple markup issue with OMFP-1695

## [0.2.8] - 2023-10-04
### Changed
- OMFP-1026 - Markup deactivates when other tools activate

## [0.2.7] - 2023-10-04
### Fix
- OMFP-1695 - Markup should not refresh all elements unless necessary

## [0.2.6] - 2023-10-04
### Fix
- OMFP-1485 - fixed glitchy draw in Markup Elements

## [0.2.5] - 2023-10-03
### Changed
- OM-89817 - Fixing golden images.

## [0.2.4] - 2023-10-02
### Changed
- OMFP-850 - Removed selection mode from Markup and allow selection in any mode

## [0.2.3] - 2023-09-29
### Fix
- Fixing unit test golden image.

## [0.2.2] - 2023-09-29
### Fix
- Multiple crash fixes OMFP-1353, OMFP-1522

## [0.2.1] - 2023-09-29
### Fix
- Removed a diagnostic print in Markup selection

## [0.2.0] - 2023-09-28
### Changed
- OMFP-845 - Added selection tolerance setting
- OMFP-845 - Drawing markups in frame local space and are moveable/scalable

## [0.1.57] - 2023-07-26
### Changed
- OM-###### - Changed Markup Export from a floating dialog to a docked panel


## [0.1.56] - 2023-05-10
### Changed
- OM-89917 - Disable Markup Export on cloud deployments.


## [0.1.55] - 2023-03-16
### Changed
- OM-80113 - Ensuring that the markup tool pulls in the playlist extension.
- Updated unit tests to ensure only the viewport window is visible.

## [0.1.54] - 2023-03-14
### Changed
- OM-80113 - Fixing "All Markups" section of the playlist tool.

[0.1.53] - 2023-03-14
## Fixed
- Discovered a missing method that could be breaking playlist tools.

[0.1.52] - 2023-03-10
## Fixed
- Added missing `super().__init__()` needed for python 3.10

[0.1.51] - 2022-03-09
## Improved
- If a user exports markup data while a markup is active for editing a toast popup will notify them that the active markup will not be included.

[0.1.50] - 2022-03-08
## Fix
- OM-85342 - The Markup Export window is can no longer be docked.

[0.1.49] - 2022-03-07
## Fix
- Markup Toolbars should now have a background color similar to the navigation bar.

[0.1.48] - 2022-03-07
## Fix
- OM-83023 - Fix for element deletion breaking the selection tool.

[0.1.46] - 2022-03-07
## Fix
- OM-84531 - Golden image fix.

[0.1.45] - 2022-03-07
## Fix
- OM-84531 - Markup element selection regression

[0.1.44] - 2023-03-06
## Fixed
- OM-82648 - Ensuring navigation bar is hidden while markup tool is active.

[0.1.43] - 2023-03-06
## Improved
- OM-84674 - Comment box drag interaction should be improved.
- OM-84550 - Panels should be less likely to spawn on top of each other.
- OM-84121 - Comment box drag interaction should be improved, as should the text editing.
- OM-83114 - Markup tool settings should persist between uses.
- OM-83109 - Deletion of markup elements should be possible.
- OM-83023 - Undo improvements (probably still bugs)
- OM-82091 - Markup should switch to selection tool when disabling active tool.

[0.1.42] - 2023-03-06
## Changed
- OM-84956 Fixed attempt at prohibiting markup export to Nucleus locations.

[0.1.41] - 2023-03-06
## Changed
- OM-84956 The user is prevented from exporting markup data to a Nucleus location.

[0.1.40] - 2023-02-26
## Changed
- OM-84127 view_mode -> application_mode

[0.1.39] - 2023-02-23
## Changed
- Added lower img thresholds back in for tests

[0.1.38] - 2022-02-21
## Added
- OM-83023 - Markup undo support.

[0.1.37] - 2023-02-13
## Changed
- Adding fast shutdown to test arguments.

[0.1.36] - 2023-01-17
## Changed
- Fixed the python module information to not break everything anymore.

[0.1.35] - 2023-01-05
## Changed
- Broke the markup tool into individual tools.
- Added unit tests for various tools.
## Added:
- Shape tool now supports shift and ctrl modifiers
- Shift constrains the shape to sharing a height/width (rectangles become squares, ellipsies become circles, etc...)
- Ctrl causes the shape to originate from the center and grow outwards instead of corner to corner.


[0.1.34] - 2022-12-15
## Changed
- Modified the default Markup Export storage folder path.

[0.1.33] - 2022-12-14
## Added
- Hiding the markup panel when in approve mode.

[0.1.32] - 2022-12-08
## Added
- Support for hiding the markup tools when switching to present mode in view.

[0.1.31] - 2022-11-18
## Changed
- Removed a weird hack and replaced it with a less bad one.

[0.1.30] - 2022-11-17
## Changed
- Fixed a bug where panels would conflict with the navigation tools.

[0.1.29] - 2022-11-16
## Changed
- Export Markup button handler changed to async call to export() in MarkupExport class.

[0.1.28] - 2022-11-16
## Improved
- Markup sidecar support now warns when you cannot unlock a markup entry.

[0.1.27] - 2022-11-10
## Fixed
- OM-72312 - Markup now works on first attempt.

[0.1.26] - 2022-11-10
## Fixed
- OM-72309 - No longer need to click twice to get the markup to appear
- OM-72308 - No longer frames the selection when displaying the markup

[0.1.25] - 2022-11-07
## Added
- Sidecar support for view.

[0.1.24] - 2022-11-05
## Changed
- HTML checkbox enabled on Markup Export dialog.

[0.1.23] - 2022-11-04
## Changed
- Markup export dialog finalized. Pop up "toast" notification for export completion added.

[0.1.22] - 2022-11-02
## Changed
- PDF export controls active and utilized.

[0.1.21] - 2022-11-02
## Changed
- moved core classes from ui/markup_export.py to omni.kit.markup.core.

[0.1.20] - 2022-11-01
## Changed
- etm failure fix.

[0.1.19] - 2022-10-31
## Changed
- markup_export.py cleanly handles if xlsxwriter is available or not.

[0.1.18] - 2022-10-31
## Changed
- Integrated 3rd party XLSXWriter module into packman. XLS/XLSX file writing enabled.

[0.1.17] - 2022-10-30
## Changed
- Markup export supports CSV export. XLSX export is ready, for when the XLSXWrter library is added to our Python distribution.

[0.1.16] - 2022-10-26
## Added
- Markup export dialog stubbed in. Currently non-functional

[0.1.15] - 2022-10-25
## Improved
- Adjusting ViewportMarkup ownership

[0.1.14] - 2022-10-13
## Improved
- Buttons should no longer be highlighted in red.

[0.1.13] - 2022-10-07
## Improved
- MarkupButton no longer requies precalculating the label widths.

[0.1.12] - 2022-10-06
## Improved
- Markup element alignment with viewport resolution.
## Fixed
- Elements appearing selected when viewing a markup entry.

[0.1.11] - 2022-08-31
## Improved
- Comment box initial transform, we now attempt to scale it better based on the screen state.
- Empty Comment Markups will self-delete when changing tools

[0.1.10] - 2022-08-29
## Changed
- The icon path for Markup tool icons now resolves correctly on both Windows and Linux.

[0.1.9] - 2022-08-26
## Improved
- State behavior changes with new playlist window.

[0.1.8] - 2022-08-25
## Changed
- Support for new markup playlist window.
- Removed redundant Apply/Cancel windows in deference to the unified toolbar UX.
- Fixed thumbnail generation on save.

[0.1.7] - 2022-08-18
## Improved
- Camera locking again when viewing, not just editing markup.
- Thumbnail serialization should no longer create bad thumbnails.
- Draw tool no longer creates extra line between start and mouse.

[0.1.6] - 2022-08-17
## Improved
- Selection tool behavior.
- Comment selection in particular.

[0.1.5] - 2022-08-08
## Improved
- VP2 Support
- Markup aligning to rendered area of viewport.

[0.1.4] - 2022-07-29
## Improved
- VP2 support

[0.1.3] - 2022-07-27
## Improved
- VP2 support

[0.1.2] - 2022-06-26
## Added
- VP2 support

[0.1.1] - 2021-08-12
========================

Changed
-------

- Use editor menu.

[0.1.0] - 2021-01-11
========================

Added
------

- Initial markup tool implementation

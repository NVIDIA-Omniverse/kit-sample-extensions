# CHANGELOG

This document records all notable changes to ``omni.kit.markup.core`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.3.6] - 2026-10-15
### Changed
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then `pump_apply_usd_changes failed (12)` and `PUMP apply_usd_changes ... failed`). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

## [1.3.5] - 2026-08-26
### Changed
- OMPE-80508: Import the renderer capture interface from `omni.kit.renderer.capture` instead of the deprecated `omni.kit.renderer_capture` module.

## [1.3.4] - 2026-08-12
### Changed
- Scheduled coroutines with `omni.kit.async_engine.run_coroutine` instead of `asyncio.ensure_future`, which guarantees they run on the main thread.

## [1.3.3] - 2026-06-22

### Fixed

- OMPE-98259: Hide the navigation menubar while editing a markup. The
  `/exts/omni.kit.viewport.navigation.core/isVisible` setting is captured when
  edit mode begins, forced to false during editing, and restored to its prior
  value when editing ends.

## [1.3.2] - 2026-05-29

### Fixed

- OMPE-19499: preserve in-progress Markup comment edit when the markup list
  refreshes due to a remote live-session change. _on_markups_changed and
  _on_markup_changed now defer the rebuild while the local user is actively
  typing in a comment field, and apply the deferred rebuild from _on_edit_end
  once the edit completes.

## [1.3.1] - 2026-05-07
### Changed
- OMPE-87832: Allow exporting markup data to Nucleus locations by writing to a temp dir and copying with `omni.client.copy_async`.

## [1.3.0] - 2026-03-31
### Changed
- Last bit of updating to events 2.0

## [1.2.35] - 2026-01-15
### Changed
- Styling update using centralized global styling

## [1.2.34] - 2026-01-15
### Changed
- Bump the version to force replublish

## [1.2.32] - 2025-12-12
### Changed
- Fixing flaky tests

## [1.2.31] - 2025-11-14
### Changed
- Disabling list window test on ETM DGXC

## [1.2.30] - 2025-10-28
### Changed
- Tweaking some test input to hopefully improve ETM stability

## [1.2.29] - 2025-10-15
### Changed
- OMPE-57963: Reverting the layers 2.0 update, it breaks to many things.

## [1.2.28] - 2025-10-10
### Changed
- OMPE-64394: Added menu_compatibility=False

## [1.2.27] - 2025-10-13
### Changed
- OMPE-57963: Switching the layer events over to 2.0

## [1.2.26] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [1.2.25] - 2025-07-16
### Changed
- Replace omni.renderer_capture to omni.kit.renderer_capture

## [1.2.24] - 2025-05-02
### Changed
- Updating events to event dispatcher

## [1.2.23] - 2025-04-18
### Changed
- Changing renderer from PXR to RTX for OVC2 ETM support.

## [1.2.22] - 2025-03-07
### Changed
- Fix type error.

## [1.2.21] - 2025-03-06
### Changed
- udpate public api.

## [1.2.20] - 2024-07-29
### Changed
- OMPE-12031: Markup visibility on rename

## [1.2.19] - 2024-05-06
### Changed
- OMPE-31744: Updating reportlab to 4.2.0

## [1.2.18] - 2024-01-10
### Changed
- OMFP-4084: Markups being deleted from source layer

## [1.2.17] - 2023-12-11
### Changed
- OMFP-3846: remainder of the fix for markup rename and delete when live

## [1.2.16] - 2023-11-29
### Changed
- OMFP-3846: part of the fix for markup rename and delete when live

## [1.2.15] - 2023-11-29
### Changed
- OMFP-2778: fix bug where markup list window and icons appear when not in markup mode due to another user in a live session editing a markup
             (similar bug description from two changelog entries ago, but different cause).

## [1.2.14] - 2023-11-28
### Fixed
- OMFP-3975: Cancel pushing hotkey context if window becomes invisible immediately

## [1.2.13] - 2023-11-15
### Fixed
- OMFP-2778: fix bug where markup icons appear when not in markup mode due to another user in a live session editing a markup.

## [1.2.12] - 2023-11-16
- OMFP-3554: clear editing variable to pass tests

## [1.2.11] - 2023-11-16
- OMFP-3554: refresh markups on layer change notify

## [1.2.10] - 2023-11-14
- OM-106439: Ensuring the `Task exception was never retrieved` message doesn't kill us.

## [1.2.9] - 2023-11-14
### Changed
- OM-106439: Fix ETM test's none stage error again.

## [1.2.8] - 2023-11-13
### Changed
- OM-106439: Fix ETM test's none stage error.

## [1.2.7] - 2023-11-09
### Changed
- Added a few more unit tests

## [1.2.6] - 2023-11-03
### Changed
- OMFP-3600: Bumping the reportlab version to 3.6.13

## [1.2.5] - 2023-11-02
### Changed
- Increasing test coverage

## [1.2.4] - 2023-11-02
### Fixed
- Fixing thumbnails when the DPI scaling is not 1.0.

## [1.2.3] - 2023-11-02
### Added
- OMFP-3422/OMFP-3426: Add tests for markup hotkeys

## [1.2.2] - 2023-10-31
### Added
- Add action display name to show well in Actions/Hotkeys window

## [1.2.1] - 2023-10-30
### Changed
- added identifiers to ui elements for easier query

## [1.2.0] - 2023-10-25
### Changed
- OMFP-778: Add tests for exporting markups and verifying csv contents
- add Mock objects for MarkupExport and MarkupExportObject
- add default argument values; MarkupExtension() and MarkupExport()
- expose properties from MarkupExport attributes

## [1.1.41] - 2023-10-26
### Changed
- OMFP-1021: Hotkey fixes.

## [1.1.40] - 2023-10-24
### Changed
- OMFP-2935: Increasing the pause between export screenshot capture, in the hopes of the renderer stabilizing.

## [1.1.39] - 2023-10-23
### Fixed
- OMFP-2961: [OVC POD-1][USD Explorer 2023.2.0-beta.44] Not able to create Markup. Live session out of sync. Console continuously showing errors.

## [1.1.38] - 2023-10-23
### Changed
- OMFP-3084: Annotations Sometimes Don't Save

## [1.1.37] - 2023-10-23
### Changed
- OMFP-1021: Add hotkeys for markups

## [1.1.36] - 2023-10-23
### Changed
- OMFP-2943: Add test for order of markups

## [1.1.35] - 2023-10-20
### Fixed
- Fixed dependencies.

## [1.1.34] - 2023-10-19
### Fixed
- OMFP-2669 - Adjust button icons, layout and colors.

## [1.1.33] - 2023-10-19
### Fixed
- OMFP-2785 - Made Markup toolbar optional when editing a markup

## [1.1.32] - 2023-10-18
### Fixed
- OMFP-2547 - Restore list window show/hide logic after editing comment

## [1.1.31] - 2023-10-17
### Fixed
- OMFP-2699 - Simpler list window layout logic.

## [1.1.30] - 2023-10-17
### Fixed
- OMFP-2669 - Adjust button layout.

## [1.1.29] - 2023-10-17
### Fixed
- OMFP-2547 - selecting a markup will not close list window, so prev/next button can cycle through them

## [1.1.28] - 2023-10-17
### Fixed
- test fixes

## [1.1.27] - 2023-10-16
### Fixed
- OMFP-2617 - Set current_markup when beginning to edit a markup.

## [1.1.26] - 2023-10-17
### Fixed
- OMFP-2243 - Avoid complete rebuild on markup refresh as it kicks users out of live Markup viewing

## [1.1.25] - 2023-10-16
### Fix
- OMFP-2406 - [Markup] Selecting scrollbar in comments element will lock Markup into a dead state

## [1.1.24] - 2023-10-13
### Fix
- Test fix - don't pass invalid pixel_size setting to UpdateMarkupElement.

## [1.1.23] - 2023-10-13
### Fix
- OMFP-2125 - Tracking distance from edge of viewport for list windows.

## [1.1.22] - 2023-10-13
### Fix
- Icon visibility

## [1.1.21] - 2023-10-13
### Fix
- OMFP-998: [OVC] Markup comments incomplete or missing

## [1.1.20] - 2023-10-13
## Fixed
- OMFP-2317 - Changed ignorePrimType type on data prims to ignorePrim attribute

## [1.1.19] - 2023-10-11
## Changed
- OMFP-2471 - Renamed 'comment' -> 'review'

## [1.1.18] - 2023-10-11
### Fix
- OMFP-2327 - Cleaned up playback state.

## [1.1.17] - 2023-10-11
### Fix
- OMFP-2424 - Avoid KeyError on markup lookup.

## [1.1.16] - 2023-10-12
### Fix
- OMFP-2405 - Allow deselect for Markup playlist

## [1.1.15] - 2023-10-11
### Fix
- OMFP-2125 - Reseting the list window position when swapping between app modes.

## [1.1.15] - 2023-10-11
### Fix
- OMFP-2142 - execute DeletePrims as a command so the action is properly recorded on the undo stack.

## [1.1.14] - 2023-10-11
### Fix
- "OM-106439 & OM-106468 - Fixing an attribute change from PIL"

## [1.1.13] - 2023-10-11
### Fix
- OMFP-2323: Early out in cases where there are no valid markup paths to refresh.

## [1.1.12] - 2023-10-11
### Fix
- OMFP-1901: Markup element remains selected at end of edit

## [1.1.11] - 2023-10-10
## Changed
- Hide markup list window when tools are disabled

## [1.1.10] - 2023-10-09
## Changed
- OMFP-2212: fix refresh_markup makes errors with closing stage
- OMFP-2067: add tests for the extension

## [1.1.9] - 2023-10-06
## Changed
- OMFP-1975: Export Mark UP should be on Mark UP thumbstrip

## [1.1.8] - 2023-10-06
## Changed
- OMFP-844: Support undo/redo of markup operations.

## [1.1.7] - 2023-10-06
## Changed
- OMFP-749: Manage playback state between Markup and Waypoint

## [1.1.6] - 2023-10-06
### Fix
- OMFP-1007 - Changed markup prim types to omni::ignorePrimType to avoid expensive FSD update

## [1.1.5] - 2023-10-05
## Changed
- OMFP-746: Allow resize of Markup list window

## [1.1.4] - 2023-10-04
## Changed
- OMFP-853: [Mark Up Export ] MArk Ups should not capture MarkUp Tool Bar or other none Mark Up Ui elements

## [1.1.3] - 2023-09-29
## Changed
- OMFP-745: Save position of Markup list window

## [1.1.2] - 2023-09-29
### Fix
- Multiple crash fixes OMFP-1353, OMFP-1522

## [1.1.1] - 2023-08-30
## Fix
- OMFP-1205: Moving some imports around to improve startup time.

## [1.1.0] - 2023-08-30
## Fix
- OM-107163: Markup should be in Show By Type

## [1.0.83] - 2023-07-13
## Fix
- OM-100910 - Screenshot size was being set too small.

## [1.0.82] - 2023-07-10
## Fix
- Fixed name of USD Presenter's sidecar extension.

## [1.0.81] - 2022-05-15
## Fix
- OM-85645 - Set the title metadata for PDF to be the file name.
- OM-86636, OM-85641 - Added additional buffer between PDF screen captures to prevent async race condition.

## [1.0.80] - 2022-04-25
## Fix
- OM-92155 - Making markup deletions undoable. Not sure why I didn't have this from the start.

## [1.0.79] - 2022-04-24
## Fix
- OM-91910 - Adjusting the raster policy for the waypoint and markup thumbstrip.

## [1.0.78] - 2022-04-18
## Fix
- OM-89920 - Fixing the waypoint and markup windows such that they don't keep recreating their playbars

## [1.0.77] - 2023-03-15
### Changed
- Removing `omni.kit.markup.playlist` from the dependencies because it caused a circular dependency issue.

## [1.0.76] - 2023-03-15
### Changed
- OM-75746 - Fixing ETM failure by add omni.kit.markup.playlist to dependencies.

## [1.0.75] - 2023-03-14
### Changed
- OM-80113 - Fixing "All Markups" section of the playlist tool.

[1.0.74] - 2022-03-13
## Fix
- Discovered a missing method that could be breaking playlist tools

[1.0.73] - 2022-03-09
## Fix
- OM-85347: Markup export to xlsx format will use "Markup Data" as the sheet name, instead of a variation of the stage name.

[1.0.72] - 2022-03-09
## Fix
- OM-82418: Use the show/hide prim icon interface to show/hide all markup icons.

[1.0.71] - 2022-03-08
## Fix
- Ensuring that refreshed icons are clickable.

[1.0.70] - 2022-03-08
## Fix
- OM-85348 - Markup export now includes the Notes: field data from the thumbnail strip. (try / except error fixed)

[1.0.69] - 2022-03-08
## Fix
- OM-85347 - Markup export to XLSX will no longer fail if the thumbnail data is corrupt/invalid.
- OM-85348 - Markup export now includes the Notes: field data from the thumbnail strip.

[1.0.68] - 2022-03-08
## Fix
- OM-84954 - Fix for waypoint icons being cleared constantly

[1.0.67] - 2022-03-07
## Fix
- OM-83023 - Fix for element deletion breaking the selection tool.

[1.0.66] - 2022-03-07
## Fix
- OM-84531 - Markup element selection regression

[1.0.65] - 2022-03-06
## Improved
- OM-84674 - Comment box drag interaction should be improved.
- OM-84550 - Panels should be less likely to spawn on top of each other.
- OM-84121 - Comment box drag interaction should be improved, as should the text editing.
- OM-83114 - Markup tool settings should persist between uses.
- OM-83109 - Deletion of markup elements should be possible.
- OM-83023 - Undo improvements (probably still bugs)
- OM-82091 - Markup should switch to selection tool when disabling active tool.

[1.0.64] - 2022-02-27
## Improved
- OM-84956 - Exporting text comments in Live sessions will no longer fail.

[1.0.63] - 2022-02-27
## Improved
- OM-83104 - icons should refresh after leaving a live session.

[1.0.62] - 2022-02-26
## Changed
- OM-84127 - view_mode -> applicaiton_mode

[1.0.61] - 2022-02-24
## Improved
- OM-84028 - Caching the thumbnail data to improve live sync times.

[1.0.60] - 2022-02-23
## Fixed
- OM-83834 - Fix for waypoint edit widget not displaying.

[1.0.59] - 2022-02-21
## Fixed
- OM-83074 - Markup export - limiting title name to <=31 chars for XLSWriter..

[1.0.58] - 2022-02-21
## Fixed
- OM-83023 - Markup undo support.

[1.0.57] - 2022-02-16
## Fixed
- OM-82912 - Fixing a bunch of issues with the list window.

[1.0.56] - 2022-02-15
## Fixed
- OM-80840 - Adding rename support to list window.

[1.0.55] - 2022-02-15
## Fixed
- OM-82709 - Markup window should no longer appear in center of viewport when empty.

[1.0.54] - 2022-02-14
## Fixed
- OM-81968 - Live markups should no longer be created at the wrong user's location.

[1.0.53] - 2022-02-13
## Fixed
- Double checking that the stage is not None, and is valid.

[1.0.52] - 2022-02-10
## Changed
- OM-80840 - Consolidating markup list browser related code into markup.core for other extensions to consume.

[1.0.51] - 2022-02-02
## Fix
- OM-80681: Fixing a NameError

[1.0.50] - 2022-02-02
## Improved
- OM-80681: Markup and live session sync improvements

[1.0.49] - 2022-01-27
## Fixed
- OM-77378: Markup should no longer hang when Editing a markup with larger scenes.

[1.0.48] - 2022-01-17
## Fixed
- OM-78327: Fix python moudle  xlsxwriter not found issue for ETM failed .

[1.0.47] - 2022-01-16
## Fixed
- OM-78327: Fix python path not found issue for ETM failed .

[1.0.46] - 2022-01-09
## Fixed
- Support for more modular markup tools.

[1.0.45] - 2022-12-15
## Fixed
- Fixing rejected state from being bashed into None

[1.0.44] - 2022-12-15
## Fixed
- Fixing rejected state from being bashed into None

[1.0.43] - 2022-12-15
## Fixed
- OM-75937 - Sometimes the URL link in PDF Markup export fails in reportlab.

[1.0.42] - 2022-12-14
## Fixed
- Allow for approve/reject data to be saved/loaded from the prim sucessfullly.

[1.0.41] - 2022-12-13
## Fixed
- A very devious bug that was causing the very first markup element to not get saved, but only in view. (thanks Greg!)

[1.0.40] - 2022-12-13
## Fixed
- Issue loading older markup entries that lacked approval status or timeline values.

[1.0.39] - 2022-12-09
## Added
- MarkupApproveSetting class housing to provide support for accept/reject approval type

[1.0.38] - 2022-12-09
## Removed
- Removed unused dependency on `omni.kit.environment.core`

[1.0.37] - 2022-12-08
## Added
- Support for hiding the markup tools when switching to present mode in view.

[1.0.36] - 2022-12-05
## Updated
- Storing frame position for markups to handle for animation state.

[1.0.35] - 2022-11-29
## Changed
- Refactored sidecar support, hopefully to better leverage the sidecar extension.

[1.0.34] - 2022-11-28
## Fixed
- Cancel wasn't repsecting the proper edit context so it caused issues with view's sidecar system.

[1.0.33] - 2022-11-21
## Fixed
- Cancel / Exit buttons now properly restore original markup state.

[1.0.32] - 2022-11-18
## Changed
- Adjusted markup default naming to match waypoint.

[1.0.31] - 2022-11-18
## Fixed
- Markup icon casing didn't match, so it failed on linux.

[1.0.30] - 2022-11-17
## Fixed
- Markup thumbnails were still being saved in the root layer during sidecar operations.

[1.0.29] - 2022-11-16
## Improved
- PDF Markup Export now includes full size screenshots

[1.0.28] - 2022-11-16
## Improved
- Markup sidecar support now warns when you cannot unlock a markup entry.

[1.0.27] - 2022-11-15
## Updated
- PDF Export directory gets correctly made on Linux. Succcessfully switch to packman based Python lib inclusion.

[1.0.26] - 2022-11-14
## Updated
- Had to reinstate "import omni.kit.pipapi". View navigation unit tests were failing on missing 3rd party modules.

[1.0.25] - 2022-11-14
## Updated
- Markup PDF export now has clickable links and better page layout.

[1.0.24] - 2022-11-10
## Updated
- Using specific pip_prebundle paths to packages for readability.

[1.0.23] - 2022-11-10
## Fixed
- OM-72309 - No longer need to click twice to get the markup to appear
- OM-72308 - No longer frames the selection when displaying the markup

[1.0.22] - 2022-11-10
## Improved
- Set third-party python dependencies (XlsxWriter, reportlab) to be included at build time with extension

[1.0.21] - 2022-11-07
## Added
- Sidecar support for view.

[1.0.20] - 2022-11-05
## Changed
- PDF Export uses scaled thumbnails for image mockups. HTML Export working.

[1.0.19] - 2022-11-04
## Changed
- Enhanced logging in MarkupExport class.

[1.0.18] - 2022-11-02
## Changed
- Moved the what-to-export? logic from the UI layer into MarkupExport.

[1.0.17] - 2022-11-02
## Changed
- Brought over core export classes from kit.tool.markup/ui/markup_export.py to a new export.py file here.

[1.0.16] - 2022-10-26
## Changed
- Adjusting ViewportMarkup ownership.

[1.0.15] - 2022-09-21
## Fix
- attempting to show the icons before a stage exists was causing an exception at startup.

[1.0.14] - 2022-09-21
## Improved
- Ensuring that markup icons are not visible when editing markup.

[1.0.13] - 2022-09-06
## Improved
- Setting the scrollbars to be "as needed" instead of "always"

[1.0.12] - 2022-09-02
## Improved
- Thumbnail capture for markup

[1.0.11] - 2022-08-25
## Improved
- State behavior changes in playlist window.

[1.0.10] - 2022-08-25
## Changed
- Support for new markup playlist window.
- Removed redundant Apply/Cancel windows in deference to the unified toolbar UX.
- Fixed thumbnail generation on save.

[1.0.9] - 2022-08-18
## Improved
- Camera locking again when viewing, not just editing markup.
- Thumbnail serialization should no longer create bad thumbnails.
- Draw tool no longer creates extra line between start and mouse.

[1.0.8] - 2022-08-08
## Added
- Markup registered with the VP2 menubar to show/hide icons.

[1.0.7] - 2022-08-08
## Improved
- VP2 Support
- Markup aligning to rendered area of viewport.

[1.0.6] - 2022-07-29
## Improved
- VP2 Support

[1.0.5] - 2022-07-27
## Improved
- VP2 support

[1.0.4] - 2022-01-21
Added
- Initial kit markup window implementation

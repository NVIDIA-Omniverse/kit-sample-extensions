# Changelog

## [110.0.1] - 2026-08-24
### Fixed
- OMPE-106826: Added the missing `human_delay(30)` double-click guard to
  `test_anim_curve_editor_move_multiple_keys_selected_by_ctrl_clicking`, which was failing the golden image test.
- Visual tests sharing a golden image now capture under their own name, so failure artifacts aren't overwritten.

## [110.0.0] - 2025-12-15
### Changed
- Updated kit-sdk version

## [109.0.0] - 2025-09-18
### Changed
- Updated kit-sdk version

## [108.0.2] - 2025-08-13
### Changed
- Update menu logic to use omni.kit.menu.utils

## [108.0.1] - 2025-07-16
### Changed
- Replace omni.renderer_capture to omni.kit.renderer_capture

## [108.0.0] - 2025-06-27
### Changed
- Upgraded Kit SDK to 108
-
## [106.4.2] - 2025-06-03
### Added
- OMPE-44157: Handle the runtime exception when acquiring windowing interface on OVC2.

## [106.4.1]
### Changed
- Upgraded Kit SDK to 107.3.

## [106.4.0]
### Changed
- Upgrade Kit SDK to 106.4

## [106.0.1]
### Changed
- Remove AnimationSchemaTools deprecation warning.

## [106.0.0]
### Fixed
- Fix OMPE-17490.

## [105.17.10]
### Fixed
- Fix OMPE-14440. Some rare case uninitialized scrubber

## [105.17.9]
### Fixed
- Fixed test dependence

## [105.17.8]
### Changed
- Reformat all source with repo format.

## [105.17.7]
### Added
- Added omni.usd.schema.anim to dependencies.

## [105.17.6]
### Fixed
- fixed dependence

## [105.17.5]
### Changed
- Enable skipped unit tests
- Ignore unused code from test coverage

## [105.17.4]
### Fixed
- Fixed OM-119450 that curve simplification menu entry in curve editor window was not functional

## [105.17.3]
### Changed
- Updated kit-sdk version

## [105.17.2] - 2023-11-27
### Changed
- Updated kit-sdk version

## [105.17.1] - 2023-09-19
### Changed
- OM-103155 Make Curve Editor time control widget visible by adding 5 frames border in the beginning and end

## [105.17.0] - 2023-09-18
### Added
- Multi-user time sync mode UI, include the presenter and the listner modes
-
## [105.16.2] - 2023-09-05
### Changed
- Use new curve node type name.

## [105.16.1] - 2023-08-31
### Changed
- Update version, Uses omni.anim.curve.core instead of omni.anim.curve.

## [105.16.0] - 2023-08-24
### Added
- Frame All and Frame Selected Icon back
### Changed
- Suppress the warning message for the release version
-
## [105.15.2] - 2023-04-28
### Fixed
- The timeline scrubber UI does not react to the time change event immediately
-
## [105.15.1] - 2023-04-18
### Fixed
- When the tangent type is auto add a new key will try to keep the original shape
-
## [105.15.0] - 2023-04-11
### Changed
- Work with the latest curve runtime which remove the animationData prim
### Added
- Pan and Zoom add some manipulation method same as the viewport
### Fixed
- remove the unnecessary import of omni.kit.property.usd.tests in the unit test
-
-
## [105.14.4] - 2023-03-13
### Changed
- Update to Python 3.10 and USD 22.11
-
## [105.14.3] - 2023-03-10
### Changed
- Update the Kit SDK and update the unit tests to accomodate the new omni.timeline extension


## [105.14.2] - 2023-02-28
### Changed
- Update the Kit SDK and update the unit tests
-
## [105.14.1] - 2023-01-21
### Changed
- An option button for simplify curve and animation preference context menus
- Re-arrange the toolbar buttons to match the design doc
-
## [105.14.0] - 2023-01-20
### Added
- Display the curve name instead of the raw attribute name
- Search the curve via the display name instead of the attribute name
- A new button to simplify the curve usually used when the keys are very dense, e.g. per frame keys
### Changed
- Refine the curve's cycle setting combobox UI
- Refine the per-curve tangent type preset UI
- Update the unit test golden image
### Fixed
- Auto fitting when the curve editor is first time toggled visible and the curve is selected
-
## [105.13.0] - 2022-12-12
### Added
- Add a curve search field in the toolbar
- Introduce the per-curve default tangent type
- Highlight the curve segment when you select both ends' keys
### Fixed
- A single Key's infinity type set/change
- Remove unnecessary warning when switching key's tangent type to Step
- Key picking area should not change the vertical display range
### Changed
- Some UI performance improvement
- Toolbar Icon update for many tangent types
- Remove timeline-related icon buttons from the toolbar
- A more readable curve name
- New Curve infinity toolbar widget

## [105.12.3] - 2022-10-28
### Added
- A new unit test case
### Fixed
- Remove the curve editor version number from the hotkey window
- Hotkey related error and warning logs
### Changed
- Moved a test case to animation runtime
- Removed some unnecessary log

## [105.12.2] - 2022-10-19
### Changed
- Update Kit SDK to 105
## [104.12.2] - 2022-10-12
### Fixed
- A toolbar icon issue at startup
- A crash issue when deleting the selected prim and select its curve key

## [104.12.1] - 2022-09-30
### Fixed
- A moving key error
- An error when the editor window's heigh value is small
-
### Changed
- When the first key is added the length of the timeline becomes longer with the frame all

## [104.12.0] - 2022-09-28
### Fixed
- Timeline node mode adding key to a non-existing curve issue
- Display keys according to Timeline node's own framerate
- Slider dragging issue when the slider is out of the window
- A key tangent issue when switching Linear type to Fixed type with an unbroken attribute
### Changed
- Do not always auto-framing
- Update the unit test format

### Added
- Important actions and hotkeys
- A map loading performance test

-
## [104.11.4] - 2022-09-19
### Changed
- Replace the selection commands
- Change some Move key commands logic
-
## [104.11.3] - 2022-09-10
### Fixed
- An initial UI button bug
-
## [104.11.2] - 2022-09-09
### Fixed
- The tangent type change's undo/redo issue
- Error when adding keys from script, to a prim without curves
- Keys won't move along the time(frame) axis when the TimeCodesPerSecond is changed
- Do not recognize the omni.anim.timeline node in some legacy cases
-
## [104.11.1] - 2022-09-02
### Fixed
- The tangent icon button selection indicator's size
-
## [104.11.0] - 2022-09-02
### Changed
- Fully support the new OG node based animation asset
- Switch to the new animation key format from runtime version 104.12.0
- Refactor the architecture of the tool and no longer talk to USD data directly
- Most of the operations are backed by the public commands offered by the animation curve runtime
### Changed
- Upgrade the Kit SDK to 88111
### Fixed
- A bug that newly added curves not shown in prim panel
## [104.10.1] - 2022-07-20
### Added
- More Unit tests
### Changed
- Upgrade the Kit SDK to 88111
### Fixed
- A bug that newly added curves not shown in prim panel

## [104.10.0] - 2022-06-30
### Added
- Middle mouse authoring key
### Fixed
- Zooming an empty curve without keys
## [104.9.2] - 2022-06-28
### Changed
- Switch the repo
- Refine the tangent calculation with an update schema
-
## [104.9.1] - 2022-06-21
### Fixed
- Remove a deprecated dependency
-
## [104.9.0] - 2022-06-15
### Added
- Post and Pre infinity type authoring
### Changed
- Next and Previous Key button behavior change same as the timeline now
- Update the command names along with the omni.anim.curve runtime
- It only works with omni.anim.curve 104.9.0 or later
-
## [104.7.9] - 2022-05-05
### Fixed
- Unit test on Create
- Correct x coordinate range when we frame keys
## [104.7.8] - 2022-03-18
### Changed
- Make the editor timeline more robust during frame selection
-
## [104.7.7] - 2022-03-15
### Fixed
- Crash during removing curve animation or removing an attribute
### Changed
- Some UI tooltip
## [104.7.6] - 2022-03-15
### Fixed
- Reduce the performance impact on animation playback
### Changed
- Some icons
## [104.7.5] - 2022-03-11
### Fixed
- Docking issue for all Apps like Create
- Update golden image for testing
## [104.7.4] - 2022-03-11
### Changed
- Fix for show_window startup setting

## [104.7.3] - 2022-03-10
### Changed
- Window hidden on startup
- Frame all and frame selected button's icon

## [104.7.2] - 2022-03-07

### Added
- Timeline node authoring,  adding curves and then start authoring
### Fixed
- Some unit test dependencies
- Remove unnecessary error messages under a special case of undo operation
### Changed
- Continuouly update the time when sliding the timeline, because the UI is not snapping to frames
-
## [104.7.1] - 2022-02-18
### Changed
- Hide the timeline slider when it is out of the canvas range
-
## [104.7.0] - 2022-02-17
### Added
- Display token-typed keys
### Changed
- Step-typed tangent is now hidden
### Fixed
- Improve the robustness of tracking the animated prim when the scene graph changes
- Error messages when moving overlapped keys
- Step-typed tangent switched to spline type when grouply rotated
- Remove useless debug messages
- A minor python import issue in the test
-
## [103.6.0] - 2022-01-30
### Added
- A welcome screen on the left prim panel
- A new Timeline Node mode to edit animation curve in the Timeline Node
- The new mode doesn't have time slider and some timeline-related buttons.
- The timeline range is detached from the global timeline.
- The begin/end time is read from the Timeline node not USD stage
- Clicking the play/stop/pause button has no effect in this mode
- Only one Timeline node prim can be editted at a time
- Able to add dynamic attribute/curve from a new button
- A better interop with the sequencer
### Changed
- Clean up some legacy code
### Fixed
- A step-typed tangent issue
- Better support for generic attribute e.g.color3f attribute

## [103.5.0] - 2021-12-20
### Changed
- Improved copy and paste key feature, users can paste a key even it is deleted
- Update the non-xformOp attribute keys' color scheme
- Improve the playback performance
- Upgrade omni.kit.widget.timeline to version 103.1.20
- The curve names on the left panel is sorted. xformOp curves always on the top
### Fixed
- A scrubber issue when upgrading the timeline widget
- Key selection undo/redo
### Added
- omni.anim.curve upgrade to 103.5.0
- Double click a curve segment to select all keys in the curve


## [103.3.1] - 2021-12-06
### Changed
- Unify the non-xformOp attribute's color scheme
- xformOp curves always shows on top of the left panel

## [103.3.0] - 2021-12-04
### Added
- Copy/Paste keys
- Curve Editor window resizable
### Changed
- Kit SDK upgrade to 68257
### Fixed
- Multi-layered support. Curve data is in the weak layer case
- A curve editor frame(not window) resize bug

## [103.2.3] - 2021-11-22
### Added
- Manually framing on selected keys

### Changed
- Kit SDK upgrade to 66172
### Fixed
- Big performance improvement on panning/zooming navigation
- Some potential assertion bugs
- Time scrubber not able to go to some odd numbered frames
- The same prim appears twice on the left prim panel
## [103.2.2] - 2021-11-09
### Added
- Vertical guidelines on the background of the curve canvas
- Visual clue for USD stage's start and end time with highlight background
### Fixed
- Tangent type setting not working issue
- revoke the registered notice an shutdown
### Changed
- Remove some obsolete code using timelineview


## [103.2.1] - 2021-11-03
### Added
- Horizontal lines on the background of the curve canvas
- Vertical ruler
### Fixed
- unit test code for Create.
- Tangent type regression bug
- A garbage collection issue
### Changed
- registered notice revoke method
- singleton object revoke method

## [103.2.0] - 2021-10-29
### Changed
- Big refactor on the curve navigation
- Remove the up/down/zoom in/zoom out icons replace them with mouse manipulation
- Upgrade the timeline widget version to 103.1.15
- Customize the timeline behavior when doing the zooming and panning
- Kit SDK upgrade to 61825
### Added
- Curves auto/manual fit to the rendering window
### Fixed
- Slow-down/crash the asset import process.
- Standardized vector-typed curve colors
- Some circular dependency issue


## [103.1.3] - 2021-09-16
### FIXED
- Curve Editor's menu typo bug

## [103.1.2] - 2021-09-16
### Changed
- Curve's color encoding refactoring
- Curve Editor's menu switched to Window/Animation submenu

## [103.1.1] - 2021-09-13
### Changed
- Update the code to support latest timeline widget version 102.1.11
- Curve Editor menu is under the Window menu now

### Fixed
- Some delete key issue

## [103.1.0] - 2021-09-10
### Changed
- Initial public version
- Kit SDK is 56906

## [102.0.2] - 2021-06-10
### Changed

## [102.0.1] - 2021-05-12
### Changed
- Update Kit SDK to 40726

## [101.0.1] - 2021-03-08
### Changed
- Updating Kit SDK to 31180

## [101.0.0] - 2021-01-30
### Changed
- Initial version

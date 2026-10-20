# Changelog

## [110.0.1] - 2026-09-23
### Deprecated
- Deprecated this extension as of Kit 110.4.1.

## [110.0.0] - 2025-12-15
### Changed
- Updated kit-sdk version

## [109.0.0] - 2025-09-18
### Changed
- Updated kit-sdk version

## [105.1.8]
### Changed
- Reformat all source with repo format.

## [105.1.7]
### Changed
- Updated kit-sdk version

## [105.1.6] - 2023-11-27
### Changed
- Updated kit-sdk version

## [105.1.5] - 2023-03-13
### Changed
- Update to Python 3.10 and USD 22.11
-
## [105.1.4] - 2022-10-19
### Changed
- Update Kit SDK to 105
-
## [104.1.4] - 2022-09-23
### Fixed
- Fix tests to pass on both Viewport backends.

## [103.1.3] - 2022-07-26
### Changed
- Changes added to support newer viewport API

## [103.1.2] - 2022-05-13
### Added
- Added testing to Focus Here feature

## [103.0.29] - 2021-12-8
### Changed
- Move to omni.kit.viewport_legacy

## [103.0.28] - 2021-7-14
### Changed
- Update Kit SDK to 49389
## [103.0.27] - 2021-06-16
### Changed
- Version update to match Update 103 Kit SDK

## [102.0.27] - 2021-06-15
### Changed
- Add feature flag

## [102.0.26] - 2021-06-02
### Changed
- Suppress the unnecessary warning output
- The Camera Animation menu is under Window now
- Start the Linux support

## [102.0.25] - 2021-05-12
### Changed
- Update Kit SDK to 40726

## [101.0.25] - 2021-04-30
### Changed
- Do not delete AnimationData prim after the last key is deleted.
- Rename the window from Camera Animation Tool to Camera Animation

## [101.0.24] - 2021-04-28
### Fixed
- Random cases where keys are not able to delete
- Minor fixes to suppress a notification in viewport because it could message infinitely in theory
- Fix a possible python crash when adding a key

## [101.0.23] - 2021-04-24
### Fixed
- Fixed the infinite log issue
- Fixed an issue that the UI manipulation won't be reflected
- Fixed a LockToViewport UI display issue

### Changed
- Upgrade TimelineView

## [101.0.22] - 2021-04-22
### Changed
- Remove the startup screen
- Remove the update key button.
- The Add Key button acts both for add and update key
- Add Lock to selection and Lock to viewport camera selection mode
- Right click to select a camera key
- Remove the manual Select Camera button
- Add the Create Camera from Current View button
- Add Key will also create an AnimationData prim for a camera prim if it is missing
- Delete the last key will automatically delete the AnimationData prim
- Paste Key will generate a new key at the time the scrubber points to
- Add notification messages as hints for incorrect operations

### Fixed
- Create a camera from the Kit menu will automatically create an AnimationData prim

## [101.0.21] - 2021-04-16
### Changed
- Add an auto camera prim switch mode, based on prim selection
- Camera Key color scheme is changed
- Single click to choose a camera key
- Double click to snap the scrubber to a key

## [101.0.20] - 2021-04-15
### Fixed
- Not able to delete key issue in the last build
- More fundamental timesample precision issue fixes
### Changed
- Add a drag bar on the left of each key for move and drag
- Change from single click to double click to choose a key
- Timeline scrubber snap to key also needs double click

## [101.0.19] - 2021-04-14
### Fixed
- Some fundamental precision issue
- Now it can work with non-integer keys though UI stick with integer keys
## [101.0.18] - 2021-04-14
### Fixed
- Camera not auto aligned with Sequencer timeline
- Strange keys pop up while moving the camera in sequencer
- The last phantom key not able to delete
- Camera animation that's newly created are not inspectable when Kit is first launched with a default level

## [101.0.17] - 2021-04-12
### Fixed
- Camera Key not editable when camera animation in sequencer
- Alleviate the hitchy when the scrubber hit a key
- cache the thumbnails correctly
- Fix a remove key issue when camera animation in sequencer, key values are no longer integers
### Changed
- Updating Kit SDK to 35614

## [101.0.16] - 2021-04-09
### Fixed
- Camera tool view react to the sequencer change
- Able to edit camera keys while camera in a sequence

## [101.0.15] - 2021-04-07
### Fixed
- Make moving key work with Sequencer.

## [101.0.14] - 2021-04-06
### Fixed
- OM-29656
- OM-29657
- OM-29764

## [101.0.13] - 2021-04-02
### Changed
- Add a feature to modify camera animation data which are processed by the sequencer
- Add Undo/Redo functionality for animation keys manipulations
- Key icon changes

## [101.0.12] - 2021-03-30
### Changed
- Change the curve tangent schema format to work correctly with the sequencer

## [101.0.11] - 2021-03-24
### Changed
- Add the scalable timeline widget
## [101.0.10] - 2021-03-16
### Changed
- Fix an async menu update bug
## [101.0.9] - 2021-03-15
### Changed
- Use the new menu API
## [101.0.8] - 2021-03-08
### Changed
- Updating Kit SDK to 31180
## [101.0.7] - 2020-02-27
### Fixed
- Bug fix - camera creation button does not work
- Bug fix - UI does not refresh on new stage open / camera deletion

## [101.0.6] - 2020-02-17
### Added
- support for camera parameters (focalLength, ...)
- schema change to support general attribute and animation binding

## [101.0.5] - 2020-02-16
### Added
- refactor for view related codes
- redesigned frame slider (WIP)
- support update existing keys by dragging views

## [101.0.4] - 2020-02-10
### Added
- support frame range that does not start at 0
- refactor frame range handling

## [101.0.3] - 2020-02-09
### Added
- added camera thumbnail support
- added icons/buttons for add,update,remove,copy,paste keys

## [101.0.2] - 2020-02-05
### Added
- remapping type added (easeIn, easeOut, easeInEaseOut, Linear)
- new icons for camera selection and creation
- support for matrix type (transform) usd attribute
- bezierSlerp is now the default interpolation type

## [101.0.1] - 2020-02-03
### Added
- more interpolation options added (linear, bezier, step, stepNext, easeInEaseOut)
- quaternion based interpolation added (linearSlerp, bezierSlerp)

## [101.0.0] - 2020-02-01
### Added
- Created 101.0.0 version with kitsdk 101.0 (build 26003)
- Basic key add/remove/update functionality
- Requires omni.anim.curve runtime to handle AnimationData usd schema
- Supports multiple interpolation type per each view

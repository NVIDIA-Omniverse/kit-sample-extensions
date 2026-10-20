# Changelog

## [110.0.1] - 2026-03-18
### Changed
- cherry pick from release/107.3

## [110.0.0] - 2025-12-15
### Changed
- Updated kit-sdk version

## [109.0.2] - 2025-11-25
### Fixed
- Fix menu refresh issue

## [109.0.1] - 2025-11-17
### Changed
- publish new version

## [109.0.0] - 2025-09-18
### Changed
- Updated kit-sdk version

## [108.0.3]
### Fixed
- Fix key node refresh issue

## [108.0.2]
### Changed
- Upgrade to Events 2.0

## [108.0.1]
### Changed
- Update menu logic to use omni.kit.menu.utils

## [108.0.0]
### Changed
- Upgraded the Kit SDK to 108
-
## [106.5.0]
### Changed
- Update to Kit SDK 107.

## [106.4.1]
### Fixed
- Fix unit test

## [106.4.0]
### Changed
- Upgrade Kit SDK to 106.4
-
## [106.0.0]
### Fixed
- OMPE-17498: Fixed unit test relation with OptionsButton

## [105.13.5]
### Changed
- Reformat all source with repo format.

## [105.13.4] - 2024-03-18
### Fixed
- Remove Container::clear during draw
- Reduce timeline pause during UI rebuild

## [105.13.3]
### Fixed
- OMPRW-851: Fixed Keyframe icon not Matching Accurate Frames Change Changing Starting Frame

## [105.13.2]
### Fixed
- OMPRW-692: Fixed keyframe slider

## [105.13.1]
### Changed
- OM-110314: Apply new options button and options menu

## [105.12.10]
### Changed
- Updated kit-sdk version

## [105.12.9] - 2023-11-27
### Changed
- Updated kit-sdk version

## [105.12.8] - 2023-10-19
### Fixed
- Fix errors when editing start time/end time with illegal value

## [105.12.7] - 2023-09-26
### Fixed
- Fix illegal frame range setting, start time cannot be greater than end time

## [105.12.6] - 2023-09-21
### Fixed
- Fix incorrectly clamps input frame range to positive values

## [105.12.5] - 2023-09-05
### Fixed
- Fix possible docker failure
- Fix errors when start live session.

## [105.12.4] - 2023-08-30
### Fixed
- Fix errors when start live session without timeline window actived.

## [105.12.3] - 2023-08-29
### Changed
- Uses omni.anim.curve.core instead of omni.anim.curve.

## [105.12.2] - 2023-08-28
### update
- Reset scrubber color when leave live session

## [105.12.1] - 2023-08-25
### update
- Updated timeline live session UI

## [105.12.0] - 2023-08-21
### Added
- Support timeline live session

## [105.11.16] - 2023-08-11
### Fixed
- fixed show end frame
- fixed scrubber position when mouse move quickly

## [105.11.15] - 2023-08-08
### Fixed
- remove deprecated settings

## [105.11.14] - 2023-07-11
### Fixed
- Update stage start/end time when the zoom value out of range

## [105.11.13] - 2023-06-20
### Changed
- Switch timeline Zoom API

## [105.11.12] - 2023-06-06
### Fixed
- Add tabBar triangle back
- Add get_FPS_list interface

## [105.11.11] - 2023-06-01
### Fixed
- Removed dependence of omni.kit.stage_templates in unit tests

## [105.11.10] - 2023-05-23
### Changed
- Cherry pick: add FixedTimeStepping in option menu

## [105.11.9] - 2023-05-18
### Changed
- Move 'ALT+S' hotkey to omni.anim.curve

## [105.11.8] - 2023-05-16
### Changed
- Cherry pick from release/105.0 again

## [105.11.7] - 2023-05-16
### Changed
- Cherry pick from release/105.0

## [105.11.6] - 2023-05-15
### Changed
- FPS comboBox support for "Custom" FPS

## [105.11.5] - 2023-04-17
### Changed
- Remove timeline dependency on preferences

## [105.11.4] - 2023-03-14
### Changed
- Move Checkmarks to left side of timeline option menu

## [105.11.3] - 2023-03-13
### Changed
- Update to Python 3.10 and USD 22.11

## [105.11.2] - 2023-03-07
### Fixed
- Fixed unreliable unit test, avoid fps zero issue

## [105.11.1] - 2023-02-09
### Changed
- Replace recorder icon, increase addkey icon size

## [105.11.0] - 2023-01-31
### Changed
- Update timeline window for Kit 105

## [105.10.6] - 2022-12-09
### Changed
- Cherry pick autokey on active camera fixing from 104.1

## [105.10.5] - 2022-11-16
### Changed
- Cherry pick from 104.1
- Add FixedTimeStepping in option menu

## [105.10.4] - 2022-10-19
### Changed
- Update Kit SDK to 105
## [104.10.4] - 2022-10-14
### Fixed
- OM-65677: Enabling Fabric Bundle and setting it to auto load crashes Create on the next start up

## [104.10.3] - 2022-10-14
### Changed
- Make play range editable

## [104.10.2] - 2022-10-10
### Added
- Support keyframe proxy.

## [104.10.1] - 2022-10-03
### Fixed
- Make legacy Viewport an optional dependency.

## [104.10.0] - 2022-09-29
### Changed
- re-implement autokey feature due to some functions not work for pushgraph

## [104.9.1] - 2022-09-14
### Changed
- increase test coverage

## [104.9.0] - 2022-09-02

### Added
- Switch FPS will dynamically switch key position and start/end time code
### Changed
- Switch to the new animation key format

## [104.8.1] - 2022-08-04
### Fixed
- Add None check

## [104.8.0] - 2022-07-18
### Fixed
- Support play in range

## [104.7.0] - 2022-06-30
### Added
- Middle Mouse Authoring
-
## [104.6.1] - 2022-06-28
### Changed
- Change the repo

## [104.6.0] - 2022-06-15
### Changed
- Update the animCurve commands
- It can only be used along with omni.anim.curve 104.9.0 or later
## [104.5.5] - 2022-05-30
### Changed
- merge from v103.5.18
- add add/delete/copy/paste key in popup window

## [104.5.4] - 2022-04-11
### Changed
- sync to v103.5.17

## [104.5.3] - 2022-03-15
### Changed
- merge from v103.5.8

## [104.5.2] - 2022-03-08
### Changed
- update version

## [103.5.4] - 2022-03-08
### Changed
- Improve keyframe range slider, disable drag single key frame
### Added
- Add option menu for toggle modifier shift/alt

## [103.5.3] - 2022-03-07
### Added
- An "Autokey all transform" toggle context menu to always autokey all transforms keys whenever any keyed value changes
## [103.5.2] - 2022-03-04

### Added
- An additional auto button state to indicate that the selected prim cannot do autokey
- A button to add all transform attribute keys
### Changed
- dock at the bottom of the window
### Fixed
- Fix key frames ranger slider issues



## [103.5.1] - 2022-02-08
### Changed
- Add setting "/exts/omni.anim.window.timeline/playinRange"
### Fixed
- Fix when startTimeCode and endTimeCode are invalid
- Fix time scrubber moving with mouse even it not pressed in the timeline bar area

## [103.5.0] - 2021-12-21
### Changed
- use same version as animation runtime
### Fixed
- Fix group undo for multiply keyframes moving

## [103.0.4] - 2021-12-20
### Fixed
- Fix bugs
### Changed
- support multiply prim keyframes

## [103.0.3] - 2021-12-8
### Changed
- Move to omni.kit.viewport_legacy

## [103.0.2] - 2021-12-08
### Changed
- Move to omni.kit.viewport_legacy

## [103.0.1] - 2021-11-25
### Added
- Initial release of Timeline into the registry

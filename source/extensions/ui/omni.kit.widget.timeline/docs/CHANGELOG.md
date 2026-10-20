# Changelog

## [107.0.4] - 2026-05-27
### Fixed
- Raise a clear `ValueError` (naming the offending `event_type`) in `TimelineValueModel.__init__` when the requested `event_type` is not in the timeline dispatch table, instead of later crashing with `TypeError: 'NoneType' object is not callable` when the missing getter is invoked.
- Atomically publish the lazy `_timeline` / `_setters` / `_getters` cache in `_get_timeline()` (build into local variables first, then assign all three module-level globals at the end of the success path) so concurrent callers cannot observe a half-initialized cache.

## [107.0.3] - 2026-05-26
### Fixed
- Lazily resolve `omni.timeline` interface in `timeline_value_model` so the extension import no longer fails with `AttributeError: 'NoneType' object has no attribute 'set_start_time'` when the timeline plugin is not yet loaded at module-import time.

## [107.0.2] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

# [107.0.1] - 2025-02-07
- Add missing extension class.

# [107.0.0] - 2025-01-23
- OMPE-27798: update public api.
- OMPE-30261: Increase test coverage.

# [104.0.3] - 2022-11-10
- Moved dependency on omni.kit.test to tests section
# [104.0.2] - 2022-11-03
- Updated to release Kit version

# [104.0.1] - 2022-10-25
- Updated for Kit 104
# [103.5.1] - 2022-08-05
- Updated Kit version to 103.5
- More tests integrated to master branch

# [103.1.28] - 2022-08-05
- Updated Kit version to 103.5

## [103.1.27] - 2022-07-04
* Added more testing, fixed a workaround for the ETM system to show actual coverage more accurately

## [103.1.26] = 2022-05-31
* Fixed a bug in a function where a None view could end up being passed.  Order of operations problem

## [103.1.25] - 2022-04-25
* Removed dependency on window for testing.  This was causing a problem in Create AT.

## [103.1.24] - 2022-03-14
* Uncommented out a line which is a speculative fix for Curve Editor
* Added some tests.  More to come!

## [103.1.23] - 2022-03-01
* Bumping rev because of sec
## [103.1.18] - 2022-02-11

* Bump kit-sdk to avoid version warnings on load.

## [103.1.17] - 2021-11-17
* Added function 'set_scrubber_disable_line' to allow users to disable the scrubber line.  Calling this function with the parameter "True" will cause the line to no longer move the scrubber.

## [103.1.16] - 2021-11-03
* Update to stop confusion of versions between 102 and 103 version.

## [103.1.15] - 2021-10-11
* Many changes made to scrolling features, and API has changed "scroll_x" to "set_x" instead to homogenize the names.
* Added some support to scrolling the timeline out of bounds, but more to be added.

## [103.1.14] - 2021-09-27
* Examples updated for Curve Editor

## [102.1.13] - 2021-09-22
* Found and fixed a bug which was preventing the calling of an on_drop function in Sequencer
## [102.1.12] - 2021-09-22
* Fixed some smoothing issues with the scrubber, improving the feel when draggin the scrubber around
* In Kit 103, you can now click on the timeline and then immediately drag the scrubber

## [102.1.1] - 2021-06-30

### Added
* Put timeline in new home.
* Fixed serveral issues with range values and clip placement.

## [102.1.0] - 2021-06-21
* Renamed to omni.kit.widget.window
* Various functions, modules, and configs fixed to align to new naming convention
## [101.0.9] - 2021-05-13
* Fixed a linux pathing issue (/ vs \)
* Further fixes on timeline position accuracy
## [101.0.8] - 2021-04-23
* Fixed incorrect style entry

## [101.0.7] - 2021-04-23
* New functionality in style
## [101.0.6] - 2021-04-12
* Added functionality for floating-point translations

## [101.0.5] - 2021-04-12
* Additional code cleanup and some minor visual fixes
* Fixed a bug that was causing timeline elements to be "off" their correct locations.  Clients may need to review any code that calls timeline_view.transform_xxxx
* Fixed a missing style element for the background of the timeline
* Some code cleanup -- Continuing effort to cleanup code and comment where needed.

## [101.0.3] - 2021-04-02

### Changed
* Fixed bug which allowed you to move past left end of timeline
* Removed dependency on omni.usd - this was just a vestigial tail

## [101.0.2] - 2021-03-30

### Changed
* Added new styles as defaults
* Changed the scrubber to resizeable icon that changes as the number of frames in it changes
* Fixed issues in the range for large numbers

## [101.0.1] - 2021-03-26
### Added
- Initial release of Timeline into the registry
### Changed

### Removed

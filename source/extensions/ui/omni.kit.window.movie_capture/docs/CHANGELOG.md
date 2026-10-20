# Changelog


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [3.0.12] - 2026-10-20
### Fixed
- OMPE-112504: `default_render_preset` accepts a comma-separated priority list; the first mode the active
  engine supports is used. The default is now `"RaytracedLighting, RealTimePathTracing"`, so it resolves on ovrtx.

## [3.0.11] - 2026-10-13
### Changed
- Kit 111 tests: `test_capture_with_render_product_all_modes` skips RTX-Minimal and logs the reason as a warning. Since `omni.kit.capture.viewport`
  added `CaptureRenderPreset.RTX_MINIMAL`, the window offers that mode, and a render-product capture in it writes no image (the
  renderer provides no tonemap input for `LdrColor`). The other render modes are still captured and checked.

## [3.0.10] - 2026-07-07
### Fixed
- OMPE-68149: Hide the inoperative wait-for-render-resolve and settle latency settings for RTX Real-Time 2.0.

## [3.0.9] - 2026-06-16
### Fixed
- OMPE-97878: Exclude the benign RTX-Minimal "Failed to add HDR to LDR Tonemap" renderer error from test stdout fail patterns.

## [3.0.8] - 2026-06-12
### Fixed
- OMPE-97878: `test_capture_with_render_product_all_modes` now expects only `LdrColor`/`HdrColor` for the RTX-Minimal preset, which doesn't produce the path-traced `Pt*` AOVs.

## [3.0.7] - 2026-06-11
### Added
- OMPE-93667: Add tests for MP4 OVC capture (unit coverage of the URI-aware paths plus an end-to-end DGXC capture).

## [3.0.6] - 2026-06-11
### Fixed
- OMPE-79931 (NVBug 5856171): `OutputSettingsWidget.destroy()` now releases every carb settings observer, fixing a SIGABRT in libcarb.dictionary during test teardown.

## [3.0.5] - 2026-06-09
### Fixed
- OMPE-86263: Add the "RTX - Minimal" renderer to the Render Preset combo box in Movie Capture. The new entry is gated on the carb setting `/persistent/rtx/modes/minimal/enabled` to match the main viewport menubar, and is only shown when `omni.kit.capture.viewport.CaptureRenderPreset` defines the `RTX_MINIMAL` preset (added in `omni.kit.capture.viewport` 2.11.0), so the extension stays compatible with older builds.

## [3.0.4] - 2026-06-04
### Added
- OMPE-95830: Add a dedicated golden image (`mc_win_ovc.png`) for the Movie Capture window startup test on DGXC/OVC, selected when `ETM_DGXC_ACTIVE` is set.

## [3.0.3] - 2026-05-22
### Added
- OMPE-52319: MP4 capture is now available in OVC/DGXC mode
- OMPE-52319: Capture Sequence and Capture Current Frame buttons are now visible in OVC mode
- OMPE-52319: Disk space pre-flight check before starting a remote capture; shows a dialog with Cancel, Clear Temp & Retry, and Continue Anyway options
- OMPE-52319: Output path picker and MP4 overwrite check are now URI-aware (`omni.client` used for remote paths)

## [3.0.2] - 2026-04-14
### Fixed
- OMPE-79931: Fix test hang caused by rendering deadlock during render product capture across multiple render modes. Enable async rendering for tests, add timeout to wait_for_capture_done, and increase settling frames between render mode switches.

## [3.0.1] - 2026-04-14
### Changed
- OMPE-88118: Reduce Kit target to 109.0 for backward compatibility.

## [3.0.0] - 2026-04-09
### Changed
- OMPE-88118: Video Codec 13.0 and 590+ driver support.

## [2.8.2] - 2026-04-01
### Changed
- OMPE-87639: Update test stage file to align AOV name

## [2.8.1] - 2026-03-30
### Changed
- OMPE-87639: Use current render mode as default render preset in test to match golden

## [2.8.0] - 2026-01-30
### Changed
- OMPE-41175: Enable "Use render product to capture" for all render modes

## [2.7.4] - 2025-12-03
### Fixed
- OMPE-71614: Track active camera after capture is done

## [2.7.3] - 2025-09-23
### Fixed
- OMPE-64553: Update test for DGXC

## [2.7.2] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [2.7.1] - 2025-08-22
### Changed
- OMPE-59716: Exclude expected error messages when capture with new render product

## [2.7.0] - 2025-08-20
### Changed
- Update to event 2.0

## [2.6.3] - 2025-08-15
### Fixed
- Sometime test failed with no render product selected in test_set_ui_values_4_render_product_and_ext_settings

## [2.6.2] - 2025-08-13
### Fixed
- Test failure with kit 108.1

## [2.6.1] - 2025-08-08
### Fixed
- Issue with capturing RenderProducts without a camera

## [2.6.0] - 2025-06-12
### Changed
- Remove external extensions dependency for render product capture if the version of omni.kit.capture.viewport is greater than 1.8.0

## [2.5.6] - 2025-05-08
### Changed
- Query renderer and mode from Viewport before global settings

## [2.5.5] - 2025-05-08
### Changed
- Updated documentation with AI agent.

## [2.5.4] - 2025-05-02
### Changed
- Removing deprecated dependency.

## [2.5.3] - 2025-03-23
### Changed
- OMPE-35647: Do not capture and show error message if no render preset selected

## [2.5.2] - 2025-03-18
### Changes
- OMPE-40327: Add omni.graph as dependency of AOV capture
- Change some warning messages to info messages
- Make the position of render product enable result dialog to be centered

## [2.5.1] - 2025-03-17
### Changed
- OMPE-39994: Fix the menu path to be Window/Rendering/Movie Capture

## [2.5.0] - 2025-03-10
### Added
- Add "Real Time 2.0" as a render preset
- Add RenderModel to manager the render presets

## [2.4.4] - 2025-03-06
### Added
- Update public api

## [2.4.3] - 2025-02-19
## Changed
- Replace `omni.kit.window.viewport` with `omni.kit.viewport.window` in test dependencies

## [2.4.2] - 2024-08-14
### Changed
- Add render product capture needed omni.graph extensions as optional dependencies so they can be included in release builds

## [2.4.1] - 2024-03-07
### Changed
- Updated the dependency to the rtx renderer settings window to optional

## [2.4.0] - 2024-02-12
### Added
- Expose the per-frame time limit capture option for Farm render jobs
- Expose the per-frame time to wait for render resolve option for RT capture

## [2.3.16] - 2024-01-16
### Changed
- Restore testcases and adjust the timeout of tests to workaround the long startup that appears randomly

## [2.3.15] - 2024-01-12
### Fixed
- Fix the ETM test failure caused by using omni.client.ListEntry

## [2.3.14] - 2023-11-27
### Changed
- Disable the movie capture restart capture test in ETM tests while we're invesgiting into its failure on certain driver

## [2.3.13] - 2023-11-22
### Fixed
- Improve the movie capture restart capture test's stability

## [2.3.12] - 2023-11-09
### Added
- Move the movie capture restart capture test to here from rtx tests

## [2.3.11] - 2023-10-24
### Fixed
- Fix the test failures in ETM tests against 105.2

## [2.3.10] - 2023-10-13
### Added
- Increased test coverage by adding more tests

## [2.3.9] - 2023-10-11
### Added
- Increased test code coverage extension.

## [2.3.8] - 2023-10-06
### Changed
- Update the description text and tooltip of the application level capture option

## [2.3.7] - 2023-09-28
### Added
- Add tooltips to some capture options to bring better user experience
### Changed
- Remove movie type playlist as its supporting extension has been deprecated
### Fixed
- Fix the Movie Capture menu item status not correct issue

## [2.3.6] - 2023-09-22
### Added
- expose the texture streaming memory budget in Farm rendering settings
### Changed
- update the number inputs in Farm rendering settings to give a unified input experience and tune the window width to show them more properly

## [2.3.5] - 2023-09-22
### Changed
- OM-104880 - Removed the omni.kit.sliderbar extension and removed the code to force enable it.

## [2.3.4] - 2023-08-29
### Changed
- Hide the folder open button for OVC environment as it is not meaningful
### Fixed
- Fix the issue that the folder open button doesn't work on Linux

## [2.3.3] - 2023-08-22
### Added
- Increased code coverage for Farm submission features, including checks for shader cache generation (if requested).

## [2.3.2] - 2023-08-22
### Added
- Increased code coverage for Farm submission features, including checks for "Advanced Rendering Features" and S3 uploads.

## [2.3.1] - 2023-08-21
### Fixed
- When submitting a USD stage with checkpoint number to Farm, use its flat file URL so that the render job can find it

## [2.3.0] - 2023-08-20
### Added
- When submitting a USD Stage for rendering on Omniverse Farm, include the checkpoint ID of the file to render in order to ensure results are consistent when re-submitting a task multiple times over time.

## [2.2.15] - 2023-08-15
### Changed
- Read default farm queue and job type for ovc deployment from settings service.
- Add `validate_usd` setting to toggle sanity check of usd file.

## [2.2.14] - 2023-08-15
### Changed
- Tune the text on the unsaved changes prompt and unify the title format of the prompts.

## [2.2.13] - 2023-08-14
### Changed
- Allow users to submit a render job with unsaved USD file to Farm if they really want to.

## [2.2.12] - 2023-08-10
### Changed
- Disables movie capture during live session.

## [2.2.11] - 2023-08-02
### Fixed
- Adds "sequencer camera" to the "cameras" menu and selects it when "sequencer camera sync" is on.

## [2.2.10] - 2023-07-24
### Added
- Added notification prompting Users to save any pending changes to the USD Stage prior to submitting a rendering task to Omniverse Farm.

## [2.2.9] - 2023-07-17
### Fixed
- Unify the name for the `farm_job_name` setting

## [2.2.8] - 2023-07-13
### Changed
- Modify the logic to support ovc mode and check if videoencoding is available.

## [2.2.7] - 2023-07-13
### Changed
- Disable .mp4 encoding type if omni.videoencoding is not available.

## [2.2.6] - 2023-07-11
### Fixed
- Fix the test failure caused by 0 FPS can be sent to movie capture from timeline in some tests

## [2.2.5] - 2023-07-10
### Fixed
- Add more guards before accessing the timeline extension API to avoid the failure of the ov-create auto test

## [2.2.4] - 2023-07-10
### Changed
- Changed the user name of render jobs sent to Farm in OVC mode to be the logged-in user name of USD Composer so that we can identify it's from whom

## [2.2.3] - 2023-07-04
### Added
- Added support to OVC by adjusting the UI to be suitable for OVC environment.

## [2.2.2] - 2023-06-20
### Changed
- Camera option now only tracks the active camera in viewport if users don't change selection in the camera dropdown, or choose to keep using the current camera

## [2.2.1] - 2023-06-19
### Changed
- Frame Rate option now only keeps in sync with the timeline window's FPS dropdownlist if users don't change selection, or choose to keep using the current fps

## [2.2.0] - 2023-06-13
### Changed
- Frame Rate option now keeps in sync with the timeline window's FPS dropdown list, and the value will be used for both animation and movie capture
- File options window now will show options for the selected output file type
### Added
- Added a new application mode capture, which will hide application's UI during capture, to help the capture of ui.scene elements
- Added support to set mp4 encoding settings

## [2.1.12] - 2023-03-23
### Changed
- Changed HDR output option to True by default
- Lower the file options message to info level

## [2.1.11] - 2023-03-20
### Changed
- Fix test failures with python 3.10

## [2.1.10] - 2023-03-06
### Added
- Added UI components to enable optional generation of shader cache for remote rendering jobs (actual generation still pending task availability).

## [2.1.9] - 2023-02-24
### Fixed
- Fixed the issue that the last batch is not included when the frames can be evenly distributed to the batches

## [2.1.8] - 2023-02-03
### Fixed
- Fixed the render product related errors at ui layout restore

## [2.1.7] - 2023-01-06
### Added
- Added identifiers for UI widgets so that we can better locate them in tests

## [2.1.6] - 2022-12-06
### Fixed
- Updated the Farm Queue management URL to be the /dashboard page if it's supported, otherwise still direct to the /ui page

## [2.1.5] - 2022-12-05
### Added
- Added two sections for known issues and limitations for movie captures in doc, so that users can have more ideas about the most frequently asked questions about movie capture

## [2.1.4] - 2022-10-20
### Fixed
- Fixed the hot reload failure issue in Create release build

## [2.1.3] - 2022-10-13
### Fixed
- Fixed the collect jobs have no priority submitted issue
- Removed archive jobs submission

## [2.1.2] - 2022-09-30
### Fxied
- Fix the S3 options visibility not updated as expected issue

## [2.1.1] - 2022-09-26
### Fxied
- Fix the render product capture related warning prompted even render product capture is not enabled any more

## [2.1.0] - 2022-08-30
### Added
- Expose exr compression method setting and move all file option settings into the File Options window

## [2.0.6] - 2022-08-23
### Fixed
- Improve the way of redistributing frames into batches

## [2.0.5] - 2022-07-26
### Changed
- Update default subframes per frame of Path Trace to 64, and Iray to 32
- Let the subframes per frame input remember PT and Iray's input values respectively so that it shows different values for PT and Iray

## [2.0.4] - 2022-07-20
### Fixed
- Fixed metadata storage of Movie Capture settings within the USD Stage's custom metadata.

## [2.0.3] - 2022-07-19
### Fixed
- Fix for archival job submissions

## [2.0.2] - 2022-07-17
### Changed
- Updated URL to the Omniverse Farm Queue online documentation.

## [2.0.1] - 2022-07-07
### Changed
- Fixed test time out issue

## [2.0.0] - 2022-06-15
### Added
- Added support for advanced rendering features, based on support from the selected Farm Queue.
- Added `priority` field for Farm tasks.
- Added option to add extensions that need to be enabled for Farm jobs.
- Added option to add registries that need to be enabled for Farm jobs.
### Fixed
- Fix frame range calculations.

## [1.2.16] - 2022-06-16
### Changed
- Update to run on legacy or new Viewport

## [1.2.15] - 2022-06-15
### Added
- Register callback function to ui.Workspace to let the Workspace to show/hide main window in this extension

## [1.2.14] - 2022-06-09
### Added
- Added extension level setting for all the available fps options, also added 50 FPS into the list

## [1.2.13] - 2022-06-05
### Changed
- Change capture button layout when window width changed for View

## [1.2.12] - 2022-05-27
### Added
- Added extension level default value setting for IRay iterations

## [1.2.11] - 2022-05-24
### Added
- Added motion blur support for Iray capture

## [1.2.10] - 2022-05-12
### Fixed
- Promote "Settle latency" to all modes
-   -1 disables (no wait), 0 is a default chosen by capture backend, and > 0 explicitly sets the frames to wait

## [1.2.9] - 2022-05-03
### Fixed
- More fixes to release ui.Image objects to avoid error messages at quitting kit

## [1.2.8] - 2022-04-28
### Fixed
- Explicitly release ui.Image objects to avoid error messages at quitting kit

## [1.2.7] - 2022-03-30
### Changed
- Update repo_build and repo_licensing

## [1.2.6] - 2022-03-19
### Changed
- Update renderer terms, now use RTX-Interactive for PT and RTX-Accurate for Iray

## [1.2.5] - 2022-03-12
### Changed
- Update movie capture's icon and preview images

## [1.2.4] - 2022-03-12
### Fixed
- Filter out temp render products created in session layer during render product capture

## [1.2.3] - 2022-03-11
### Changed
- Improve the UI support for AOV capture with a render product.

## [1.2.2] - 2022-02-13
### Changed
- Changed the style of motion blur checkbox to make it look the same to other checkboxes

## [1.2.1] - 2022-02-09
### Changed
- Changed Iray to RTX Ground Truth

## [1.2.0] - 2022-02-07
### Changed
- Changed the style of checkboxes to make them look the same to the Render Setting Window's checkboxes

## [1.1.9] - 2022-01-29
### Added
- Add enable status check of AOV support required extensions; if they're not eabled then disable Render Product input and prompt users with its tooltip.

## [1.1.8] - 2022-01-24
### Added
- Add a check before starting capture to make sure if RenderProduct set then output file type needs to be .exr.

## [1.1.7] - 2022-01-20
### Added
- Support multiple buffer capture via a RenderProduct Prim

## [1.1.6] - 2021-12-28
### Added
- Added support to save sunstudy settings into usd stage if sunstudy movie type is enabled

## [1.1.5] - 2021-12-27
### Changed
- Changed to use omni.kit.capture.viewport instead of current omni.kit.capture. They're the same in bahavior for now and future development will be on omni.kit.capture.viewport.

## [1.1.4] - 2021-12-09
### Added
- Added support to shaded/debug material render styles

## [1.1.3] - 2021-12-07
### Changed
- Update sunstudy to use the new sunstudy in omni.kit.environment.sunstudy

## [1.1.2] - 2021-12-07
### Changed
- Updated the use of omni.kit.viewport to omni.kit.viewport_legacy

## [1.1.1] - 2021-11-26
### Changed
- Changed sunstudy Time Duration option to Movie Length to make it clearer
### Added
- Merged recent sunstudy fixes in kit master's movie maker to this repo

## [1.1.0] - 2021-11-11
### Added
- Add recent fixes in the original movie capture extension, including the file picker folder name fix, the motion blur frame shutter settings fix, and the HDR setting for .exr format fix
- Add new auto tests to check movie maker window can be opened
- Add support to save UI settings into usd stage

## [1.0.0] - 2021-09-01
### Changed
- Move the movie capture extension out from kit repo to kit-windows and merge the diverged implementations in kit master and release/102 branches together.
- Rename it from omni.kit.window.movie_maker to omni.kit.window.movie_capture.

## [0.5.7] - 2021-08-27
### Fixed
- Fixed the render settings cog can't open corresponding render setting window issue

## [0.5.6] - 2021-08-18
### Fixed
- Fixed an issue where batch sizes could be larger than requested or had missing frames.

## [0.5.5] - 2021-08-04
### Changed
- Disabled the "Submit to Queue" button if the desired output file format is MP4.
- Changed naming to refer to distributed capabilities as "Omniverse Queue" and "Omniverse Agent".
### Added
- Added the `queue_management_endpoint_prefix` setting to allow specifying the management endpoint URL of Omniverse Queue.

## [0.5.4] - 2021-07-26
### Fixed
- Fixed an issue where the "number" inputs could accept unsupported values.

## [0.5.3] - 2021-07-26
### Changed
- Made the default window size wider.
- Allowed Users to learn more about the capabilities of Omniverse Queue, in case no Queue can be reached.

## [0.5.2] - 2021-07-16
### Added
- Added UI feedback to User when submitting a render task to Omniverse Queue
- Added ability to open the Omniverse Queue Dashboard in a browser window, provided the selected Queue instance is reachable
- Added confirmation prompt when sending a task job to Queue

## [0.5.1] - 2021-06-23
### Added
- Fixed farm job name and made it configurable via the settings to allow users to override the job type.

## [0.5.0] - 2021-06-23
### Added
- Added UI option to submit to Omniverse Queue instances

## [0.4.9] - 2021-05-24
### Added
- Added UI option to turn path trace motion blur on and off during capture
### Fixed
- Fixed the error message coming out when setting a server path as the output folder by only showing local dirs in the file picker

## [0.4.8] - 2021-05-20
### Added
- Added UI option to set settle latency for capture in RTX real time mode

## [0.4.7] - 2021-05-11
### Added
- Add the overwrite existing frames option to replace the skip existing frames option, and move it to the output options section
- Add message box to ask users' confirmation if image frames or video could be overwritten
### Fixed
- Fix the issue that render mode dropdown selection is reset to what's in the viewport after capture, now it will keep the selection set for capture

## [0.4.6] - 2021-04-29
### Added
- Add new movie type sunstudy if the sunstudy window extension gets enabled

## [0.4.5] - 2021-04-28
### Added
- Add path trace samples per pixel setting for Iray mode captures

## [0.4.4] - 2021-04-15
### Fixed
- Fix the issue that it can't scroll down to the bottom if the window size is not big enough

## [0.4.3] - 2021-04-10
### Added
- Add UI for skipping existing frames

## [0.4.2] - 2021-04-02
### Added
- Add UI for preroll frames

## [0.4.1] - 2021-03-19
### Fixed
- Movie capture window now knows active renderer is set to iray and can update accordingly
### Changes
- Add get_instance interface so that users can get the extension instance to launch the movie capture window in their scripts

## [0.4.0] - 2021-03-15
### Added
- Expose caption options as extension settings so that users can set desired values in their scripts
- Focus the render setting window after showing it
### Fixed
- Update the render setting window's set render api to use its latest name

## [0.3.4] - 2021-03-01
### Fixed
- Make the meaning of samples per pixel clearer to users

## [0.3.3] - 2021-02-23
### Fixed
- Fixed the issue that if the open folder button is clicked twice then the file picker dialog will show overlapped files and folders

## [0.3.2] - 2021-02-10
### Changes
- Updated StyleUI handling

## [0.3.1] - 2021-02-07
### Added
- Show what custom aspect ratio is when users don't want the default ratios
### Fixed
- Make sure the path tracing settings, like subframes, shutter open and close, work for path tracing mode only
- Fixed the simulation speed is much faster in captured movie issue
- Fixed the jumping numbers issue when mouse moves in and out number input fields

## [0.3.0] - 2020-12-03
### Added
- Added support to capture in IRay
### Fixed
- Fixed the open output location icon
### Changed
- Changed default subframes per frame value to 5

## [0.2.1] - 2020-11-23
### Changed
- Updated to use new FilePicker

## [0.2.0] - 2020-10-15
### Changed
- Refactor to extract the various widgets and allow them to be used in other extensions

## [0.1.5] - 2020-10-14
### Fixed
- Rename the new movie maker to Movie Capture and the old movie capture tool to Movie Capture Old
- Move menu location from under Window to Rendering

## [0.1.4] - 2020-10-12
### Added
- Show path trace settings if path trace is selected in the render preset dropdown, otherwise hide it
- Split the Capture button's functionality into two more specific ones: Capture Sequence and Current Current Frame

## [0.1.3] - 2020-10-08
### Fixed
- Use the new settings interface to fix the settings interface deprecated warning
- Fix the reference to omni.kit.capture extension errors at quiting

## [0.1.2] - 2020-10-07
### Fixed
- Fix for file padding

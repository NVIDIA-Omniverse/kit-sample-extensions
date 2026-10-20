# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.0] - 2024-11-29
### Added
- Update kit sdk to 107.

## [0.11.5] - 2023-09-25
### Added
- Added the handling of texture streaming memory budget in render settings

## [0.11.4] - 2023-07-25
### Fixed
- Fixed the render job failure when capture option capture_every_nth_frame is greater than 1

## [0.11.3] - 2023-07-21
### Fixed
- Fixed a bug potentially resulting in the `flush_frame_timeout` parameter not respecting its intended bounds.

## [0.11.2] - 2023-07-18
### Changed
- Add logic to notify tracker from `FileManager` when all tasks are complete.

## [0.11.1] - 2023-02-28
### Changed
- Update unit tests to use `omni.kit.test.AsyncTestCase` class.

## [0.11.0] - 2022-07-20
### Changed
- add `error_on_missing_upload_frames` parameter on `/run` endpoint to raise an exception on missing upload frames.
- add `flush_frame_timeout` setting, gives renderer some time to write out all the frames.
- add `finalize_frame_sync_timeout` setting, timeout for uploading any final missing frames.
- add `capture_setting_settle_delay` setting, adds a delay in seconds, after creating omni.kit.capture options object.

## [0.10.0] - 2022-03-04
### Changed
- Improved uploading of rendered frames to avoid missing frames.

## [0.9.0] - 2022-03-01
### Changed
- Check frames for changes after they have been written. AOVs will modify the written frames a few times before they are stored.

## [0.8.3] - 2022-02-15
### Fixed
- Fix waiting logic and add additional logging.

## [0.8.2] - 2022-02-15
### Fixed
- Provide additional time to complete upload of frames.

## [0.8.1] - 2022-01-30
### Fixed
- Updated several old imports of omni.kit.capture instead of omni.kit.capture.viewport.

## [0.8.0] - 2022-01-29
### Changed
- Update to using omni.kit.capture.viewport.
- Add metrics for average frame, subframe and iteration times.
- Add time remaining to progress facility.

## [0.7.2] - 2022-01-26
### Fixed
- Fix to adapt to new omni.usd API.

## [0.7.1] - 2022-01-25
### Fixed
- Fix duplicate GPU metric name when using multiple GPUs.

## [0.7.0] - 2022-01-16
### Changed
- Add filesize threshold for image output.
- Add metrics to track GPU and memory stats.
- Add additional logging to provide progress on render samples.
- Add support for snapshotting frames during rendering.

## [0.6.5] - 2022-01-10
### Changed
- Fix default async loading for commandline render script.
- Fix only exit when finished rendering.

## [0.6.4] - 2021-11-08
### Changed
- Fix bug where success is always false.

## [0.6.3] - 2021-11-07
### Changed
- Fix bug where stages failing to open would not error out task. Follow up bug in Kit: #OM-40649.

## [0.6.2] - 2021-10-23
### Changed
- Updated iconography of Extension to match Omniverse Farm branding.

## [0.6.1] - 2021-10-22
### Fixed
- Missing keyword args for asyncio.wait_for.

## [0.6.0] - 2021-10-21
### Added
- Added support to append task_id to output folder.
- Added zip functionality to upload back all frames to S3 as a zip.

## [0.5.1] - 2021-10-19
### Fixed
- Fixed and improved logic regarding stage and asset loading.

## [0.5.0] - 2021-10-17
### Added
- Added basic support for S3 upload.
- Added setting to override root of temporary directory

## [0.4.6] - 2021-10-08
### Fixed
- Fixed missing function call which caused an error message to never be printed.

## [0.4.5] - 2021-09-22
### Changed
- Reduce stagger interval from 60 to 5 seconds.

## [0.4.4] - 2021-07-24
### Changed
- Changed `documentation` of Prometheus metrics gathered during rendering.

## [0.4.3] - 2021-07-23
### Changed
- Changed `documentation` and `unit` labels of Prometheus metrics gathered during rendering.

## [0.4.2] - 2021-07-03
### Added
- Added task progress reporting.

## [0.4.1] - 2021-06-24
- Fix to support omni.kit.capture 4.x

## [0.4.0] - 2021-04-22
- Stagger the start of the rendering to handle multiple agents running on the same host.
- Additional work for metrics collection
- Raise exceptions when Stage failed to load

## [0.3.2] - 2021-03-23
- Fix metrics collection.

## [0.3.1] - 2021-03-23
- Fix metrics collection.

## [0.3.0] - 2021-02-14
- Add additional metrics.

## [0.2.6] - 2021-02-11
- Further fixes to give the renderer time to write out the frames.

## [0.2.5] - 2021-02-11
- Fix to make sure final frames are copied.

## [0.2.4] - 2021-02-05
- Workaround to handle async loading hanging occasionally.

## [0.2.3] - 2021-02-02
- Fix issues with ASSETS_LOADED events not being received.

## [0.2.1] - 2021-02-01
- Update Teamcity auto publish script.

## [0.2.0] - 2021-02-01
- Handle the new render service endpoint spec.

## [0.1.0] - 2021-01-30
- Initial version.
- Automated Teamcity publishing.

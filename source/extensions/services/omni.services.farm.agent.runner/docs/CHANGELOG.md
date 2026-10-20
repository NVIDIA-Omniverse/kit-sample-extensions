# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.4] - 2026-08-13
### Fixed
- OMPE-103669: Accept absolute USD paths in expected Farm runner test errors.

## [0.7.3] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [0.7.2] - 2024-04-12
### Updated
- Improve agent behaviour when no GPU is present.

## [0.7.1] - 2023-10-19
### Updated
- Moved telemetry handling to the controller to centralize the functionality

## [0.7.0] - 2023-10-05
### Added
- Added telemetry.
- Can be enabled/disabled using this setting: structuredLog/enable=true

## [0.6.7] - 2023-09-21
### Updated
- Fix a toml extension parsing error.

## [0.6.6] - 2023-09-21
### Updated
- Appropriate exit code on failure to post_quit() call.

## [0.6.5] - 2023-08-21
### Updated
- raise exception when unable to reach controller.
- Add test case to cover the failures

## [0.6.4] - 2023-08-17
### Updated
- Add omni.rtx.shadercache.vulkan dependency to unit tests.

## [0.6.3] - 2023-04-03
### Updated
- Change Test class to `omni.kit.test.AsyncTestCase`

## [0.6.2] - 2022-03-14
### Fixed
- Move task shutdown to outer loop to avoid the application not shutting down if there is an error in the error handling.
- Remove exception logging on retries as there might be no exception raised.

## [0.6.1] - 2022-02-15
### Changed
- Make sure the application always shutsdown at the end of a task.

## [0.6.0] - 2022-01-30
### Changed
- Collect and upload time remaining during checkin.

## [0.5.0] - 2022-01-23
### Changed
- Unroll metadata information if available.

## [0.4.9] - 2022-01-06
### Changed
- Use omni.kit.app to quit and shutdown Kit app reliably.

## [0.4.8] - 2021-10-23
### Changed
- Updated iconography of Extension to match Omniverse Farm branding.

## [0.4.7] - 2021-09-27
### Changed
- WAR, checkin with agent timing out.

## [0.4.5] - 2021-07-22
### Added
- Log errors during task execution.

## [0.4.4] - 2021-07-06
### Added
- Register the http client for communication with the local agent.

## [0.4.3] - 2021-07-03
### Added
- Added task progress reporting.

## [0.4.2] - 2021-04-22
- Send metrics at end of job.

## [0.4.1] - 2021-03-26
- Fix metrics decoding.

## [0.4.0] - 2021-03-23
- Pass through metrics when task checks in.

## [0.3.1] - 2021-02-11
- Reduce checkin interval to make sure the task does not timeout while hanging to open a scene.

## [0.3.0] - 2021-02-11
- Use new Kit SDK
- Send heartbeats to agent with task updates.

## [0.2.1] - 2021-02-01
- Update teamcity auto publish script

## [0.2.0] - 2021-02-01
- Improve log and error handling

## [0.1.0] - 2021-01-30
- Initial version
- Automated Teamcity publishing

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.1] - 2025-03-18
## Changed
- Remove test dependencies to fix test error.

## [0.11.0] - 2024-11-27
## Changed
- OMPE-27947:Compatible with Kit 107 (USD 24 / Python 3.11)

## [0.10.0] - 2024-01-09
## Changed
- Add `source` attribute to asyncio collect tasks to resolve another exception in upstream collect tool. (OM-118053)

## [0.9.0] - 2024-01-09
## Changed
- Bump version to 0.9.0 to avoid previously reverted 0.8.0 version that seems to be causing a conflict.

## [0.8.0] - 2024-01-09
## Changed
- Add `start_time` attribute to asyncio collect tasks to resolve exceptions in upstream collect tool. (OM-118053)

## [0.7.0] - 2023-06-21
## Changed
- Remove dependency `omni.kit.tool.collect` (and `omni.client`) in favor of `omni.kit.usd.collect`. Due to refactor from OM-86682.

## [0.6.0] - 2023-06-14
## Changed
- Remove dependency pin `omni.kit.tool.collect` to `2.1.27`  (originally introduced due to OM-86689), this is causing issues with USD Composer (OM-97607).

## [0.5.0] - 2023-03-22
### Changed
- Update `BaseUploadCollector` class to work with latest `omni.kit.tool.collect-2.1.27` due to interface updates on the Collector class.
  - make use of `CollectorTaskType`, update `_configure_task` to use those types.
  - update `add_copy_task` with new kwarg `skip_if_existed` per `omni.kit.tool.collect.Collector`
  - update `open_or_create_layer` with new kwarg `clear=True` per `omni.kit.tool.collect.Collector`
  - update `remove_all_materials_and_bindings` to `_remove_all_materials_and_bindings` per `omni.kit.tool.collect.Collector`
- pin `omni.kit.tool.collect` to `2.1.27` in dependencies.
- add `ignore_missing_assets` param to `/collect/process/s3` endpoint, defaulted to `True` (the current existing behavior).

## [0.4.1] - 2023-02-28
### Changed
- Update unit tests to use `omni.kit.test.AsyncTestCase` class.

## [0.4.0] - 2022-10-25
### Changed
- Updated to work with newest version of the collect tool.

## [0.3.7] - 2022-09-07
### Changed
- Use fixed version of collect tool.

## [0.3.6] - 2021-10-23
### Changed
- Updated iconography of Extension to match Omniverse Farm branding.

## [0.3.5] - 2021-08-31
### Changed
- Temporary workaround to catch the saving of layers and make sure they are uploaded to S3.

## [0.3.4] - 2021-08-31
### Changed
- Append filename as subfolder to output folder by default for all collectors.

## [0.3.3] - 2021-08-29
### Changed
- Allow overriding the certificate bundle via the settings.

## [0.3.2] - 2021-08-29
### Changed
- Add SSL options for S3 and improve README and documentation.

## [0.3.1] - 2021-08-28
### Changed
- Fix AWS argument passing.

## [0.3.0] - 2021-08-28
### Changed
- Add support for remote storage backends.
- Add support for AWS S3 as a remote storage backend.

## [0.2.0] - 2021-08-25
### Changed
- Add support for progress
- Add farm job configuration
- Remove no longer needed dependency on omni.kit.renderer.core. Added exception for unittests.

## [0.2.0] - 2021-07-22
- Temporarily add dependency on omni.kit.renderer.core to fix unittests.

## [0.1.0] - 2021-04-03
- Initial version.

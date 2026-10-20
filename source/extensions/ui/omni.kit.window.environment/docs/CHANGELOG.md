# CHANGELOG

This document records all notable changes to ``omni.kit.window.environment`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.8.1] - 2025-11-25
### Changed
- Make sure env type correct loaded from cache

## [1.8.0] - 2025-08-20
### Changed
- Update to event 2.0

## [1.7.8] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [1.7.7] - 2025-04-14
### Removed
- Usage and checks for legacy Viewport

## [1.7.6] - 2025-01-09
### Changed
- OMPE-27665: Add python API document.

## [1.7.5] - 2025-01-03
### Change
- OMPE-32822: Fix a test failure with Events 2.0

## [1.7.4] - 2024-11-13
### Change
- Update for kit 107 with usd 24 and python 3.11

## [1.7.3] - 2024-09-30
### Change
- Update test of navigating to dynamic sky to do not use UI comparison

## [1.7.2] - 2024-07-23
### Change
- OMPE-14781: Added missing dependency "omni.kit.notification_manager"

## [1.7.1] - 2024-04-26
### Change
- Update test to make sure data loaded

## [1.7.0] - 2024-04-26
### Change
- OM-123517: Run Usd.Stage.Open in async mode to not block UI if long latencies

## [1.6.11] - 2023-08-14
### Change
- Property widget displayed when window first visible

## [1.6.10] - 2023-07-10
### Change
- Clean env templates from stage template menu after env templates updated

## [1.6.9] - 2023-06-27
### Change
- Cache new root folders during warmup
- Cache environment type to speed up UI loading time

## [1.6.8] - 2023-06-26
### Changed
- Update menu text for lazy menu

## [1.6.7] - 2023-06-14
### Changed
- OM-98241: New default folder

## [1.6.6] - 2023-06-08
### Added
- Added ability to pass custom root folder path into EnvBrowserModel

## [1.6.5] - 2023-06-02
### Change
- OM-96989: Default not build ui when startup

## [1.6.4] - 2023-05-25
### Change
- OM-66083: Support templates with sub layers

## [1.6.3] - 2023-05-23
### Change
- OM-95536: Hide "*props*", "SubUSDs"

## [1.6.2] - 2023-05-15
### Change
- OM-66083: Do not show render setting of scene templates

## [1.6.1] - 2023-05-03
### Change
- OM-92888: Fix property button missed in Composer when startup

## [1.6.0] - 2023-03-13
### Change
- OM-85649: support of lazy load workflow in Create

## [1.5.1] - 2023-02-20
### Removed
- Remove unused print

## [1.5.0] - 2023-02-19
### Changed
- OM-83124: Save env templates to cache file and load in next startup

## [1.4.9] - 2023-01-04
### Changed
- Make sure environment model created before navigating to dynamic skies

## [1.4.8] - 2023-01-03
### Changed
- Update golden

## [1.4.7] - 2022-11-14
### Changed
- OM-73937: Set sun study time to avoid test sometimes failed

## [1.4.6] - 2022-11-14
### Changed
- OM-72818: the threshold at which it goes to stacked could still be narrower

## [1.4.5] - 2022-11-14
### Changed
- Update template with async and new template API if possible

## [1.4.4] - 2022-11-14
### Changed
- Change default layout to horizontal instead of vertical since default dock changed to Content

## [1.4.3] - 2022-11-14
### Changed
- Update golden images

## [1.4.2] - 2022-11-10
### Changed
- Do not show window immediately after docked

## [1.4.1] - 2022-11-04
### Changed
- Use action when applying environment
- OM-36606: Add show light warning to options menu

## [1.4.0] - 2022-11-04
### Changed
- Use new treeview style

## [1.3.0] - 2022-10-28
### Changed
- Update golden for new environment property
- Make actions be optional

## [1.2.2] - 2022-11-02
### Fixed
- Avoid exception if file url is None

## [1.2.1] - 2022-10-06
### Removed
- Remove VP1 test

## [1.2.0] - 2022-09-10
### Added
- OM-44838: Add action to drop to stage window

## [1.1.8] - 2022-08-29
### Changed
- calling `FolderBrowserModel`'s start_traverse instead of the `FileSystemFolder`'s one'
- Add local cache file path to use local cache feature to avoid folder traverse when close and open the app again

## [1.1.7] - 2022-08-22
### Added
- Updated test (for coverage)

## [1.1.6] - 2022-06-19
### Added
- Drop to VP2

## [1.1.5] - 2022-05-20
### Changed
- Default sky location

## [1.1.4] - 2022-04-06
### Fixed
- OM-48058: Exception being thrown when drag-drop into Viewport.

## [1.1.3] - 2022-03-30
### Changed
- Republish for repo updates

## [1.1.2] - 2022-03-15
### Changed
- Add settings for main window visible on startup

## [1.1.1] - 2022-03-09
### Changed
- UI refactor

## [1.1.0-beta.1] - 2021-02-25
### Changed
- UI refactor

## [1.0.0-beta.9] - 2021-01-26
### Changed
- Default scene template url

## [1.0.0-beta.8] - 2021-01-26
### Changed
- Allow to change sky when scene template enabled
- Show prompt when import/export scene template

## [1.0.0-beta.7] - 2021-01-22
### Changed
- Fix typo
- Refresh scene template lists if new saved

## [1.0.0-beta.6] - 2021-01-18
### Changed
- Fix issue if no stage when startup

## [1.0.0-beta.5] - 2021-12-20
### Added
- Enable "Set to Stage" in options menu
- Also rename "Set to World" to "Set to Stage"

## [1.0.0-beta.4] - 2021-12-16
### Changed
- Remove /Environment before applying new scene template
### Added
- Add new options menu

## [1.0.0-beta.3] - 2021-12-08
### Added
- Fix destory to destroy typo

## [1.0.0-beta.2] - 2021-10-29
### Changed
- Use new model and delegate

## [1.0.0-beta.1] - 2021-10-29
### Added
- First beta

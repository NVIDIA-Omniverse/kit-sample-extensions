# CHANGELOG

This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [1.3.8] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: compose camera layers when copying cameras and hide the private runtime camera.

## [1.3.7] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.3.6] - 2025-03-19
### Changed
- Updated documentation with AI agent.

## [1.3.5] - 2025-01-06
### Added
- Update public api

## [1.3.4] - 2024-04-11
### Changed
- OM-122149: Removing AnimationSchemaTools (`omni.usd.schema.anim`) dependency.

## [1.3.3] - 2024-01-08
### Changed
- Removing `omni.kit.usd_presenter.conn.manager` dependency.

## [1.3.2] - 2023-11-29
### Changed
- Do not need to stop timeline if stop playing when timeline is end

## [1.3.1] - 2023-10-13
### Changed
- Increase code coverage to 87.6%

## [1.3.0] - 2023-09-26
### Added
- Add setting to use time sampling for smooth play (default animation)

## [1.2.0] - 2023-09-25
### Added
- OM-41439: Smooth navigate in playlist when next/previous

## [1.1.9] - 2023-05-19
### Fixed
- OM-95172: Don't reset the paly model's index when play stop

## [1.1.8] - 2023-04-07
### Changed
- Updating from omni.view.conn.manager -> omni.kit.usd_presenter.conn.manager

## [1.1.7] - 2023-03-14
### Changed
- Only accept drop cameras/waypoints/markups in playlist model

## [1.1.6] - 2023-03-14
### Changed
- OM-80113 - Fixing "All Markups" section of the playlist tool.

## [1.1.5] - 2023-02-27
### Changed
- OM-83090: Make sure animation camera prim with type "Camera" to run animation

## [1.1.4] - 2023-02-23
### Changed
- Ignoring IToken testing error message that appears to be unrelated to the tests passing

## [1.1.3] - 2022-11-18
### Changed
- OM-71202: Fix play issue on smooth mode for system playlist

## [1.1.2] - 2022-11-17
### Changed
- Fixed missing constant preventing the waypoint browser/thumbnail window from doing 'Play'

## [1.1.1] - 2022-11-17
### Changed
- OM-71202: Fix play issue on smooth mode

## [1.1.0] - 2022-11-08
### Changed
- OM-71202: Make sure there will be prim path for playlist and match new animation commands

## [1.0.1] - 2022-09-16
### Added
- API to add playlist card from other extensions
- PlayManager to play playlist to sync with other extensions
### Removed
- Remove playlist card of Waypoint (use omni.kit.waypoint.playlist instead)

## [1.0.0] - 2022-08-16
### Added
- Comes from omni.kit.tool.camera_playlist

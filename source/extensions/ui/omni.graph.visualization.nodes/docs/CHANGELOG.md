# Changelog

The documentation for omni.graph.visualization.nodes
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.4] - 2025-08-21
### Changed
- OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

## [2.1.3] - 2025-01-15
### Fixed
- OMPE-27792: Update public API.

## [2.1.2] - 2024-12-30
### Fixed
- Deprecation warning from DrawScreenSpaceText

## [2.1.1] - 2023-05-04
### Fixed
- Fixed broken DrawScreenSpaceText node.
- NOTE: this node must be in an ActionGraph configured for "pipelineStageSimulation" (the default) and not used to
  drive a Character (SkelRoot).

## [2.1.0] - 2023-04-19
### Changed
- DrawLine in omni.graph.visualization.nodes has rotted
- Fix DrawLine
- Fix DrawLabel

## [2.0.1] - 2023-02-17
### Changed
- OM-82556: Added super().__init__() calls to init overrides for Py 3.10.

## [2.0.0] - 2022-09-27
### Changed
- Built against kit-104.

## [1.2.0] - 2022-08-04
### Added
- VP2 support for screen-space text -- but still calling the node "Beta" until it has more robust support.

## [1.1.2] - 2022-07-28
### Changed
- Mark screen-space text node as "Beta" until VP2 is supported.

## [1.1.1] - 2022-03-18
### Changed
- Rebuilt against latest kit-sdk

## [1.1.0] - 2022-03-11
### Added
- Added node for drawing text in screen space
### Changed
- Removed 'debug' from node named

## [1.0.1] - 2022-02-18
### Changed
- Minor version bump

## [1.0.0] - 2022-02-17
### Added
- Initial nodes

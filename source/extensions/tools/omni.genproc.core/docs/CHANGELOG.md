# CHANGELOG

This document records all notable changes to ``omni.genproc.core`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [110.0.2] - 2026-10-17

### Changed

- Republish through the verified Windows signing path with signed package metadata.

## [110.0.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: migrate graph token handling to NameToken and integrate current native dependencies.

## [110.0.0] - 2025-12-10
### Changed
- Updated for Kit 110.

## [109.0.0] - 2025-08-21
### Changed
- Updated to new Path and Token interface.

## [108.0.0] - 2025-07-22
### Changed
- Recompile with new kit-kernel.

## [107.0.3] - 2025-05-13
### Changed
- Increased tests tolerance.

## [107.0.2] - 2025-03-13
### Changed
- Enable Arm Builds

## [107.0.1] - 2025-02-10
### Changed
- Added `writeTarget.usd = true`.

## [107.0.0] - 2025-02-05
### Changed
- Updated for Kit 107. Recompiled with ABI=1.

## [106.1.0] - 2024-09-03
### Changed
- Moved to Kit 106.1

## [105.1.9] - 2024-01-25
### Changed
- Removed use of omni.graph.io Import node (replacing with ReadPrimsV2).
- Removed explicit usage of bundle dirtyIDs.
- Updated index.rst.

## [105.1.8] - 2023-11-29
### Changed
- Republish.

## [105.1.7] - 2023-08-17
### Changed
- Update to CUDA 11.8 for compatibility with other extensions.

## [105.1.6] - 2023-07-25
### Fixed
- Republish with a version number greater than the latest 105.1 extension.

## [105.1.4] - 2023-05-22
### Changed
- Republish.

## [105.1.3] - 2023-05-18
### Changed
- Republish.

## [105.1.2] - 2023-05-12
### Changed
- PointOnCurve -- revert to single u-value version.
- PointsOnCurve -- add node to handle arrays of u-values or random sampling.

## [105.1.1] - 2023-05-11
### Changed
- PointOnCurve -- Support one u-value, an array of u-values, or randomly sampled u-values.

## [105.1.0] - 2023-05-08
### Changed
- Rebuild against kit 105.1.

## [105.0.18] - 2023-04-25
### Changed
- Removed Flora.

## [105.0.17] - 2023-04-24
### Fixed
- Check nullptr of texcoord data from bundle.

## [105.0.16] - 2023-03-30
### Changed
- Add cycle flag in motion path node.

## [105.0.15] - 2023-03-22
### Changed
- Republish after USD/python update.

## [105.0.14] - 2023-03-21
### Changed
- Republish after USD/python update.

## [105.0.13] - 2023-03-14
### Changed
- Republish after USD/python update.

## [105.0.12] - 2023-02-21
### Changed
- Update PhysX usage.

## [105.0.11] - 2023-02-15
### Fixed
- Improved region test for `ScatterPointsGroup` node.
### Added
- Added group name in texture filter.
- Added group visibility in `ScatterPointsGroup` node.

## [105.0.10] - 2023-01-17
### Added
- Added `LoadTexture2D` node for generic texture(s) loading and output data into bundle.
- Added the ability to assign texture filter to Flora system to filter point scattering.

## [105.0.9] - 2023-01-10
### Added
- Added `ScatterPointsGroup` node for Flora.
- Added `ScatterPointsModifier` node to post modify `omni.particle.system.core.PointInstancer` data.

## [105.0.8] - 2023-01-03
### Changed
- Align cublas and cusparse dlls from cuda 11.7.0 with omni.pip.torch on Windows.
- Remove redundant cuda libs on Linux.

## [105.0.7] - 2022-11-23
### Fixed
- Scatter Points crash.

## [105.0.6] - 2022-11-16
### Changed
- Support the new Fabric system.

## [105.0.5] - 2022-11-10
### Changed
- Re-add cuda libraries to extension.

## [105.0.4] - 2022-11-10
### Changed
- Reduce cublas and cusparse dynamic libraries.

## [105.0.3] - 2022-10-14
### Changed
- Merge motion path node from 104.

## [105.0.2] - 2022-09-30
### Changed
- Incrementing extension version; better point inside mesh test.

## [105.0.1] - 2022-09-05
### Fixed
- Fixed tangents and binormals of ScatterPoints.

## [105.0.0] - 2022-09-02
### Fixed
- Fixed normal transform for prim to triangles.

## [104.5.6] - 2022-08-11
### Fixed
- Fixed arbitrary perpendicular utility function

## [104.5.5] - 2022-08-09
### Changed
- Rebuild against new kit-sdk

## [104.5.4] - 2022-08-07
### Fixed
- Replace custom Releaser with std::unique_ptr

## [104.5.3] - 2022-08-01
### Changed
- Re-categorized nodes

## [104.5.2] - 2022-07-11
### Fixed
- Check for nullptr before dereferencing.

## [104.5.1] - 2022-07-08
### Changed
- Move nodes to wip.genproc.core

## [104.5.0] - 2022-06-28
### Added
- Move curve nodes from omni.curve.nodes into this extension
### Fixed
- Deregister nodes when the extension is unloaded

## [104.4.2] - 2022-06-17
### Changed
- Kid-SDK version bump to fix MPiB dirty id tracking and DataModel attribute remove bug.

### Fixed
- Fix compilation errors related to FC type safety.


## [104.4.1] - 2022-06-13
### Fixed
- Fix template names for instance along curves nodes

## [104.4.0] - 2022-05-17
### Added
- ScatterPointsFromCamera node

## [104.3.0] - 2022-05-03
### Added
- PrimToTransform node
- Add opacity and travelling to ExtrudeAlongCurve node

## [104.2.0] - 2022-02-01
### Added
- ExtractPointsFromPrims node

## [104.1.0] - 2022-01-28
### Changed
- Renamed extension to omni.genproc.core
### Removed
- Removed extension dependencies and menu options

## [104.0.0] - 2022-01-27
### Changed
- Bump version to 104.

## [1.8.0] - 2021-12-12
### Added
- PointInstancerAlongCurves -- pass prototypes through node; use bbox for end-to-end instancing
- CurveInstancerAlongCurves -- minimum curve length
### Fixed
- instance transforms in end-to-end instancing

## [1.7.0] - 2021-11-08
### Added
- Point instancing along curves: add prototypes input and end-to-end instancing option

## [1.6.3] - 2021-11-03
### Added
- OgnExportToHydra - a node to send deformed points from a bundle to hydra from the source prim

## [1.6.2] - 2021-10-26
### Added
- OgnDeformByCurve

## [1.6.1] - 2021-10-25
- Force update of new version

## [1.6.0] - 2021-10-22
### Added
- Options to align curves-along-curves instances

## [1.5.0] - 2021-10-12
### Added
- Instancing along curves -- convert to BundlePrims workflow; additional instancing options
- Add curves along curves node

## [1.4.0] - 2021-09-09
### Added
- Added visualization of frames along curve
### Fixed
- Fixed frames on points sampled along curve, improved sampling using ramp

## [1.3.0] - 2021-09-01
### Fixed
- Better curve sampling in OgnPointInstancerAlongCurves

## [1.2.0] - 2021-08-27
### Added
- Added OgnPointInstancerAlongCurves

## [1.1.0] - 2021-06-17
### Added
- Added OgnPaint Node.

### Fixed
- Fixed forwarding attribute on OgnMergeAttributes Node.


## [1.0.0] - 2021-05-25
### Added
- Initial version. Added MergeAttributes Node.

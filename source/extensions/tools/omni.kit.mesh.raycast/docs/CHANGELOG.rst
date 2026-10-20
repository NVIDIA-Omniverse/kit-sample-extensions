# CHANGELOG

This document records all notable changes to ``omni.kit.mesh.raycast`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

[110.0.2] - 2026-10-16
Changed
-------
- Give the existing Kit 111 compatibility changes a distinct package version: use the current Python binding and raycast buffer ownership APIs.

## [110.0.1]
### Fixed
- BVH refit: a path whose map entry exists only because it has mesh descendants no longer reuses
  bound index 0 as its own. It takes a free bound, so it cannot overwrite a descendant's bound.
  ``test_raycast`` intermittently lost ``/World/Cube/Sphere`` when the visible cube and its sphere were
  re-added sphere-first. Ported from main (19ce1a68), with its regression test ``test_ancestor_becomes_geometry``.
- ``RaycastTests``: force a synchronous BVH refresh before each query that follows a stage edit,
  so ``test_raycast`` no longer depends on that edit reaching the BVH before the raycast update
  handler happens to run.
- ``RaycastTests``: assert on mesh paths rather than result counts, so a failure names the prim
  that went missing instead of only saying ``False is not true``.

## [110.0.0]
### Changed
- updated to kit 110

## [109.0.0]
### Changed
- updated to kit 109

## [108.0.0]
### Changed
- updated to kit 108.0

## [107.0.1]
### Changed
- Enabled Arm

## [107.0.0]
### Changed
- Updated to ABI=1.

## [106.0.0]
### Changed
- update to kit 106.1, remove physxSchema

# [105.4.0] - 2024-02-29
### Changed
- Updated usdrt dependency.

# [105.3.3] - 2023-12-04
### Updated
- Updated Kit Version

# [105.3.2] - 2023-10-19
### Fixed
- Added a check for a rare crash

# [105.3.1] - 2023-04-14
### Fixed
- update unit test cause some prim's normal inverted recently(OM-87593)

# [105.3.0] - 2023-03-31
### Added
- Updated Kit Version

# [105.2.1] - 2023-03-22
### Added
- Added setHitFilterFn
- Supported double side raycast

# [105.2.0] - 2023-03-14
### Changed
- Update for latest USD and Python version.

# [105.1.2] - 2023-03-09
### Changed
- Updated `SplineCurve` to correctly handle periodic Cubic Bezier BasisCurves.

# [105.1.1] - 2023-02-02
### Added
- closestRaycastMesh now sets the face_index when hitting a mesh.

# [105.1.0] - 2022-11-29
### Changed
- enable bvhBuildOnFirstRequired by default.

# [105.0.7] - 2022-11-23
### Fixed
- Fixed when added mesh is child of a non-xformable.

# [105.0.6] - 2022-11-15
### Added
- Added setting bvhBuildOnFirstRequired.

# [105.0.5] - 2022-10-26
### Changed
- Added stage load activity.

# [105.0.4] - 2022-10-27
### Changed
- Cherry pick MR-391 from release 104.0

# [105.0.3] - 2022-10-11
### Changed
- Changed adding new bounds to multi-threaded.

# [105.0.2] - 2022-09-28
### Fixed
- Revert fixing deformable visualization meshes, because deformable changed design

# [105.0.1] - 2022-09-27
### Fixed
- Fixed mesh desc invalid message on deformables

# [105.0.0] - 2022-08-30
### Fixed
- Fixed remove non-imagable prim cause BVH rebuild.

# [104.2.9] - 2022-08-24
### Fixed
- Fixed unable to raycast on deformable visualization meshes.

# [104.2.8] - 2022-08-22
### Fixed
- Fixed crash on shutdown due to calling into ITasking in plugin implementation's destructor.

# [104.2.7] - 2022-08-08
### Fixed
- Fixed tests on Linux

# [104.2.6] - 2022-08-04
### Fixed
- Excluded UsdGeomCamera from BVH

# [104.2.5] - 2022-07-19
### Changed
- change getVertexLocalPosition to getVertexLocalPositions

# [104.2.4] - 2022-07-13
### Changed
- Support toggle visible of prim.

# [104.2.3] - 2022-07-12
### Fixed
- Excluded UsdGeomPoints from BVH and correctly handle unsupported types.

# [104.2.2] - 2022-06-15
### Fixed
- Fixed BVH rebuilding when resync path is the absolute root "/".

# [104.2.1] - 2022-06-07
### Added
- Added functions to tessellate and sample on `UsdGeomBasisCurves`. See `tessellateCurve` and `sampleCurveSegmentAtT`

# [104.2.0] - 2022-05-25
### Added
- Added `RaycastContext` so each query can optionally operates on different configurations.
### Changed
- Fixed mismatch overlap vertices and faces returned in `overlap_vertices`` call.

# [104.1.3] - 2022-05-23
### Changed
- Fixed vertex indices returned by `overlap_vertices`` if there's unused point in mesh's Points attribute.

# [104.1.2] - 2022-04-15
### Changed
- Merge from release 103

# [104.1.1] - 2022-03-18
### Fixed
- Fixed assert issue in debug mode
- Fixed add and remove prim in same frame
### Added
- Added unit test

# [104.1.0] - 2022-03-14
### Changed
- `OverlapVerticesResult` now contains overlapped face indices as well.
### Added
- Added `IMeshRaycast::getVertexLocalPosition` as a faster way to get vertex location.

# [104.0.2] - 2022-02-22
### Changed
- update version.

# [104.0.2] - 2022-01-31
### Changed
- Switched to `UsdContext::computePrimWorldBoundingBox` and `UsdContext::computePrimWorldTransform`.

# [104.0.1] - 2022-01-27
### Changed
- Fixed potential invalid access to `end` iterator.

# [104.0.0] - 2022-01-27
### Changed
- Added writeTarget to extension.toml file

# [103.5.0] - 2022-01-13
### Changed
- Maintain BVH across entire USD stage life span.

# [103.4.0] - 2021-12-22
### Changed
- Fixed out of sync BVH and collision mesh pose.
- Added multi-thread support for collecting result in `overlapVertices`.

# [103.3.0] - 2021-12-16
### Changed
- Hash and reuse identical `PxTriangleMesh` even if they're from different prim.

# [103.2.0] - 2021-12-03
### Added
- Supported `UsdGeomBasisCurves`. The curves are tessellated into tri mesh for ray cast and overlap test.

# [103.1.8] - 2021-11-29
### Changed
- Fix crash in `reportHit` when doing overlap test.

# [103.1.7] - 2021-11-12
### Changed
- Fix distance error for closestRaycastBound.

# [103.1.6] - 2021-11-12
### Changed
- Add interface for get the raycast hit bound.

# [103.1.5] - 2021-10-25
### Changed
- Add flooding support for shape prims.

# [103.1.4] - 2021-10-11
### Changed
- Version changes.

# [103.1.3] - 2021-09-29
### Changed
- Add raycast support for shape prims.

# [103.1.2] - 2021-08-23
### Changed
- Add support for UsdGeomMesh with physx deformables related properties.

# [103.1.1] - 2021-08-06
### Changed
- Bugfixes.

## [103.1.0] - 2021-07-28
### Added
- Added `overlapVertices`, `freeOverlapVerticesResult` and python binding `overlap_vertices`.

## [103.0.0] - 2021-06-24
### Changed
- Version changes.

## [102.2.0] - 2021-06-22
### Changed
- BVH and cached triangle mesh will refit/rebuild when USD data changes.

## [102.1.1] - 2021-06-21
### Changed
- Version changes.

## [102.1.0] - 2021-05-25
### Changed
- Version changes.

## [0.5.1] - 2021-05-21
### Changed
- Naming changes.

## [0.5.0] - 2021-05-04
### Changed
- Prepare for 101 release.

## [0.4.0] - 2021-05-01
### Added
- Added `getFloodPoints`

## [0.3.1] - 2021-04-26
### Changed
- Fixed Linux linking.

## [0.3.0] - 2021-04-12
### Added
- Support Tetrahedron Mesh.

## [0.2.0] - 2021-04-05
### Added
- Added `spherecast`.

## [0.1.4] - 2021-03-04
### Changed
- update license

## [0.1.3] - 2021-01-26
### Fixed
- Fix issue when raycast on mesh combination of the scale and rotate

## [0.1.2] - 2020-12-08
### Fixed
- Remove dependency on carb.setting extension

## [0.1.1] - 2020-11-28
### Added
- Add API for raycast on single mesh(whitout set BVH)
### Fixed
- support mesh scale
- clear bound cache when createBVH

## [0.1.0] - 2020-11-02
### Added
- Initial mesh raycast

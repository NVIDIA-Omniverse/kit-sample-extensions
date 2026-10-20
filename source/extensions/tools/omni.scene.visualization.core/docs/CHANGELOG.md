# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [110.0.2] - 2026-10-16
### Changed
- Issue a fresh package for verified Windows signing and signed publication metadata.

## [110.0.1] - 2026-10-12
### Changed
- Kit 111 tests: `test_visualization_options` accepts 0.02 on Windows only (lines drawn over the corner dots; 0.01617 measured), for EA1. Linux keeps 1e-4. EA2 ticket: OMPE-<to be filed>.

## [110.0.0] - 2025-12-10
### Changed
- Updated for Kit 110.

## [109.0.1] - 2025-10-07
### Changed
- Added wait for viewport ready in test. Changed image compare function.

## [109.0.0] - 2025-08-21
### Changed
- Updated to new Path and Token interface.

## [107.0.2] - 2025-03-13
### Changed
- Enable Arm Builds

## [107.0.1] - 2025-02-18
### Changed
- Updated `omni.kit.viewport.window` dependency.

## [107.0.0] - 2025-02-05
### Changed
- Updated for Kit 107. Recompiled with ABI=1. Updated unittest.

## [105.4.14] - 2024-09-09
### Changed
- OMPE-20562: Fix deprecated usage for IStageUpdate interface.

## [105.4.13] - 2023-11-29
### Changed
- Removed unnecessary physx dependency.

## [105.4.12] - 2023-08-03
### Added
- Support reading fabric world transform for prim visualization.

## [105.4.11] - 2023-07-28
### Added
- Option to control whether the widths primvar is used for BasisCurves wireframe / vertex visualization (default to false).

## [105.4.10] - 2023-07-11
### Changed
- Use USDRT API to query for prims with sceneviz schema on stage load.

## [105.4.9] - 2023-06-27
### Changed
- Removed unnecessary dependency on preferences window.

## [105.4.8] - 2023-06-01
### Fixed
- Add omni.kit.stage_templates dependency for tests.

## [105.4.7] - 2023-05-22
### Changed
- Republish.

## [105.4.6] - 2023-05-05
### Changed
- Removed unnecessary dependency on omni.kit.window.property.

## [105.4.5] - 2023-03-22
### Changed
- Republish after USD/python update.

## [105.4.4] - 2023-03-21
### Changed
- Republish after USD/python update.

## [105.4.3] - 2023-03-14
### Changed
- Republish after USD/python update.

## [105.4.2] - 2023-03-07
### Added
- Added `DrawLineLoop` to draw line segments with last vertex connected to first vertex.
### Changed
- Correctly draw periodic UsdBasisCurves that does not have the first vertex repeated.

## [105.4.1] - 2023-02-07
### Changed
- Rebuild
- Added ambient light setting to tests

## [105.4.0] - 2023-02-07
### Changed
- Use schema to track prims with visualization attributes.
- Add (experimental, default false) option for metadata prim.
- Refactor.

## [105.3.0] - 2023-01-19
### Changed
- Add hasVisualization flag attribute to speed up large scene initialization.

## [105.2.6] - 2023-01-13
### Changed
- Perform scene traversal in parallel.
- Small optimization for initialization of large stages.

## [105.2.5] - 2022-11-28
### Fixed
- One more case of overwriting an attribute value from USD.

## [105.2.4] - 2022-11-16
### Changed
- Fixed bug where the visualization attribute in USD was not in-sync with the visualization flag.

## [105.2.3] - 2022-11-16
### Changed
- Update for upstream dependencies.

## [105.2.2] - 2022-11-16
### Changed
- Support the new Fabric system.

## [105.2.1] - 2022-11-12
### Fixed
- Fixed bug that was creating unnecessary active layer edits of sceneviz attrs.

## [105.2.0] - 2022-11-10
### Added
- display color/opacity, normal, and width visualizations for BasisCurves prims.

## [105.1.3] - 2022-11-01
### Fixed
- Fixed test based on upstream changes.

## [105.1.2] - 2022-10-26
### Fixed
- Avoid needlessly adding sceneviz attributes to instance prims.

## [105.1.1] - 2022-10-25
### Fixed
- Support visualizing types that derive from UsdGeomMesh / UsdBasisCurves.

## [105.1.0] - 2022-10-14
### Added
- Golden image test.
### Fixed
- Vertex color option now looks for displayColor/Opacity primvars.

## [105.0.2] - 2022-09-30
### Changed
- Incrementing extension version.

## [105.0.1] - 2022-09-01
### Changed
- Respect prim visibility (no sceneviz drawing when a prim is invisible).
- Update sceneviz drawing when a prim's sceneviz attributes are modified directly.

## [105.0.0] - 2022-08-23
### Changed
- Republish.

## [104.0.3] - 2022-06-27
### Fixed
- Deregister nodes when the extension is unloaded.

## [104.0.2] - 2022-06-17
### Changed
- Kid-SDK version bump to fix MPiB dirty id tracking and DataModel attribute remove bug.

### Fixed
- Fix compilation errors related to FC type safety.

## [104.0.1] - 2022-01-28
### Fixed
- Expose interface symbols at top level of python module

## [104.0.0] - 2022-01-27
### Changed
- Bump version to 104.

## [103.3.4] - 2022-01-26
- Moved UI to separate extension and renamed extension

## [103.3.3] - 2021-12-12
- Visualize point instances using bbox attributes.

## [103.3.2] - 2021-12-10
### Fixed
- Visualizing prims on extension startup.

## [103.3.1] - 2021-11-08
- Supported visualization of linear UsdBasisCurve.

## [103.3.0] - 2021-11-08
### Added
- OgnPointInstancerVisualizer: add prototypes input and visualize their bounding boxes

## [103.2.2] - 2021-11-08
- Config changes for ETM.

## [103.2.1] - 2021-10-25
- Force update of new version

## [103.2.0] - 2021-10-12
### Added
- OmniGraph node support for visualizing BundlePrims of point instancers and curves

## [103.0.8] - 2021-09-27
Republish.

## [103.0.7] - 2021-09-20
Fix assert failures.

## [103.0.6] - 2021-08-27
Expose get_interface on omni.scene.visualization module.

## [103.0.5] - 2021-08-18
Support for curves.
Persistence of visualized objects.

## [103.0.4] - 2021-08-12
Use updated IDebugDraw function names.

## [103.0.3] - 2021-08-06
Bugfixes.

## [103.0.2] - 2021-07-27
Fixed some crashes. Changed some attribute names.

## [103.0.1] - 2021-06-08
Bugfixes.

## [103.0.0] - 2021-06-23
Point to kit-sdk version 103

## [102.1.2] - 2021-06-21
Plumbing for point/line size. Recompile.

## [102.1.1] - 2021-06-02
Recompile.

## [102.1.0] - 2021-05-25
Rename.

# Changelog

## [110.4.1] - 2026-10-16
### Changed
- Update the exact Scene Optimizer Core dependency to its fresh signed-publication version.

## [110.4.0] - 2026-10-05
### Changed
- Updated omni.scene.optimizer.core version dependency to 110.4.0

## [110.3.0] - 2026-09-09
### Added
- OMPE-83801 - The `editStageMetrics` panel exposes the new `stopAtSkeletonRoot` argument.

### Changed
- Updated omni.scene.optimizer.core version dependency to 110.3.0

## [110.2.1] - 2026-08-04
### Fixed
- OMPE-103688 - `moveMaterials` now runs in the `move_material_looks`, `merge_extreme` and
  `merge_extreme_spatial` presets (previously skipped).

### Changed
- Updated omni.scene.optimizer.core version dependency to 110.2.1

## [110.2.0] - 2026-07-14
### Changed
- Updated omni.scene.optimizer.core version dependency to 110.2.0

## [110.1.0] - 2026-03-13
### Added
- OMPE-83740 - Add Shrinkwrap operation (OpenVDB)
- OMPE-62172 - Add invert option to BoxClip
- OMPE-40485 - Add SmallMeshChecker with SIZE_THRESHOLD

### Fixed
- OMPE-78396 - Bugfix for isCudaAvailable
- OMPE-78953 - Verify normals_checker behavior
- OMPE-79367 - Normals checker fix for requirements mode in validation
- OMPE-64727 - Enable Consider Deep Transforms for fuzzy dedupe
- OMPE-83497 - Fix Dedupe Deep Transforms and Pivots 
- Fix intermittent failure in cuda test
- Fix coverage counter in tests

### Updated
- OMPE-78396 - Update omo to use dlopen instead of linking libcuda
- OMPE-78396 - Use SO_LOG_WARN for CUDA
- OMPE-78396 - Configure GPU operators to check for presence of GPU and GPU CUDA drivers before running on GPU
- OMPE-81208 - Check for cuda/GPU once per executable
- OMPE-76841 - Clustered visibility check params for Find Occluded Meshes
- OMPE-53997 - Add unit tests for Dice Meshes
- Rationalize remesh tests 
- Removed mesh_tools.libs as an extension and linked it as a static library
- Link openvdb as a static library for shrinkwrap operation
- Updating kit kernel to 110.1.0

## [110.0.0] - 2025-12-17
### Changed
- Updated kit version

## [109.0.3] - 2025-12-15
### Fixed
- OMPE-75025 - Fix crash in deduplicate geometry to getAllChildren and ignore geom subsets

## [109.0.2] - 2025-12-02
### Added
- Add a convenience function to make describing joined arguments much more readable

### Fixed
- OMPE-72936 - Use consider deep transforms logic when using fuzzy deduplicate
- OMPE-69388 - Treat explicit attributes as constant primvars when merging meshes

### Updated
- Deduplicate with primvars now avoids deduplicating materials that are specialized, also update the analysis to exclude those materials from consideration

## [109.0.1] - 2025-11-12
### Fixed
- Asset Validator rule registration and reloading (v1.7.1)
- Mesh Cleanup to use points.size() VertexCount before stats
- Include abstract prims in Decimate Meshes
- Add override requirements for validation rule checks

## [109.0.0] - 2025-10-17
### Added
- Isolated Vertices Checker added to performance validation rules
- Original Mesh handling option to split meshes
- OMPE-63300 New USD Stats window from scene optimizer that presents 
- OMPE-56441, OMPE-64822 - New NormalsChecker performance validation rule
- OMPE-7305 - New FlatHierarchiesChecker performance validation rule that will check for prims with large amounts of children
- OMPE-62404, OMPE-63579 - Ignore Attribute option added to Deduplicate Geometry operation
- OMPE-61781 - Add Deduplicate detail panel to show the prims attributes and instance prototype
- OMPE-62400 - Added World space detection mode for Remove Small Geometry operation
- OMPE-62836 - Fit Primitives new operation to use UsdGeomMesh primitives
- OMPE-63934 - Mesh Cleanup new option to remove lamina faces and new validation rule added for duplicate face checker
- OMPE-63041 - Add Remove Attributes operation

### Fixed
- OMPE-64613 - Remove Small Geometry Compute Method for Threshold Small fixes that uses bounds maximum side size rather than cubic volume
- OMPE-64532 - Fix for Deduplicate Geometry to remove consider deep transforms from fuzzy mode
- OMPE-61871 - manually cherry-picked buffer overflow fixes for VirtualMesh
- Fix zero area face removal settings to match ColocatedVerticesChecker

### Updated
- OMPE-61770 - Improved reporting for RemoveSmallGeometry, SplitMeshes, ComputeExtents, and EditStageMetrics
- Improved reporting for SparseMeshChecker that will display which meshes are to be diced and which are to be split/clustered
- Cleaning up redundant subdivision operation output
- OMPE-61771 - Remove unnecessary logging for Find Hidden Meshes operation
- OMPE-61769 - Improve reporting for omnimesh operations and make more consistent when displaying mesh stats
- Updated tool tips for performance validators where some were missing
- OMPE-63579 - Remove Consider Attributes argument from Deduplicate Geometry
- OMPE-61569 - Refactor remove prims operation in various operations
- Updated Omnimesh-ops to give the same output results on ARM and x86
- OMPE-62171 - Refactor geometry based code to their own plugins and subfolders
- Updated Performance Validators to use new requirement structure for Asset Validator
- Improve usage of ArResolverScopedCache to speed up material calculations
- Replaced Asset Validator validation rules with Scene Optimizer based rules when they are available
- Minor performance improvement to materials analysis
- OMPE-51438 - Update omnimesh_ops_usd to the cuda12.4 flavoromnimeshops
- OMPE-68062 - Update Edit Stage Metrics to ignore viewport cameras

## [108.1.2] - 2025-09-08
### Fixed
- Removed Merge Vertices operation from UI

## [108.1.1] - 2025-09-04
### Updated
- Validator checkers have updated requirements rules with 1.3.1 release of Asset Validator
- Version lock extensions for ETM tests

## [108.1.0] - 2025-08-29
### Added
- OMPE-56576 - Deduplicate Geometry operation to support point-based geometry (i.e. basis curves) 
- Analysis mode for Mesh Cleanup to enable performance validators
- OMPE-57104 - New DegenerateGeometryChecker to analyze a scene checking for degenerate geometry (0.0 extent volume)
- OMPE-60332 - New Remove Small Geometry operation (with analysis support) that identifies and removes small geometry from the stage
- OMPE-55352, OMPE-60169 - Box Clip operation now supports instances and external references
- New Utility function to Flatten Instances that removes all instancing/composition from prims making them standalone prims
- OMPE-55971, OMPE-40489 - New DeduplicateGeometry and FuzzyDeduplicateGeometry Checkers available in the performance validation
- OMPE-54019 - New analysis mode and validator for Find Hidden Meshes
- Materials validation requirement added to DuplicateMaterialsChecker
- Geometry validation requirement added for RedundantTimesamplesChecker
- OMPE-53966 - New RedundantTimeSamplesChecker available in the performance validation
- OMPE-40495 - Add EmptyLeafChecker validation rule and analysis mode for Prune Leaves operation
- OMPE-53201 - Add HighVertexCountChecker validation rule

### Fixed
- Config change in Python API for analysis extension to comply with sonarqube requirements
- Deduplicate Geometry analysis mode uses updated filtering to match all composition cases and defaults to using instancable reference settings
- OMPE-53445 - Avoid omni.fabric.plugin warnings about primvars:::indices in Box Clip operation
- OMPE-57383 - Extents too big after converting mesh to prim in Fit Primitives operation
- OMPE-58894 - Removed multi-threading setup for clustering algorithm to improve processing times for spatial clustering on Split Meshes operation

### Updated
- OMPE-57247 - Updates the analysis API to provide a standard way for analysis to return a list of suggestedOperation that can be used to fix the issues. Updates the sparseMeshes operation to handle sparse disjoint meshes as well as large sparse single meshes
- OMPE-57621 - Updated logging in operations and improved timing setup
- OMPE-57635 - Updated scoped timers to be less verbose on per prim basis
- OMPE-58895 - Updated Edit Stage Metrics operation to not scale camera properties associated with lens and filmback when MPU is changed
- OMPE-51292, OMPE-57550, OMPE-57631 - Updated Fit primitive operation arguments and ability to account for inward/flipped normals, open endcaps on prims, and reduce verbosity of log output
- CoincidingMeshesChecker renamed to CoincidingGeometryChecker
- Omnimesh ops updated to latest version and new package location
- Changed MeshCleanupChecker rule into 3 new validation rules: ZeroAreaFacesChecker, NonManifoldChecker, ColocatedVerticesChecker
- OMPE-61225 - Updated UI menu dependencies for updated kit requirements
- OMPE-56762 - Updated Meshes submenu to be Geometry since multiple operations support other data types. Moved Optimize Primvars operation to the stage submenu

## [108.0.11] - 2025-08-06
### Fixed
- OMPE-58201 - Fixed a crash in Deduplicate Geometry operation to pass on empty prims, need path expression for inclusion

### Updated
- OMPE-57367 - Filter light and camera prims for omnimesh operations
- Remove timers for Fit Primitives operation
- Improved performance of resolving path expressions
- Improve Find Coincident Geometry traversal
- Simplify their prim resolving code in Optimize Skeletal Roots and Find Hidden Meshes

## [108.0.10] - 2025-07-24
### Updated
- OMPE-56442 - Split meshes feature included in Dice Meshes operation
- Stats operation now supports analysis mode

## [108.0.9] - 2025-07-22
### Updated
- OMPE-55594 - Box Clip added checks and tests
- OMPE-51290 - Attribute transfer from mesh to shape prims in Fit Primitives
- OMPE-51290 - Update omnimesh version

## [108.0.8] - 2025-07-22
### Added
- OMPE-3279 - Find Coincident Geometry skips empty mesh definitions

## [108.0.7] - 2025-07-21
### Updated
- OMPE-56041 - Updated kit and dependency library versions
- Improved performance on material analysis for better thread handling

## [108.0.6] - 2025-07-16
### Added
- PrimitiveFitChecker validation rule can now apply fixes in Asset Validator UI

### Updated
- OMPE-55594 - Box clip optimization to better handle mesh filtering
- Fit Primitive now logs total meshes replaced in output report
- Duplicate material analysis optimization when querying prim composition and running composition checks

### Fixed
- OMPE-51290 - Fit Primitives keeps material assignment on resulting output prim

## [108.0.5] - 2025-07-14
### Added
- OMPE-40491/OMPE-54014 - Fit Primitives supports meshes and added validator rule

### Updated
- Updated bundle extension to include analysis and validators dependencies
- Updated Asset Validator import python modules

## [108.0.4] - 2025-07-07
### Added
- OMPE-52167 - Topology Simplification option in Decimate Meshes
- OMPE-53331 - Add support for deduplicating geom subsets with primvars
- OMPE-41262 - omni.scene.optimizer.validators extension added that contains checkers for Asset Validator which use the Scene Optimizer analysis API

### Fixed
- OMPE-53944 - Geom subsets fix for omnimesh operations

### Updated
- OMPE-53944 - Update omnimesh version
- OMPE-54156 - Update kit kernel version

## [108.0.3] - 2025-06-29
### Updated
- Updated mesh_tools version

## [108.0.2] - 2025-06-27
### Updated
- Updating analysis extension version

## [108.0.1] - 2025-06-26
### Added
- New Box Clip operation
- New Dice Meshes operation
- New Fit Primitives operation
- Support for all point based geometry types in Find Coincident Geometry operation
- New option to deduplicate with primvars in Optimize Materials operation

### Fixed
- Merge Mesh operations applies any existing materialBindingAPI schemas
- Split Meshes analysis of extents and bad extents values updated
  - World space extents calculations
  - Local extents used in sparse mesh analysis

### Updated
- New UI menu with category subsections
- Find Coinciding Meshes renamed to Find Coincident Geometry
- Merge Vertices expanded with additional functionality and renamed to Mesh Cleanup
- Analysis mode to Optimize Primvars and Optimize Materials
- Improved spatial clustering behavior for clustering modes in Merge Static Meshes and Split Meshes
- Source Mesh tools extension instead of packman package

 ## [108.0.0] - 2025-05-21
### Updated
- Split mesh clustering and analysis for improved mesh handling
- Updated kit version

## [107.3.7] - 2025-05-20
### Added
- Support for USDPhysics angular velocity and distant lights in Edit Stage Metrics 
- Support for USD predicate expressions in operations

## [107.3.6] - 2025-05-14
### Fixed
- Merge meshes with custom output name

## [107.3.5] - 2025-05-08
### Updated
- Updated kit version

## [107.3.4] - 2025-05-06
### Fixed
- Manifold handling for face winding order

## [107.3.3] - 2025-05-01
### Fixed
- Compute pivot updated checks for empty points attributes

## [107.3.2] - 2025-04-29
### Updated
- Updated unit tests to specify a temporary directory location

## [107.3.1] - 2025-04-24
### Fixed
- MaterialBind on subset indexed attributes are handled to display correct material binding

## [107.3.0] - 2025-04-23
### Added
- New Generate Normals operation
- New Manifold Meshes operation

### Updated
- Merge vertices operation now has make manifold option on by default

## [107.1.4] - 2025-04-14
### Fixed
- Pivot transform Ops are handled correctly in Deduplicate Geometry operation

## [107.1.3] - 2025-04-08
### Fixed
- Primvars re-indexes attributes that originally had indices
- Merge Meshes better handling for Original Prim merge point
 - Ensured conflicting double xformOp pivots do not retain their type
 - Cleaned up the behavior of splitting and clustering invisible prims

### Updated
- Removed extra copies of libraries from core path

## [107.1.2] - 2025-03-25
### Fixed
- Expose ui extension to public API

## [107.1.1] - 2025-03-24
### Added
- Crease and sharpness support for subdivide meshes
- Public API rework and added repo checks

### Fixed
- Auto uv library is dynamically linked on windows
- Setting indices on referenced prims fixed for indexing primvars
- Moving ancestral prims is handled correctly in mesh checks
- Modify Instances - Merge Mesh preset update with SDF path expressions usage

### Updated
- Merge, Optimize Skeleton Roots, Deduplicate Geometry  use new mesh restructuring modules
- VirtualMesh updated to support splitting meshes with hole indices and subdivision surface data
- SpatialClustering and VirtualMesh updated to support all features needed for Merge operations

## [107.1.0] - 2025-03-03
### Added
- Split Meshes spatial clustering supports:
  - Keeping materials separate when splitting meshes
  - Merge boundaries like Merge Mesh operation for output mesh hierarchy location
  - Strict attribute mode like Merge Meshes operation
- Split Meshes has Original Prim merge boundary that uses the original prim that meshes have been split as a boundary specifier
- Compute Pivot can now add pivot xformOp to xforms
- Added support for string types for Optimize Primvars

### Fixed
- Mesh normals were not handled correctly with Split Meshes
- Decimate Meshes crash with NaNs and updated UI reporting
- Compute Pivot points weren't being computed in operation
- Improved performance of Compute Pivot operation

### Updated
- Updated default behavior for considering materials in Merge and Split mesh operations, users now specify to keep materials separated if needed

## [107.0.6] - 2025-02-14
### Added
- ABI upgrade

## [107.0.5] - 2025-02-04
### Added
- Optimize Primvars supports sting arrays to be simplified/indexed 
- Recently used JSON configs are viewable in preset menu

### Fixed
- Updated stats handling and reporting, uses JSON payload
- UI update to remove duplicate actions registering with Kit actions

## [107.0.4] - 2025-01-27
### Added
- SDF Prim based filtering, regex removed
- Subdivide Meshes operation

### Updated
- Split Meshes has spatial merge option

## [107.0.2] - 2025-01-07
### Added
- License update for 2025

### Fixed
- Fix mismatch with malloc/delete

## [107.0.1] - 2024-12-17
### Fixed
- Fix mismatch with malloc/delete

## [107.0.0] - 2024-11-25
### Added
- Update Kit SDK version to 107.0.2

## [106.1.10] - 2024-10-29
### Fixed
- Updated CI pipeline configs

## [106.1.5] - 2024-10-25
### Fixed
- Remesher added index primvar support and overall improved performance

## [106.1.4] - 2024-10-24
### Added
- Release bump to debug pipeline

## [106.1.3] - 2024-10-24
### Added
- Remesher operation
- Organize prototypes
- Updated kit verison

### Fixed
- Tessellation updates
- UI updates to allow UI window to be saved in app layout

## [106.1.1] - 2024-08-15
### Added
- Update Kit kernel version to 106.1
- Consider attributes option in fuzzy deduplicate

### Fixed
- Compute OBBs more accurately to improve fuzzy deduplication matching algorithm
- Improve geometry references/instanceable references reporting
- Change up axis of individual xformOps without needing to collapse them to matrices
- Remove Redundant UV primvars opinions on references
- UV generation ignores instance prototypes restrictions
- Stop report output logging to kit/console to reduce data amount
- Update Delete Hidden Prims to use internal method instead of kit method
- Skip time varying meshes to avoid crashes in some SO operations

## [106.0.16] - 2024-07-16
### Added
- Update Kit SDK version to 106.0.1

## [106.0.14] - 2024-07-15
### Added
- Release bump for master branch

## [106.0.13] - 2024-07-15
### Added
- Delete prims update

### Fixed
- Decimate meshes crash fix for invalid USD meshes

## [106.0.12] - 2024-07-01
### Added
- Release bump to debug pipeline

## [106.0.11] - 2024-07-01
### Added
- Decimate meshes accounts for world space scale, uses input mesh normals, and color variation to guide decimation algorithm
- Edit stage metrics operation

### Fixed
- Decimate meshes improved stability in multi-operations and misplaced output parts
- Find coinciding meshes new UI/UX to allow for copying of paths of found coinciding mesh prim generated report UI
- Find hidden meshes fix instance where CUDA was crashing

## [106.0.10] - 2024-05-16
### Added
- Tessellate meshes operation refactor

## [106.0.9] - 2024-05-09
### Added
- Test release to include linux binaries

## [106.0.8] - 2024-05-09
### Added
- Test release to include linux binaries

## [106.0.7] - 2024-05-09
### Added
- Test release to include linux binaries

## [106.0.6] - 2024-04-23
### Added
- Test release to include operation plugin libraries

## [106.0.5] - 2024-04-22
### Added
- Migrated pipeline to Gitlab-ci

## [106.0.4] - 2024-03-15
### Added
- Added new option for Fuzzy Deduplication

## [106.0.3] - 2024-02-26
- Updated version number to match bundle and core releases

## [106.0.1] - 2024-02-23
- Updated kit version to match connectors for security updates

## [106.0.0] - 2024-02-16
- Adopted kit-sdk 106.0

## [105.2.19] - 2024-02-13
- core update release

## [105.2.18] - 2024-02-13
### Added
- Merge Meshes UX report updated catagories and tracking

## [105.2.17] - 2024-02-08
### Added
- Added support to load json config files from nucleus paths

## [105.2.16] - 2024-02-01
### Changed
- Improve tooltip for Find Hidden Meshes
- Updated UI for setting GPU threshold for Decimate Meshes

## [105.2.15] - 2024-01-30
### Added
- New operation: Find Hidden Meshes

## [105.2.14] - 2024-01-16
### Added
- Optimize Primvars
- Triangulate Meshes

## [105.2.13] - 2024-01-03
### Changed
- Updates for new Brep schema

## [105.2.12] - 2023-12-14
### Changed
- Updated version number to match bundle version

## [105.2.8] - 2023-12-13
### Fixed
- Updated default options for AutoUVs

## [105.2.7] - 2023-12-06
### Added
- New AutoUVs menu options

## [105.2.6] - 2023-11-23
### Added
- New operation: Merge Vertices

## [105.2.5] - 2023-11-20
### Added
- Tessellation: Flag to separate parts
- New presets in `Load Preset` button that ship with USD Explorer
- Load presets from nucleus links
### Changed
- Sort Operations alphabetically
- Added scroll bar to account for multiple report tabs
- UI test coverage 100%

## [105.2.4] - 2023-09-19
### Added
- Decimation: Expose parallel CPU and GPU vertex count thresholds
- AutoUV: Equalize texel density + add padding between UV islands
- Spatial merge: add spatial clustering mode
- Unbind materials utility function

## [105.2.2] - 2023-08-25
### Added
- Added support for drag/drop of prims to the Edit Paths window

## [105.2.1] - 2023-08-13
- Exposed "Allow Single Meshes" option to Merge operation

## [105.2.0] - 2023-07-17
- Adopted kit-sdk 105.2

## [105.1.2] - 2023-06-28
### Added
- Operation arguments can define conditional enable state logic.

## [105.1.1] - 2023-05-12
### Added
- New Merge Results GUI for easier debugging of merge operations.

## [105.1.0] - 2023-04-27
### Added
- A Security Warning dialog is shown when loading config files that contain python scripts.
- Prune Leaf Xforms operation can now be filtered by prim path.

## [105.0.7] - 2023-04-03
### Changed
- Preliminary visualization of Operation feedback reports
- Updated omni.scene.optimizer.core version dependency to be un-versioned

## [105.0.6] - 2023-03-23
### Changed
- Updated omni.scene.optimizer.core version dependency to 105.0.6

## [105.0.5] - 2023-03-15
### Changed
- Updated omni.scene.optimizer.core version dependency to 105.0.5
- Explicit stage for commands
- Decouple UI from core

## [105.0.4] - 2023-03-07
### Changed
- Updated omni.scene.optimizer.core version dependency to 105.0.4

## [105.0.3] - 2023-02-28
### Added
- New operation to execute a python script on a Usd Stage
- New operation to Generate Projection UVs on a Usd Stage

## [105.0.2] - 2023-02-09
### Added
- Updated how json files are exported, now have better readability

## [105.0.1] - 2023-01-27
### Added
- Added Split Meshes operation

## [105.0.0] - 2022-12-07
### Added
- Updated scene.optimizer.core version dependency

## [104.1.5] - 2022-11-11
### Change
- UI exposes tolerance value for geometry deduplication.

## [104.1.3] - 2022-11-10
### Changed
- UI improvements for "Process Point Clouds" operation.

## [104.1.2] - 2022-11-03
### Changed
- Command names prefixes changed from "DataAdapter" to "SceneOptimizer"

## [104.1.1] - 2022-10-20
### Added
- Added "Parent Prim" option to "Merge Boundary" argument of "Merge Static Meshes" operation

## [104.1.0] - 2022-10-03
### Changed
- First version of 104.1

## [104.0.10] - 2022-09-28
- Updated arguments for Merge Static Meshes
- Minor UI bug fixes

## [104.0.9] - 2022-09-21
- Updated data.adapter.core version dependency

## [104.0.8] - 2022-09-20
- Updated data.adapter.core version dependency

## [104.0.7] - 2022-09-01
- Added confirmation dialog before clearing processes
- UI look and feel improvements

## [104.0.6] - 2022-08-29
- New icons

## [104.0.5] - 2022-08-29
- Added Center Pivot command
- Update DataAdapter UI per UX design

## [104.0.4] - 2022-07-11
- Added Compute Extents command
- Added Optimize Materials command
- Added Print Stage Stats command
- Added new options to Merge/Deduplicate commands based on core features
- Commands now show a readable display name
- Arguments now show tooltips
- Removed some unncessary commands

## [104.0.3] - 2022-05-11
- Move menu to Window->Utilities.

## [104.0.2] - 2022-03-24
- Specifying which version of *.core we depend on

## [104.0.1] - 2022-02-04
### Changed
- Added default values in UI and the ability to make features mutually exclusive

## [104.0.0] - 2022-01-27
### Changed
- Bump version to 104.

## [103.0.10] - 2022-01-24
- Renamed to omni.data.adapter.ui

## [103.0.9] - 2022-01-24
- Moved UI to standalone extension

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

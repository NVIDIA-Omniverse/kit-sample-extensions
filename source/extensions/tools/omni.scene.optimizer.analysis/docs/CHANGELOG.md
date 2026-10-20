# Changelog

## [110.4.1] - 2026-10-16
### Changed
- Update the exact Scene Optimizer Core dependency to its fresh signed-publication version.

## [110.4.0] - 2026-10-05
### Changed
- Updated omni.scene.optimizer.core version dependency to 110.4.0

## [110.3.0] - 2026-09-09
### Changed
- Updated omni.scene.optimizer.core version dependency to 110.3.0

## [110.2.1] - 2026-08-04
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
### Changed
- Initial version

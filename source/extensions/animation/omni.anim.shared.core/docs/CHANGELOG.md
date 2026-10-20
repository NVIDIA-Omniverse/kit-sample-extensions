# Changelog

## [Unreleased]
### Fixed
- Kit 111: `test_get_xform_node` waits, bounded, for Runtime Core to take in the prims it authors before the first Get Xform evaluation it checks. Get Xform reads the runtime scene (OVStage), and in a fresh process its first evaluation read a scene without them ("could not find the prim in ovstage").

## [110.0.1] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: declare Runtime Core and migrate animation stage access and graph nodes.

## [110.0.0] - 2025-12-18
### Fixed
- Update kit to 110 and usd to 25.11

## [109.0.2] - 2025-12-9
### Fixed
- Added missing `__init__.py` file in `python/nodes/utils/` directory to fix Python package import failures on aarch64 platform.
- Resolves ETM test failures for matrix operation nodes (DecomposeMatrix, MatrixInverse, MatrixMixer, MatrixMultiply) on ARM64.

## [109.0.1] - 2025-12-8
### Changed
- Enable ARM publishing.

## [109.0.0] - 2025-09-18
### Changed
- Add support for kit sdk 109.

## [108.0.0] - 2025-07-03
### Changed
- Add support for kit sdk 108.

## [107.0.1] - 2025-04-03
### Changed
- Add support for ARM.

## [107.0.0] - 2024-10-25
### Changed
- Add support for kit sdk 107

## [106.0.2] - 2024-10-25
### Changed
- [DHT-2161] Fix get_mesh_data error with CustomData and add to support CustomData for create_mesh

## [106.0.1] - 2024-06-19
### Changed
- Add signing.

## [106.0.0] - 2024-02-09
### Changed
- Upgrade kit-sdk from 105 to 106

## [105.9.4] - 2024-01-17
### Changed
- Fix get_prim_io to handle input bundle path without vprim

## [105.9.3] - 2024-01-15
### Changed
- Update README

## [105.9.2] - 2023-12-07
### Changed
- Release Ogn on plugin shutdown

## [105.9.1] - 2023-11-03
### Changed
- ArraySetByKeys duplicated keys support

## [105.9.0] - 2023-10-25
### Changed
- Add `omni.anim.ArraySetByKeys` node
- Retire `omni.anim.TimesamplePoints` node

## [105.8.2] - 2023-08-04
### Changed
- Add `use_online_index = true` in configuration for suppressing pipapi warning

## [105.8.1] - 2023-07-17
### Changed
- Updated OgnGetXform to fix fabric bug in later kit versions

## [105.8.0] - 2023-06-06
### Changed
- Deprecated stamp_mesh, replaced it with stamp_geom which supports basisCurves

## [105.7.2] - 2023-06-05
### Changed
- Remove omni.kit.test dependency

## [105.7.1] - 2023-05-26
### Changed
- Fix issues on UsdSkel meshes with deformer applied for Stamp Mesh - Deformation

## [105.7.0] - 2023-05-23
### Changed
- Add time code support for stamp_mesh_deformation to stamp animated UsdSkel meshes

## [105.6.0] - 2023-4-26
- Add kit_utils.get_mesh_element_size to support skel primvars for USDSkel mesh deformation stampping
- Update Mesh Data container to support to support skeletal meshes
- Update kit_utils.create_mesh to support USDSkel mesh creation

## [105.5.1] - 2023-4-19
- Tag OgnTimeSamplePoints and OgnGetXform as threadsafe

## [105.5.0] - 2023-4-19
- Rename extension to omni.anim.shared.core
- Remove autoPropertyWidget and ognNodePropertyWidget

## [105.4.0] - 2023-4-14
- Remove stageChangeHandler

## [105.3.6] - 2023-4-12
- removed anim drag/drop from omni.anim.shared. Use omni.anim.skelJoint.

## [105.3.5] - 2023-3-30
- fix get_prim_io() to use og.Controller whenever possible

## [105.3.4] - 2023-3-30
- Release Extension reference on shutodown

## [105.3.3] - 2023-3-27
- Make anim.shared not always depend on ui

## [105.3.2] - 2023-3-22
### Changed
- republish
## [105.3.1] - 2023-03-20
### Changed
- Add support for headless mode

## [105.3.0] - 2023-03-06
### Changed
- python and usd update

## [105.2.9] - 2023-02-22
### Changed
- Add usd-write tag on usd authoring nodes

## [105.2.8] - 2023-02-17
### Changed
- Add SWIPAT info

## [105.2.7] - 2022-02-17
### Changed
- Updated get_xform_input_path() to work with both attributes and relationships

## [105.2.6] - 2023-02-08
### Changed
- Fix Prox crash immediately on apply

## [105.2.5] - 2023-02-02
### Changed
- build from 105.0+master.105200

## [105.2.4] - 2023-01-17
### Changed
- Fix test configuration

## [105.2.3] - 2023-01-12
### Changed
- Get some tests to pass

## [105.2.2] - 2022-12-17
### Changed
- Add DeformerRegistry for Def-Pi node callbacks
- Add drawAffectors attribute to Def-Pi nodes
- Automate the Def-Pi menus

## [105.2.1] - 2022-11-28
### Changed
- moved omni.ui extension on top of other UI extensions to fix "omni.kit" no attribute "menu" error

## [105.2.0] - 2022-11-21
### Changed
- support headless mode

## [105.1.0] - 2022-11-14
### Changed
- Fabric and usd lib update

## [105.0.2] - 2022-11-02
### Changed
- Ignore TC CUDA based test failures

## [105.0.1] - 2022-10-28
### Changed
- Update tests

## [105.0.0] - 2022-10-20
### Changed
- Upgrade kit-sdk from 104 to 105
## [104.12.0] - 2022-10-11
### Changed
- Remove duplicated kit_utils from A2F character transfer

## [104.11.1] - 2022-9-29
### Changed
- Add new option to stamp mesh with copy primvars

## [104.11.0] - 2022-9-26
### Changed
- Add output execution port to SetXform

## [104.10.2] - 2022-9-22
### Changed
- implement iterpolation attribute copy in createMesh

## [104.10.1] - 2022-9-13
### Changed
- Documented DecomposeMatrix in omni.anim.shared ReadMe

## [104.10.0] - 2022-9-8
### Changed
- Removed deprecated OmniGraphHelper

## [104.9.0] - 2022-9-7
### Moved
- moved omni.anim.decomposeMatrix to omni.anim.shared

## [104.8.0] - 2022-9-6
### Changed
- increment for kit sdk update 104.0+release.92424

## [104.7.2] - 2022-08-04
### Changed
- Change autoPropertyWidget for renamed ComputeNode to OmniGraphNode

## [104.7.0] - 2022-7-12
### Changed
- Republish with latest kit 104 sdk to addess compatibility issue

## [104.6.13] - 2022-6-01
### Changed
- Fix Stamp mesh uv issue to include float2[] and use texcoord2f when writing

## [104.6.12] - 2022-5-18
### Changed
- ReadTime no longer created by default when creating graph

## [104.6.11] - 2022-5-17
### Changed
- Accept any texCoord primvars as uv when reading mesh

## [104.6.10] - 2022-5-17
### Changed
- Fix uvs where previously skipped when custom data is not as expected

## [104.6.9] - 2022-5-12
### Fixed
- Add a missing dependency to pass the unit test
## [104.6.8] - 2022-5-10
### Changed
- Add primvars:UVMap support when reading mesh for stamp

## [104.6.5] - 2022-03-13
### Changed
- Fixed undo when assign animation

## [104.6.4] - 2022-2-19
### Changed
- Removed toast warning message for animation assignment

## [104.6.3] - 2022-2-11
### Changed
- Better integration of Graph evaluation type
- Default to LazyGraph
- Remove Xform node

## [104.6.2] - 2022-2-9
### Changed
- Fix Typo

## [104.6.1] - 2022-2-7
### Changed
- Switch to ReadTime node

## [104.6.0] - 2022-2-4
### Changed
- Deprecate global implicit graph

## [104.5.2] - 2022-1-25
### Changed
- version up to 104

## [103.5.2] - 2022-01-11
### Changed
- Update kit sdk to 70123

## [103.5.1] - 2021-10-04
### Changed
- Add test for get_xform set_xform point_timesampe time_node

## [103.5.0] - 2021-09-28
### Changed
- Add omni.anim.TimesamplePoints node

## [103.4.3] - 2021-09-27
### Changed
- Update Kit SDK to 60126

## [103.4.2] - 2021-08-25
### Changed
- Update Kit SDK to 55256

## [103.4.1] - 2021-08-13
### Changed
- Update Kit SDK to 53790

## [103.3.2] - 2021-7-29
### Changed
- Add omni.kit.renderer.core to test dependency

## [103.3.1] - 2021-7-14
### Changed
- Update Kit SDK to 49389

## [103.3.0] - 2021-06-16
### Changed
- Version update to match Update 103 Kit SDK

## [102.3.0] - 2021-06-07
### Changed
- Converted MatrixConstrain to use bundles

## [102.2.0] - 2021-06-01
### Changed
- Rename omni.anim.getXform to omni.anim.GetXform
- Rename omni.anim.matrix_constraint to omni.anim.MatrixConstraint
- Rename omni.anim.matrix_inverse to omni.anim.MatrixInverse
- Rename omni.anim.matrix_mixer to omni.anim.MatrixMixer
- Rename omni.anim.matrix_multiply to omni.anim.MatrixMultiply

## [102.1.0] - 2021-05-28
### Added
- Set package target
- Add kit_utils.py

## [102.0.7] - 2021-05-12
### Changed
- Update Kit SDK to 40726

## [102.0.6] - 2021-05-05
### Changed
- Update Kit SDK to 39243

## [101.0.7] - 2021-05-05
### Fixed
- cpu to gpu update bug
### Added
- icon.png

## [101.0.6] - 2021-04-16
### Fixed
- Fixed a bug input time is directly used as time code.

## [101.0.5] - 2021-03-31
### Changed
- get_xform nodetype changed to omni.anim.getXform

## [101.0.4] - 2021-03-30
### Added
- get_xform Ogn node

## [101.0.3] - 2021-03-08
### Changed
- Updating Kit SDK to 31180

## [101.0.2] - 2020-02-25
### Changed
- SDK Update

## [101.0.1] - 2020-02-01
### Changed
- SDK Update

## [101.0.0] - 2020-01-22
### Changed
- Version Update

## [0.1.2] - 2021-01-13
### Added
- XformQuery node to get world matrix of a prim
- MatrixMultiply node to multiply two matrices
- MatrixInverse node to invert a matrix
- MatrixMixer node to interpolate between two matrices
- MatrixConstraint node to set the world matrix of a prim
- Matrix utilities for composing and decomposing matrices
- An example usda file constraining one object between two others, using the nodes in this extension.

## [0.1.1] - 2020-12-01
### Changes
- SDK update

## [0.1.0] - 2020-11-16
### Changes
- Initially create.

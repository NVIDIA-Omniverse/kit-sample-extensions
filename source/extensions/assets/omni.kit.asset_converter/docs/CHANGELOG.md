# Changelog

## [6.1.5] - 2026-10-17

### Changed

- Republish through the verified Windows signing path with signed package metadata.

## [Unreleased]
- Kit 111 (Linux) workaround: install FBX SDK allocator handlers with a 16-byte minimum alignment at startup, so FBX animation is not lost under Kit's mimalloc. Native library built from usd-convert-asset-internal#6's `fbx_allocator.cpp`; skipped when the staged converter already has that fix. Remove at the pin bump to the first usd-convert-asset 9.2.x with #6.

## [6.1.4] - 2026-10-16
### Changed
- Give the existing Kit 111 compatibility changes a distinct package version: deliver the FBX allocator workaround and its native library loading integration.

## [6.1.0] - 2026-09-04
- Added `SUPPRESS_PXR_CONFLICT_WARNING` environment variable to suppress the expected OpenUSD conflict warning
- Explicitly set the subdivision scheme to `none` on exported meshes, including empty meshes
- Reject negative and out-of-range face-vertex indices during USD import
- Abort USD export when an external material or texture file copy fails
- Export JPEG textures with the validator-compatible `.jpg` extension
- Remove unreferenced mesh points and remap related vertex and skin data
- Remove unreferenced indexed UV values
- Skip empty meshes after mesh compaction
- Author normalized, winding-consistent face-varying normals during USD mesh export
- Preserve valid FBX NURBS curves as `UsdGeomNurbsCurves`, with explicit closed/periodic control points; skip and log malformed curves
- Report FBX NURBS curves rejected during USD export instead of silently losing them
- Deduplicate repeated display-color and UV primvar values while preserving face-varying corner data
- Remove zero-area faces
- Support Unicode texture file paths on Windows

## [6.0.6] - 2026-08-18
- Normalize imported texture path separators before texture lookup and USD export.
- Explicitly register the Asset Converter USD plugins during extension startup.

## [6.0.5] - 2026-07-29
- Updated to Asset Converter 9.1.1

## [6.0.4] - 2026-07-21
- Updated to Asset Converter 9.0.22
- Improved error handling and logging for unsupported file formats and pxr (OpenUSD) import conflicts in the native converter.

## [6.0.3] - 2026-07-06
- Fixed out of bounds heap read on unclamped .obj

## [6.0.2] - 2026-06-02
- Update to Asset Converter 9.0.17

## [6.0.1] - 2026-06-02
- Update kit-kernel to version 110.1.1

## [6.0.0] - 2026-05-29
- Updated to Asset Converter 9.0.13

## [5.1.4] - 2026-04-14
- Updated kit-kernel to version 110.1

## [5.1.3] - 2026-04-13
- Updated to Asset Converter 8.0.0

## [5.1.2] - 2026-03-18
- Removed unit test warnings and improved assertion logging
- Update kit-kernel version

## [5.1.1] - 2025-12-23
- Added WebP texture support for GLTF conversion

## [5.1.0] - 2025-12-16
- Added OpenUSD-25.11 / Python 3.12 flavor
- Updated draco to v1.5.6
- Updated tiny_gltf to v2.9.7
- Updated stb_image to v2.28
- Updated stb_image_write to v1.16
- Updated json.hpp to v3.10.4

## [5.0.25] - 2025-12-11
- Use FbxSdk allocation routines to enforce 16-byte alignment if mimalloc is used
- Enable FBX animation conversion test
- Enable tinygltf loader on linux-aarch64

## [5.0.24] - 2025-12-09
- Disable flaky test to resolve ETM failure.

## [5.0.23] - 2025-12-05
- Added FBX animation conversion test case

## [5.0.22] - 2025-11-12
- Fix crash in USD to STL export when USD file contains no materials or when IgnoreMaterials() is enabled

## [5.0.21] - 2025-10-30
- Fix out of bound access to materials for fbx importer

## [5.0.20] - 2025-10-21
- Fix crash in Assimp exporter when STL export fails due to no valid triangular meshes
- Improve STL export error messages to include names of skipped meshes with non-triangular faces

## [5.0.19] - 2025-10-20
- Improve STL export error handling and mesh skipping logic in Assimp exporter
- Fix incorrect FBX animation rotation

## [5.0.18] - 2025-10-14
- Add third party notices

## [5.0.17] - 2025-10-09
- Fix obj conversion on linux-aarch64
- Fix obj material mapping

## [5.0.16] - 2025-09-08
- Fix scaling for Collada files
- Update to libxml2 2.14.5

## [5.0.15] - 2025-08-28
- Fix root transform for Z_UP Collada files

## [5.0.14] - 2025-08-19
- Publish for `windows-x86_64`, `linux-x86_64`, and `linux-aarch64` platforms

## [5.0.13] - 2025-08-14
- Improve unit test code coverage

## [5.0.12] - 2025-08-08
- Normalize absolute paths for OBJ material libraries
- Published for `windows-x86_64` and `linux-x86_64` platforms only

## [5.0.11] - 2025-08-05
- Update to libxml2 2.14.4

## [5.0.10] - 2025-08-01
- Include windows import library.

## [5.0.9] - 2025-07-31
- Include omniverse_asset_converter.h in extension package.

## [5.0.8] - 2025-07-30
- mesh regression fix

## [5.0.7] - 2025-07-30
- Exclude FBX tests on linux-aarch64 as it's unsupported.

## [5.0.6] - 2025-07-29
- Kit 106.5 build flavor

## [5.0.5] - 2025-07-29
- Only create normals attribute for UsdGeomPoints if normals are nonzero

## [5.0.4] - 2025-07-14
- Use the release binary for assimp

## [5.0.3] - 2025-07-01
- Build flavors

## [5.0.2] - 2025-06-16
- Fix collisions of USD layer names
- Ensure prim type is set to 'Mesh' for prototype mesh prims

## [5.0.1] - 2025-06-13
- Update fbxsdk to 2020.3.7

## [5.0.0] - 2025-05-14
- Update to Kit 108, USD 25.02, and Python 3.12

## [4.1.3] - 2025-06-11
- Fix crash when shutdown

## [4.1.2] - 2025-06-03
- Clean up extension documentation

## [4.1.1] - 2025-05-02
- Fix omni.kit.asset_converter test in OVC2.

## [4.1.0] - 2025-04-29
- Add support for linux-aarch64

## [4.0.5] - 2025-04-21
- Update to libxml2 2.14.1

## [4.0.4] - 2025-03-21
- Update kit-kernel

## [4.0.3] - 2025-03-21
- Update Support Level from Enterprise to Core

## [4.0.2] - 2025-03-19
- Update libxml2 to 2.13.6

## [4.0.1] - 2025-02-12
- Remove dependency of legacy viewport omni.kit.window.viewport

## [4.0.0] - 2025-02-05
- Switch to new ABI

## [3.0.6] - 2025-01-29
- Disable neuray tests

## [3.0.5] - 2025-01-24
- Enable tests since they are fixed by kernel 107.0.3.

## [3.0.4] - 2025-01-14
- Fix crash when converting mesh without face or vertex data

## [3.0.3] - 2025-01-03
- Update to kit-kernel 107.0.3

## [3.0.2] - 2025-01-02
- Disable tests related to Neuray libs

## [3.0.1] - 2024-12-13
- Update to Kit Kernel 107

## [3.0.0] - 2024-11-12
- Update to Kit 107

## [2.8.0] - 2024-11-26
- Update assimp to 5.4.3 and fix obj export.

## [2.7.0] - 2024-11-25
- Update assimp to 5.2.5

## [2.6.0] - 2024-11-21
- Update and clean up dependencies.

## [2.5.0] - 2024-11-20
- Update to Kit-kernel 106.5

## [2.4.0] - 2024-11-18
- Update omniverse-asset-converter for new assimp, fbxsdk and zlib

## [2.3.1] - 2024-10-18
- Target specific Kit version

## [2.3.0] - 2024-10-16
- Update to latest Kit 106.4

## [2.2.0] - 2024-10-03
- Added stage up-axis options for using the imported asset's up-axis for the USD stage's up-axis or overriding it with Y-up or Z-up; added combobox (drop-down menu) for selecting the up-axis

## [2.1.23] - 2024-09-11
- Fix for data structure storing joint nodes to set common root node
- Fix for calculating rest transform for non-root bones

## [2.1.22] - 2024-09-06
- Apply OMNI_CONVERTER_FLAGS_USE_METER_PER_UNIT flag in obj import

## [2.1.21] - 2024-08-13
- Fix for parsing diffuse colors

## [2.1.20] - 2024-08-12
- Fix ETM failure for omni.kit.asset_converter on release/106.0.

## [2.1.19] - 2024-08-08
- Update OmniverseAssetConverter library to ...
- Update iray-for-omniverse lib in OmniverseAssetConverter
- Fix export of MDL materials with body UDIM textures to glTF NV_materials_mdl.

## [2.1.18] - 2024-07-26
- Fix copying to existing file paths with Omni Client

## [2.1.17] - 2024-07-26
- Update OmniverseAssetConverter library to f465d20e-custom,.
- Fix EXCEPTION_ACCESS_VIOLATION_READ: check for nullptr if triangulate fails
- Fix ETM failure.

## [2.1.16] - 2024-07-24
- Update OmniverseAssetConverter library to 3fa2cc7d4-custom, include following fixes.
- Fix crash when processing invalid skin inverseBindMatrices.
- Remove extra "0" from the SkelRoot name.
- Update libxml2 lib in asset-converter

## [2.1.15] - 2024-07-13
- Fix ETM failure for omni.kit.asset_converter on release/106.0.

## [2.1.14] - 2024-07-11
- Reduce size of test texture data

## [2.1.13] - 2024-07-10
### Fixed
- Make omni.mdl.neuraylib.utils optional to fix for Kit 106.

## [2.1.12] - 2024-07-08
- Update OmniverseAssetConverter library to 19dc192ae-custom.
- Fix export of MDL materials with body textures to glTF NV_materials_mdl.
- Add more test cases for glTF NV_materials_mdl.

## [2.1.11] - 2024-05-14
### Fixed
- Update asset converter to 8.0.1618 to fix unicode strings cannot be imported properly.

## [2.1.10] - 2024-05-01
- Fix signing of binaries.

## [2.1.9] - 2024-04-18
- Add enterprise tag.

## [2.1.8] - 2024-03-25
- Update asset converter to 8.0.1599 for more fixes to export obj with materials.

## [2.1.7] - 2024-03-21
- Update asset converter to 8.0.1595 to fix albedo color export from USD to other formats.

## [2.1.6] - 2024-03-20
- Update OmniverseAssetConverter library to 8.0.1589.
- Add test cases for glTF NV_materials_mdl import/export.

## [2.1.5] - 2024-03-15
- Fix ETM tests issue for Kit 107 that cannot run omni.client.write_file_async from non-main loop.

## [2.1.4] - 2024-03-13
- Update OmniverseAssetConverter library to 8.0.1584.
- Refactor import/export of NV_materials_mdl to use rtx.neuraylib.NeurayLib functions.

## [2.1.3] - 2024-01-17
- Update OmniverseAssetConverter library to 8.0.1565.
- In fbx importer, treat null node as a special bone node for blender exported fbx files.
- Improve gltf import emissive strength and mesh color with float value.

## [2.1.2] - 2023-12-07
- Update OmniverseAssetConverter library to 8.0.1547 to fix gltf opacity.

## [2.1.1] - 2023-11-03
- Remove extension disable/enable tests to fix ETM.

## [2.1.0] - 2023-11-01
- Bump ext minor version.

## [2.0.18] - 2023-10-12
### Changed
- Delay manager start up to reduce extension's startup time.

## [2.0.17] - 2023-10-06
### Changed
- Increase code coverage.

## [2.0.16] - 2023-09-21
### Changed
- Update OmniverseAssetConverter library to 8.0.1532.
- Add support for NV_materials_mdl glTF vendor extension.

# [2.0.15] - 2023-08-31
- Added `writeable` function to `omni_client_wrapper` to check destination path is writeable before converting.

## [2.0.14] - 2023-08-23
### Changed
- Update OmniverseAssetConverter library to 8.0.1512.
- Fix file format plugin to use correct extentions and formatId.

## [2.0.13] - 2023-08-21
### Changed
- Update OmniverseAssetConverter library to 8.0.1506 to support FBX file that's over 2G.

## [2.0.12] - 2023-07-11
### Changed
- Add context param to control gltf export separate bin file.

## [2.0.11] - 2023-07-11
### Fixed
- Update OmniverseAssetConverter library to 8.0.1465, the new lib include following update
- Make sure gltf color adapter array index will not go out of bounds
- Use texCoord2f instead of float2f for uv data type
- GLTF point/normal cache to morph target, fix issues with gltf exporter
- Fix the fps for the fbx point cache animation import
- Add a context flag to control export embedded or separate gltf
- Populate baked preview surface material before populate mdl material

## [2.0.10] - 2023-07-11
### Fixed
- Fix linux test failed.

## [2.0.9] - 2023-07-04
### Fixed
- Lstrip convert path to fix export fbx pointcache animation.

## [2.0.8] - 2023-06-08
### Changed
- Update OmniverseAssetConverter library to 8.0.1438.

## [2.0.7] - 2023-06-07
### Changed
- Update OmniverseAssetConverter library to 8.0.1418.
- Ability to preserve original skeleton when converting from FBX to USD

## [2.0.6]
### Changed
- Bump version to republish

## [2.0.5] - 2023-04-18
### Changed
- Update OmniverseAssetConverter library to 8.0.1404.
- Fix the gltf not export correct mesh color issue.

## [2.0.4] - 2023-03-28
### Changed
- Update OmniverseAssetConverter library to 8.0.1397.
- Fix the fbx animation's order rotation value.

## [2.0.3] - 2023-03-21
### Changed
- Update OmniverseAssetConverter library to 8.0.1392.
- Filter the fbx animation's horizontal/reverse rotation value.

## [2.0.2] - 2023-03-20
### Changed
- Update OmniverseAssetConverter library to 8.0.1389 to fix a crash of assimp exporter.

## [2.0.1] - 2023-03-13
### Changed
- Add writeTarget.python into config to ensure py tag appended to package name.

## [2.0.0] - 2023-03-11
### Changed
- Update OmniverseAssetConverter library to 8.0.1378 for USD 22.11 and python310 support.

## [1.3.6] - 2023-03-09
### Changed
- Update OmniverseAssetConverter library to 7.0.1367.
- Fix normal issue with left-hand.

## [1.3.5] - 2023-02-21
### Changed
- Update OmniverseAssetConverter library to 7.0.1365.
- Fix gltf vertex colors.

## [1.3.4] - 2023-02-02
### Changed
- Fix issue to convert assets in parallel.

## [1.3.3] - 2023-01-30
### Changed
- Update OmniverseAssetConverter library to 7.0.1355.
- Fix issue to save layer to Nucleus when there are spaces in the path.

## [1.3.2] - 2023-01-16
### Changed
- Update OmniverseAssetConverter library to 7.0.1348.
- Fix export nonskinned skeleton bone missing.
- Keep the points index for obj file import.
- Improve path utils to handle local paths.
- Add FBX and OBJ into extension list as format plugin is case-sensitive.

## [1.3.1] - 2023-01-12
### Changed
- Add `asset_converter_native_bindings` to python modules list

## [1.3.0] - 2022-12-21
### Changed
- Update OmniverseAssetConverter library to 7.0.1333.
- 10x speed up to usd exporter.
- Fix default prim issue after importing from File menu.

## [1.2.41] - 2022-12-21
### Changed
- Fix hang of unittests for kit 105.

## [1.2.40] - 2022-12-12
### Changed
- Update OmniverseAssetConverter library to 7.0.1321 to use original frames and fps when import fbx to fix interpolation Euler angles.

## [1.2.39] - 2022-10-26
### Changed
- Update OmniverseAssetConverter library to 7.0.1303 to fix uv export of FBX when there are multi-subsets.

## [1.2.38] - 2022-10-11
### Changed
- Update OmniverseAssetConverter library to 7.0.1301 to avoid export fallback color for obj import.

## [1.2.37] - 2022-10-07
### Changed
- Update OmniverseAssetConverter library to 7.0.1300 to fix path resolve issue under linux when it's to reference glTF directly.

## [1.2.36] - 2022-09-08
### Changed
- Add support for BVH file imports.
- Update OmniverseAssetConverter library to 7.0.1293.

## [1.2.35] - 2022-09-03
### Changed
- Update tests to pass for kit 104.

## [1.2.34] - 2022-09-01
### Changed
- Update OmniverseAssetConverter library to 7.0.1289.
- Fix export crash caused by invalid normal data from usd.
- Merge skeletons for glTF to have single skeleton.

## [1.2.33] - 2022-08-05
### Changed
- Update OmniverseAssetConverter library to 7.0.1286.
- Fix issue of material naming conflict during USD export.
- Export kind for root node during USD export.
- Fix crash of exporting USD into OBJ caused by mal-formed USD data.

## [1.2.32] - 2022-07-22
### Changed
- Update OmniverseAssetConverter library to 7.0.1270.
- Fix hang of USD plugin to reference glTF from server.
- Improve glTF light import/export.

## [1.2.31] - 2022-06-07
### Changed
- Update OmniverseAssetConverter library to 7.0.1258.
- Fix some glb file cause crashs in importer.

## [1.2.30] - 2022-05-19
### Changed
- Update OmniverseAssetConverter library to 7.0.1253.
- Support to pass file argument for specifying meter as world unit.
- Improve file format plugin to import asset with original units instead of baking scalings.

## [1.2.29] - 2022-05-19
### Changed
- Update OmniverseAssetConverter library to 7.0.1250 to fix issue of converting assets to local path under linux.

## [1.2.28] - 2022-05-16
### Changed
- Update OmniverseAssetConverter library to 7.0.1245
- Fix fbx animation rotation
- Optimize uv export to fix texture load not properly

## [1.2.27] - 2022-05-12
### Changed
- Update OmniverseAssetConverter library to 7.0.1237 to fix pdb name issue for assimp library.

## [1.2.26] - 2022-05-07
### Changed
- Fix tests to make sure it will not fail for 103.1 release.

## [1.2.25] - 2022-05-04
### Changed
- Update OmniverseAssetConverter library to 7.0.1236.
- Support fbx uv indices's import and export.
- Support export lights for gltf.

## [1.2.24] - 2022-04-19
### Changed
- Update OmniverseAssetConverter library to 7.0.1225.
- Fix naming issue of obj import if mesh names are empty.
- Fix color space setup for material loader.
- Fix geometric transform import for FBX.

## [1.2.23] - 2022-04-12
### Changed
- Update OmniverseAssetConverter library to 7.0.1219 to support dissovle attribute of MTL for obj importer.

## [1.2.22] - 2022-03-30
### Changed
- Bump version to update licensing build.

## [1.2.21] - 2022-03-29
### Changed
- Supports option to close current stage with import to avoid multi-threading issue if output path is opened already.

## [1.2.20] - 2022-03-28
### Changed
- Update OmniverseAssetConverter library to 7.0.1201 to support option to bake scales for FBX import.

## [1.2.19] - 2022-03-09
### Changed
- Update OmniverseAssetConverter library to 7.0.1197 to improve pivots support for exporter.
- Fix issue that exports USD with pivots to gltf/obj.

## [1.2.18] - 2022-03-08
### Changed
- Update OmniverseAssetConverter library to 7.0.1192 to support to control hidden props export for USD exporter.

## [1.2.17] - 2022-03-04
### Changed
- Update OmniverseAssetConverter library to 7.0.1191 to improve animation import for FBX.
- Fix issue of skeletal mesh import when skeleton is not attached to root node.
- Fix issue of skeletal mesh if its joints is not provided, which should use global joints instead.
- Fix crash of skeleton import if skeleton removed and skinning is still existed.
- Fix issue of FBX importer that has possible naming conflict of nodes.
- Supports to export all instances into single USD for DriveSim usecase.
- Supports options to disable scene instancing for DriveSim usecase.

## [1.2.16] - 2022-02-22
### Changed
- Update OmniverseAssetConverter library to 7.0.1171 to improve multiple animation tracks import/export.

## [1.2.15] - 2022-02-16
### Changed
- Update OmniverseAssetConverter library to 7.0.1161 to remove instancing flag if glTF/glb is opened directly with file format plugin so it could be editable.

## [1.2.14] - 2022-02-15
### Changed
- Update OmniverseAssetConverter library to 7.0.1159 to fix a crash of fbx importer that accesses invalid attributes.

## [1.2.13] - 2022-02-15
### Changed
- Update OmniverseAssetConverter library to 7.0.1157 to improve glTF loading performance through file format plugin.

## [1.2.12] - 2022-02-13
### Changed
- Update OmniverseAssetConverter library to 7.0.1150 to fix a FBX exporter crash that's caused by empty uv set.

## [1.2.11] - 2022-02-11
### Changed
- Update OmniverseAssetConverter library to 7.0.1149 to fix a FBX exporter issue that ignores props under root node.

## [1.2.10] - 2022-02-11
### Changed
- Fix API docs.

## [1.2.9] - 2022-02-10
### Changed
- Update OmniverseAssetConverter library to 7.0.1148 to fix a crash caused by exporting obj files without materials.

## [1.2.8] - 2022-02-08
### Changed
- Update OmniverseAssetConverter library to 7.0.1145 to fix a crash that's caused by invalid path that includes "%" symbols.

## [1.2.7] - 2022-02-07
### Changed
- Update OmniverseAssetConverter library to 7.0.1143 to improve USD exporter to exclude proxy and guide prims.

## [1.2.6] - 2022-02-07
### Changed
- Update OmniverseAssetConverter library to 7.0.1142 to fix glTF import.
- Uses default mime type based on extension name if it's not specified for textures.
- Fix transparent material import.

## [1.2.5] - 2022-01-11
### Changed
- Update OmniverseAssetConverter library to 7.0.1138 to fix a regression to import assets to OV.

## [1.2.4] - 2022-01-09
### Changed
- Update OmniverseAssetConverter library to 7.0.1136.
- Re-org skeletal animation.
- Fix transform issue of obj export.
- Improve export for FBX assets exported from Substance Painter to avoid exporting separate parts for the same mesh.

## [1.2.3] - 2021-12-30
### Changed
- Update OmniverseAssetConverter library to 7.0.1127 to export obj model as meshes instead of group of subsets so subsets can be pickable.

## [1.2.2] - 2021-12-29
### Changed
- Update OmniverseAssetConverter library to 7.0.1123 to use tinyobj for obj import.

## [1.2.1] - 2021-12-23
### Changed
- Update OmniverseAssetConverter library to 7.0.1117 to support override file copy to speed up copying file.
- More optimization to avoid redundant IO to speed up glTF import.

## [1.2.0] - 2021-12-16
### Changed
- Update OmniverseAssetConverter library to 7.0.1115 to improve exporter.
- Replace assimp with tinygltf for glTF import/export.
- Refactoring stage structure to improve animation export.
- Refactoring stage structure to support scene instancing.
- Lots of improvement and bugfixes.

## [1.1.43] - 2021-12-01
### Changed
- Update OmniverseAssetConverter library to 7.0.1061 to rotation order issue of FBX import.
- Add option to control pivots generation.
- Use euler angles for rotation by default for FBX import.

## [1.1.42] - 2021-10-09
### Changed
- Update OmniverseAssetConverter library to 7.0.1041 to fix memory leak, and improve uv set import.

## [1.1.41] - 2021-10-08
### Changed
- Update OmniverseAssetConverter library to 7.0.1040 to fix opacity map export issue of FBX importer.

## [1.1.40] - 2021-10-06
### Changed
- Update OmniverseAssetConverter library to 7.0.1039 to improve exporter.

## [1.1.39] - 2021-09-30
### Changed
- Update initialization order to make sure format plugin loaded correctly.

## [1.1.38] - 2021-09-23
### Changed
- Update OmniverseAssetConverter library to 7.0.1024 to fix color space import of textures.

## [1.1.37] - 2021-09-22
### Changed
- Update OmniverseAssetConverter library to 7.0.1020 to improve exporter.
- Supports to import/export glTF from/to UsdPreviewSurface and glTF MDL.
- Supports to export USDZ to glTF.

## [1.1.36] - 2021-09-12
### Changed
- Update OmniverseAssetConverter library to 7.0.1012 to integrate latest glTF MDL to support transmission/sheen/texture transform extensions.

## [1.1.35] - 2021-09-07
### Changed
- Update OmniverseAssetConverter library to 7.0.1007 to use translate/orient/scale for transform to fix interpolation issues of animation samples of assimp importer.
- Fix camera import of assimp importer.
- Improve and fix rigid/skeletal animation import for glTF.

## [1.1.34] - 2021-09-03
### Changed
- Update OmniverseAssetConverter library to 7.0.1002 to fix crash caused by invalid memory access.

## [1.1.33] - 2021-09-03
### Changed
- Update OmniverseAssetConverter library to 7.0.999 to improve glTF import.
- Fix material naming conflict for glTF import for USD exporter.
- Fix tuple property set for material loader.

## [1.1.32] - 2021-09-01
### Changed
- Update OmniverseAssetConverter library to 7.0.989 to reduce artifacts size for linux.

## [1.1.31] - 2021-09-01
### Changed
- Update OmniverseAssetConverter library to 7.0.988 to fix linux build caused by DRACO symbol conflict between assimp and USD.

## [1.1.30] - 2021-08-30
### Changed
- Update OmniverseAssetConverter library to 7.0.984 to support import material as UsdPreviewSurface.
- Enable support to import draco compressed meshes of glTF.

## [1.1.29] - 2021-08-09
### Changed
- Update OmniverseAssetConverter library to 7.0.962 to support export non-skinned skeleton.

## [1.1.28] - 2021-08-05
### Changed
- Update OmniverseAssetConverter library to 7.0.961 to fix camera animation issue.

## [1.1.27] - 2021-07-27
### Changed
- Update OmniverseAssetConverter library to 7.0.956 to check invalid mesh to avoid crash.

## [1.1.26] - 2021-07-22
### Changed
- Update AssetConverterContext to support a to_dict() function.

## [1.1.25] - 2021-07-10
### Changed
- Update OmniverseAssetConverter library to 7.0.950 for better glTF material import support.

## [1.1.24] - 2021-06-09
### Fixes
- Use copy on overwrite to avoid removing file firstly for files upload.

## [1.1.23] - 2021-06-07
### Changed
- Update OmniverseAssetConverter library to 7.0.943 to fix default prim issue of animation clip import.

## [1.1.22] - 2021-06-02
### Changed
- Add param for converter context to customize precision of USD transform op.

## [1.1.21] - 2021-06-02
### Changed
- Update OmniverseAssetConverter library to 7.0.942 for supporting customizing precision of USD transform op.

## [1.1.20] - 2021-05-25
### Changed
- Update OmniverseAssetConverter library to 7.0.941 for more glTF import improvement.

## [1.1.19] - 2021-05-10
### Changed
- Update OmniverseAssetConverter library to 7.0.933 to support pivot.

## [1.1.18] - 2021-05-07
### Changed
- Update OmniverseAssetConverter library to 7.0.928 to fix and improve glTF export.
- Add glb import/export support.
- Add embedding textures support for glTF/glb export support.

## [1.1.17] - 2021-05-06
### Changed
- Update OmniverseAssetConverter library to 7.0.925 to fix and improve glTF import.
- Shorten library search path to mitigate long path issue.
### Fixes
- Fix camera import and export issue.
- Fix OmniPBR material export issue for FBX.

## [1.1.16] - 2021-05-05
### Changed
- Update assimp to latest.
### Fixes
- Fix crash to import cameras from glTF.

## [1.1.15] - 2021-05-04
### Changed
- Update OmniverseAssetConverter library to 7.0.916 to provide WA for supporting pivots from FBX files.

## [1.1.14] - 2021-04-28
### Changed
- Update OmniverseAssetConverter library to 7.0.914 to include float type support and fix default/min/max issue of material loader.

## [1.1.13] - 2021-04-12
### Fixes
- Fix the crash to import FBX file that's over 2GB.

## [1.1.12] - 2021-03-30
### Changed
- Update extension icon.
- Remove extension warning.

## [1.1.11] - 2021-03-29
### Changed
- Support to merge all static meshes if they are under the same transform and no skin meshes are there.

## [1.1.10] - 2021-03-24
### Fixes
- Fix anonymous USD export.
- Fix crash of empty stage export to OBJ.

## [1.1.9] - 2021-03-24
### Fixes
- Fix texture populates for FBX that's referenced by property of texture object.

## [1.1.8] - 2021-03-23
### Changed
- Improve material export to display all material params for Kit editing.

## [1.1.7] - 2021-03-19
### Changed
- Shorten the length of native library path to avoid long path issue.

## [1.1.6] - 2021-03-06
### Changed
- Improve texture uploading to avoid those that are not referenced.

## [1.1.5] - 2021-03-05
### Changed
- Support to remove redundant materials that are not referenced by any meshes.

## [1.1.4] - 2021-02-20
### Fixes
- Fix issue that exports timesamples when it has no real transform animation.

## [1.1.3] - 2021-02-19
### Fixes
- More fixes to long path issue on windows.

## [1.1.2] - 2021-02-18
### Fixes
- Shorten the path length of native libraries to fix long path issue.

## [1.1.1] - 2021-02-16
### Fixes
- Fix obj export crash when there are no materials.

## [1.1.0] - 2021-02-15
### Changed
- Separate asset converter from Kit as standalone repo.

## [1.0.1] - 2021-01-26
### Changed
- Add animation export for FBX export.
- Add options to support embedding textures for FBX export

### Fixes
- Fix opacity map import/export for fbx.
- Animation import fixes.

## [1.0.0] - 2021-01-19
### Changed
- Initial extension from original omni.kit.tool.asset_importer.

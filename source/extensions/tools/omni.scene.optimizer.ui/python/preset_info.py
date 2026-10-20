# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


__all__ = [
    "get_preset_info_for_execution_context",
]

import omni.kit.commands


def get_preset_info_for_execution_context():
    """Get the preset configuration info for context options"""
    _preset = list()

    # This preset sets instancable on applicable references, computes extents, Creates UVs for no UV prims, removes duplicate
    # time samples, and prunes leaf xforms
    _preset.append(
        {
            "name": "apollo_connector_default",
            "displayName": "Modify Instances - Clean Prototypes",
            "arguments": [
                {"operation": "utilityFunction", "paths": [], "function": 3},
                {"operation": "computeExtents", "meshPrimPaths": []},
                {
                    "operation": "generateProjectionUVs",
                    "paths": [],
                    "projectionType": 4,
                    "useWorldSpaceScales": True,
                    "scaleFactor": 0.01,
                    "overwriteExisting": False,
                },
                {
                    "operation": "optimizeTimeSamples",
                    "paths": [],
                    "removeInterpolated": True,
                    "epsilonD": 1e-12,
                    "epsilonF": 1e-06,
                },
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
            ],
        }
    )

    # This preset sets instancable on applicable references, computes extents, Creates UVs for no UV prims, removes duplicate
    # time samples, and prunes leaf xforms
    _preset.append(
        {
            "name": "merge_instance_meshes",
            "displayName": "Modify Instances - Merge Meshes",
            "arguments": [
                {
                    "operation": "merge",
                    "meshPrimPaths": ["//Components", "//Prototypes", "//FamilyData", "//Meshes", "//Mesh_Originals"],
                    "considerMaterials": True,
                    "materialAlbedoAsVertexColors": False,
                    "originalGeomOption": 1,
                    "mergePoint": 4,
                    "rootPath": "merged_mesh",
                    "considerAllAttributes": False,
                    "allowSingleMeshes": False,
                    "spatialMode": 0,
                },
                {
                    "operation": "pruneLeaves",
                    "paths": ["Components", "Prototypes", "FamilyData", "Meshes", "Mesh_Originals"],
                    "pruneMode": 0,
                },
            ],
        }
    )

    # This preset deduplicates materials, center pivots, deduplicate geometry, and prune leaf xforms
    _preset.append(
        {
            "name": "dgp",
            "displayName": "Modify Stage - Deduplicate Materials and Meshes",
            "arguments": [
                {"operation": "optimizeMaterials", "materialPrimPaths": [], "optimizeMaterialsMode": 0},
                {"operation": "pivot", "meshPrimPaths": []},
                {
                    "operation": "deduplicateGeometry",
                    "meshPrimPaths": [],
                    "considerDeepTransforms": True,
                    "tolerance": 0.001,
                    "duplicateMethod": 2,
                    "fuzzy": False,
                    "useGpu": False,
                    "allowScaling": False,
                },
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
            ],
        }
    )

    # This preset deudplicates materials, runs a python script to move all materials to /Looks path
    # (excluding /Environment materials), and prune leaf xforms.
    _preset.append(
        {
            "name": "move_material_looks",
            "displayName": "Modify Stage - Move Materials to /Looks",
            "arguments": [
                {"operation": "optimizeMaterials", "materialPrimPaths": [], "optimizeMaterialsMode": 0},
                {"operation": "moveMaterials", "materialsPath": "/World/Looks", "makeRootDefault": True},
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
            ],
        }
    )

    # This preset deduplicates materials, move materials to /Looks, de-instance, merge, delete hidden, prune leaves,
    # set pivots
    _preset.append(
        {
            "name": "merge_extreme",
            "displayName": "Modify Stage - Merge Meshes",
            "arguments": [
                {
                    "operation": "utilityFunction",
                    "paths": [],
                    "function": 0,
                },
                {"operation": "optimizeMaterials", "materialPrimPaths": [], "optimizeMaterialsMode": 0},
                {"operation": "moveMaterials", "materialsPath": "/World/Looks", "makeRootDefault": True},
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
                {
                    "operation": "merge",
                    "meshPrimPaths": [],
                    "considerMaterials": True,
                    "materialAlbedoAsVertexColors": False,
                    "originalGeomOption": 1,
                    "mergePoint": 7,
                    "rootPath": "Geometry/Merged/merged_mesh",
                    "considerAllAttributes": False,
                    "allowSingleMeshes": True,
                    "spatialMode": 0,
                },
                {"operation": "deleteHiddenPrims"},
                {"operation": "removeUntypedPrims"},
                {
                    "operation": "pythonScript",
                    "python": "IyMgUmVtb3ZlIHVudHlwZWQgcHJpbXMKIyMjIyMjIyMjIyMjIyMjIyMjIwoKaW1wb3J0IG9tbmkudXNkCmZyb20gcHhyIGltcG9ydCBVc2QsIFVzZEdlb20sIFNkZgoKc3RhZ2UgPSBvbW5pLnVzZC5nZXRfY29udGV4dCgpLmdldF9zdGFnZSgpCmhpZGRlbl9wcmltX3BhdGhzID0gW10KCiMgRG9lcyBub3QgaW5jbHVkZSBpbnN0YW5jZSBwcm94aWVzCml0ID0gaXRlcihVc2QuUHJpbVJhbmdlLlN0YWdlKHN0YWdlLCBVc2QuUHJpbUlzTG9hZGVkICYgflVzZC5QcmltSXNBYnN0cmFjdCkpCnJlbW92ZSA9IFtdCnJlbmRlclBhdGggPSBTZGYuUGF0aCgnL1JlbmRlcicpCmZvciBwcmltIGluIFVzZC5QcmltUmFuZ2Uoc3RhZ2UuR2V0UHNldWRvUm9vdCgpKToKICAgIHByZWZpeGVzID0gcHJpbS5HZXRQYXRoKCkuR2V0UHJlZml4ZXMoKQoKICAgIGlmIHByZWZpeGVzOgogICAgICAgIGlmIHByZWZpeGVzWzBdID09ICcvUmVuZGVyJzoKICAgICAgICAgICAgY29udGludWUKCiAgICBpZiBub3QgcHJpbS5Jc0EoVXNkLlNjaGVtYUJhc2UpOgogICAgICAgIHJlbW92ZS5hcHBlbmQocHJpbSkKICAgICAgICAKZm9yIHByaW1fdG9fcmVtb3ZlIGluIHJlbW92ZToKICAgIHN0YWdlLlJlbW92ZVByaW0ocHJpbV90b19yZW1vdmUuR2V0UGF0aCgpKQo=",
                },
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
            ],
        }
    )

    # This preset deduplicates materials, move materials to /Looks, de-instance, merge spatially, delete hidden, prune leaves,
    # set pivots
    _preset.append(
        {
            "name": "merge_extreme_spatial",
            "displayName": "Modify Stage - Spatial Merge Meshes",
            "arguments": [
                {"operation": "utilityFunction", "paths": [], "function": 0},
                {"operation": "optimizeMaterials", "materialPrimPaths": [], "optimizeMaterialsMode": 0},
                {"operation": "moveMaterials", "materialsPath": "/World/Looks", "makeRootDefault": True},
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
                {
                    "operation": "merge",
                    "meshPrimPaths": [],
                    "considerMaterials": False,
                    "materialAlbedoAsVertexColors": False,
                    "originalGeomOption": 1,
                    "mergePoint": 7,
                    "rootPath": "Geometry/Merged/merged_mesh",
                    "considerAllAttributes": False,
                    "allowSingleMeshes": True,
                    "spatialMode": 1,
                    "spatialThreshold": 10.0,
                    "spatialMaxSize": 1000.0,
                    "spatialVertexCount": 10000,
                },
                {"operation": "deleteHiddenPrims"},
                {"operation": "removeUntypedPrims"},
                {"operation": "pruneLeaves", "paths": [], "pruneMode": 0},
            ],
        }
    )

    return _preset

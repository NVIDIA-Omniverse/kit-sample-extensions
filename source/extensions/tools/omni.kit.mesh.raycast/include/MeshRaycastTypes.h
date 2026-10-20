// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <carb/Types.h>

#include <usdrt/gf/vec.h>

namespace omni
{
namespace meshraycast
{
enum class RaycastEventType
{
    eBvhRebuilt,
};

enum class BvhRefreshRate
{
    eSlow, // sync to stage every 10 seconds
    eFast, // sync to stage every frame
};

struct HitResult
{
    int32_t meshIndex;
    carb::Float3 position;
    carb::Float3 normal;
    size_t faceIndex;
};

struct BoundResult
{
    int32_t meshIndex;
    float distance;
};

struct OverlapResult
{
    size_t* meshIndices;
    size_t size;
};

struct OverlapVerticesResult
{
    size_t meshSize; //!< number of meshIndices entries.
    int32_t* meshIndices; //!< pointer to an array of meshIndices.
    size_t* vertexIndicesSize; //!< pointer to an array of number of vertex indices for each mesh.
    size_t* vertexIndices; //!< pointer to an array of combined vertex indices for all meshes, each mesh offset by
                           //!< vertexIndicesSize.
    size_t* faceIndicesSize; //!< pointer to an array of number of face indices for each mesh.
    size_t* faceIndices; //!< pointer to an array of combined face indices for all meshes, each mesh offset by
                         //!< faceIndicesSize.
};

struct CurveTessellateResult
{
    size_t curveCount;
    size_t* positionCounts; //!< A UsdGeomBasisCurves may contain multiple curves. Each of them is tessellated
                            //!< separately and stored in flattened positions array.
    usdrt::GfVec3f* positions;
    size_t* tangentCounts; //!< A UsdGeomBasisCurves may contain multiple curves. Each of them is tessellated separately
                           //!< and stored in flattened tangents array.
    usdrt::GfVec3f* tangents;
};

// Contains configurations of how raycast should be performed.
struct RaycastContext;

} // namespace meshraycast
} // namespace omni

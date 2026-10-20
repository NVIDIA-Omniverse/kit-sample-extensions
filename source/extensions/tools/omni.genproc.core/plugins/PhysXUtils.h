// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <carb/logging/Log.h>

#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <physx/include/geometry/PxSphereGeometry.h>
#include <physx/include/geometry/PxTriangleMesh.h>
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

namespace omni
{
namespace genproc
{

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::ConstBundlePrims;

template <typename T>
class Releaser
{
public:
    void operator()(T* p)
    {
        p->release();
    }
};

template <typename T>
using UniquePhysXPtr = std::unique_ptr<T, Releaser<T>>;

physx::PxTriangleMesh* triPointsToPxTriangleMesh(const vec3f* points,
                                                 const size_t pointsCount,
                                                 const int* triIndices,
                                                 const size_t triIndicesCount);

void triPointsToPxTriangleMesh(const vec3f* points,
                               const size_t pointsCount,
                               const int* triIndices,
                               const size_t triIndicesCount,
                               UniquePhysXPtr<physx::PxTriangleMesh>& triangleMesh);

bool getMeshIntersection(const vec3f& origin,
                         const vec3f& direction,
                         const physx::PxTriangleMeshGeometry& triMeshGeometry,
                         const physx::PxReal maxDistance,
                         vec3f& hitPosition,
                         vec3f& hitNormal,
                         int* hitFace = nullptr,
                         float* hitDistance = nullptr);

bool getMeshClosestPoint(const vec3f& origin, const physx::PxTriangleMeshGeometry& triMeshGeometry, vec3f& closestPoint);

bool IsPointWithinMesh(const physx::PxVec3& testPos,
                       const physx::PxTriangleMeshGeometry& triMeshGeometry,
                       physx::PxU32& nearestTriIndex,
                       physx::PxVec3& nearestSurfacePosOut,
                       physx::PxVec3& normalOut);

size_t getMultihitMeshIntersection(const vec3f& origin,
                                   const vec3f& direction,
                                   const physx::PxTriangleMeshGeometry& triMeshGeometry,
                                   const physx::PxReal maxDistance,
                                   std::vector<vec3f>& hitPositions,
                                   std::vector<vec3f>& hitNormals,
                                   std::vector<int>* hitFaces = nullptr,
                                   std::vector<float>* hitDistances = nullptr,
                                   const physx::PxU32 maxRaycastHits = 32);

bool bboxIsEmpty(const std::pair<vec3f, vec3f>& bbox);

void getPrimBBoxes(ConstBundlePrims& bundlePrims,
                   const bool usePrimExtent,
                   std::vector<matrix4d>& transformOut,
                   std::vector<std::pair<vec3f, vec3f>>& bboxOut);

void getSphereGeometry(ConstBundlePrims& bundlePrims,
                       const bool usePrimExtent,
                       std::vector<physx::PxSphereGeometry>& geometryOut,
                       std::vector<physx::PxTransform>& poseOut);

bool getMeshIntersectionViaSweep(const vec3f& direction,
                                 const physx::PxGeometry& geom0,
                                 const physx::PxTransform& pose0,
                                 const physx::PxGeometry& geom1,
                                 const physx::PxTransform& pose1,
                                 const physx::PxReal maxDistance,
                                 vec3f& hitPosition,
                                 vec3f& hitNormal,
                                 int* hitFace = nullptr,
                                 float* hitDistance = nullptr);

bool pointInsideMesh(const vec3f& point, const physx::PxTriangleMeshGeometry& triMeshGeometry);

}
}

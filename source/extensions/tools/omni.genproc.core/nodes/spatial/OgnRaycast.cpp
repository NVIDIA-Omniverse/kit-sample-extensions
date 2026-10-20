// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include "../plugins/PhysXUtils.h"
#include "../plugins/Utils.h"

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <physx/include/foundation/PxTransform.h>
#include <physx/include/geometry/PxSphereGeometry.h>
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

#include <OgnRaycastDatabase.h>
#include <algorithm>
#include <cmath>
#include <limits>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::genproc;

class OgnRaycast
{
public:
    enum SourceType : size_t
    {
        BUNDLE_PRIM = 0,
        POINT_AND_DIRECTION,
        NUM_SOURCE_TYPES
    };

    enum QueryType : size_t
    {
        RAYCAST = 0,
        SWEEP,
        NUM_QUERY_TYPES
    };

    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
    }

    static void raycast(const vec3f& sourcePoint,
                        const vec3f& sourceDirection,
                        const physx::PxTriangleMeshGeometry& triMeshGeometry,
                        const physx::PxReal maxDistance,
                        const bool closestHitOnly,
                        std::vector<vec3f>& hitPoints,
                        std::vector<vec3f>& hitNormals,
                        std::vector<int>& hitFaces,
                        std::vector<float>& hitDistances)
    {
        if (closestHitOnly)
        {
            vec3f hitPoint, hitNormal;
            int hitFace = 0;
            float hitDistance = 0.f;
            const bool hasHit = getMeshIntersection(sourcePoint, sourceDirection, triMeshGeometry, maxDistance,
                                                    hitPoint, hitNormal, &hitFace, &hitDistance);

            if (hasHit)
            {
                hitPoints.push_back(hitPoint);
                hitNormals.push_back(hitNormal);
                hitFaces.push_back(hitFace);
                hitDistances.push_back(hitDistance);
            }
        }
        else
        {
            std::vector<vec3f> primHitPoints, primHitNormals;
            std::vector<int> primHitFaces;
            std::vector<float> primHitDistances;
            const size_t hitCount =
                getMultihitMeshIntersection(sourcePoint, sourceDirection, triMeshGeometry, maxDistance, primHitPoints,
                                            primHitNormals, &primHitFaces, &primHitDistances);
            if (hitCount > 0)
            {
                const size_t offset = hitPoints.size();
                hitPoints.resize(offset + hitCount);
                hitNormals.resize(offset + hitCount);
                hitFaces.resize(offset + hitCount);
                hitDistances.resize(offset + hitCount);
                for (size_t i = 0; i < hitCount; i++)
                {
                    hitPoints[offset + i] = primHitPoints[i];
                    hitNormals[offset + i] = primHitNormals[i];
                    hitFaces[offset + i] = primHitFaces[i];
                    hitDistances[offset + i] = primHitDistances[i];
                }
            }
        }
    }

    static void sweep(const physx::PxGeometry& sourceGeometry,
                      const physx::PxTransform& sourcePose,
                      const vec3f& sourceDirection,
                      const physx::PxTriangleMeshGeometry& triMeshGeometry,
                      const physx::PxReal maxDistance,
                      std::vector<vec3f>& hitPoints,
                      std::vector<vec3f>& hitNormals,
                      std::vector<int>& hitFaces,
                      std::vector<float>& hitDistances)
    {
        vec3f hitPoint, hitNormal;
        int hitFace = 0;
        float hitDistance = 0.f;
        const physx::PxTransform colliderPose = physx::PxTransform(physx::PxIdentity);
        const bool hasHit = getMeshIntersectionViaSweep(sourceDirection, sourceGeometry, sourcePose, // sweep stuff
                                                        triMeshGeometry, colliderPose, maxDistance, // collision stuff
                                                        hitPoint, hitNormal, &hitFace, &hitDistance); // output stuff
        if (hasHit)
        {
            hitPoints.push_back(hitPoint);
            hitNormals.push_back(hitNormal);
            hitFaces.push_back(hitFace);
            hitDistances.push_back(hitDistance);
        }
    }

    static bool compute(OgnRaycastDatabase& db)
    {
        auto& context = db.abi_context();

        ConstBundlePrims inputPrims(db.abi_context(), db.inputs.primBundle().abi_bundleHandle());
        const size_t inputPrimCount = inputPrims.getPrimCount();
        ConstBundlePrim& inputCommonAttrs = inputPrims.getConstCommonAttrs();
        // BundleAttrib const* minCornerAttr = inputCommonAttrs.getAttr(db.tokens.bboxMinCorner);
        // BundleAttrib const* maxCornerAttr = inputCommonAttrs.getAttr(db.tokens.bboxMaxCorner);
        // BundleAttrib const* bboxTransformAttr = inputCommonAttrs.getAttr(db.tokens.bboxTransform);

        // NOTE: bbox attributes currently unused...
        // const vec3d* minCornerData = nullptr;
        // const vec3d* maxCornerData = nullptr;
        // const matrix4d* bboxTransformData = nullptr;

        // if (minCornerAttr != nullptr && minCornerAttr->size() == inputPrimCount)
        //{
        //    minCornerData = minCornerAttr->getData<vec3d>();
        //}
        // if (maxCornerAttr != nullptr && maxCornerAttr->size() == inputPrimCount)
        //{
        //    maxCornerData = maxCornerAttr->getData<vec3d>();
        //}
        // if (bboxTransformAttr != nullptr && bboxTransformAttr->size() == inputPrimCount)
        //{
        //    bboxTransformData = bboxTransformAttr->getData<matrix4d>();
        //}

        ConstBundlePrims obstaclePrims(db.abi_context(), db.inputs.obstacleBundle().abi_bundleHandle());
        const size_t obstaclePrimCount = obstaclePrims.getPrimCount();

        const bool optionsChanged =
            (db.state.prevPoint() != db.inputs.point()) || (db.state.prevDirection() != db.inputs.direction()) ||
            (db.state.prevSourceType() != db.inputs.sourceType()) ||
            (db.state.prevQueryType() != db.inputs.queryType()) || (db.state.prevRange() != db.inputs.range()) ||
            (db.state.prevClosestHitOnly() != db.inputs.closestHitOnly()) ||
            (db.state.prevRadius() != db.inputs.radius()) || (db.state.prevVerbose() != db.inputs.verbose());

        if (!optionsChanged && !db.inputs.primBundle.changes().hasChanged() &&
            !db.inputs.obstacleBundle.changes().hasChanged())
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        UniquePhysXPtr<physx::PxTriangleMesh> triMesh;
        std::vector<int> triFaceToPrimFace;
        std::vector<size_t> triFaceToPrimIndex;

        // TODO: cache triMesh
        {
            std::vector<vec3f> points;
            std::vector<int> indices;

            primsInBundleToTriangles(obstaclePrims, points, indices,
                                     nullptr, // normals
                                     &triFaceToPrimFace, &triFaceToPrimIndex);

            triPointsToPxTriangleMesh(points.data(), points.size(), indices.data(), indices.size(), triMesh);

            if (points.size() == 0 || indices.size() == 0)
            {
                CARB_LOG_ERROR_ONCE(
                    "OgnRaycast: must provide an obstacles bundle with at least one mesh prim to use in intersection tests.");
                return false;
            }
        }

        SourceType sourceType = SourceType(db.inputs.sourceType());
        if (sourceType < SourceType(0))
            sourceType = SourceType(0);
        if (sourceType >= NUM_SOURCE_TYPES)
            sourceType = SourceType(size_t(NUM_SOURCE_TYPES) - 1);

        QueryType queryType = QueryType(db.inputs.queryType());
        if (queryType < QueryType(0))
            queryType = QueryType(0);
        if (queryType >= NUM_QUERY_TYPES)
            queryType = QueryType(size_t(NUM_QUERY_TYPES) - 1);

        if (sourceType == BUNDLE_PRIM && inputPrimCount == 0)
        {
            CARB_LOG_ERROR_ONCE(
                "OgnRaycast: must provide an input bundle with at least one prim to use in intersection tests.");
            return false;
        }

        physx::PxTriangleMeshGeometry triMeshGeometry(triMesh.get());

        physx::PxReal maxDistance =
            db.inputs.range() > 0.f ? (physx::PxReal)db.inputs.range() : std::numeric_limits<physx::PxReal>::max();


        std::vector<vec3f> hitPoints, hitNormals;
        std::vector<int> hitFaces;
        std::vector<float> hitDistances;
        std::vector<NameToken> hitPaths;

        vec3f sourcePoint, sourceDirection;
        physx::PxSphereGeometry sourceBoundingSphere;
        physx::PxTransform sourcePose;
        if (sourceType == BUNDLE_PRIM)
        {
            std::vector<matrix4d> sourceTransforms;
            getPrimTransforms(inputPrims, sourceTransforms);

            if (queryType == RAYCAST)
            {
                for (size_t primIndex = 0; primIndex < inputPrimCount; primIndex++)
                {
                    const matrix4d& transform = sourceTransforms[primIndex];

                    sourcePoint = vec3f(transform.ExtractTranslation());
                    sourceDirection = transform.TransformDir(db.inputs.direction()).GetNormalized();

                    raycast(sourcePoint, sourceDirection, triMeshGeometry, maxDistance, db.inputs.closestHitOnly(),
                            hitPoints, hitNormals, hitFaces, hitDistances);
                }
            }
            else // SWEEP
            {
                std::vector<physx::PxSphereGeometry> geometry;
                std::vector<physx::PxTransform> pose;
                const bool usePrimExtent = false;
                getSphereGeometry(inputPrims, usePrimExtent, geometry, pose);

                for (size_t primIndex = 0; primIndex < inputPrimCount; primIndex++)
                {
                    const matrix4d& transform = sourceTransforms[primIndex];
                    sourceDirection = transform.TransformDir(db.inputs.direction()).GetNormalized();
                    sweep(geometry[primIndex], pose[primIndex], sourceDirection, triMeshGeometry, maxDistance,
                          hitPoints, hitNormals, hitFaces, hitDistances);
                }
            }
        }
        else // sourceType == POINT_AND_DIRECTION
        {
            sourcePoint = db.inputs.point();
            sourceDirection = db.inputs.direction().GetNormalized();

            if (queryType == RAYCAST)
            {
                raycast(sourcePoint, sourceDirection, triMeshGeometry, maxDistance, db.inputs.closestHitOnly(),
                        hitPoints, hitNormals, hitFaces, hitDistances);
            }
            else // SWEEP
            {
                sourceBoundingSphere = physx::PxSphereGeometry(db.inputs.radius());
                sourcePose = physx::PxTransform(sourcePoint[0], sourcePoint[1], sourcePoint[2]);

                sweep(sourceBoundingSphere, sourcePose, sourceDirection, triMeshGeometry, maxDistance, hitPoints,
                      hitNormals, hitFaces, hitDistances);
            }
        }

        // remap hit faces pt 1, since triangles are reordered by physx
        const physx::PxU32* mapping = triMesh.get()->getTrianglesRemap();
        for (size_t i = 0; i < hitFaces.size(); i++)
        {
            hitFaces[i] = (int)mapping[hitFaces[i]];
        }

        hitPaths.resize(hitFaces.size());
        for (size_t i = 0; i < hitFaces.size(); i++)
        {
            CARB_ASSERT(hitFaces[i] < triFaceToPrimIndex.size());
            const size_t primIndex = triFaceToPrimIndex[hitFaces[i]];
            CARB_ASSERT(primIndex < obstaclePrimCount);
            hitPaths[i] = obstaclePrims.getPrim(primIndex)->path();
        }

        // remap hit faces pt 2, since prim faces may not all be triangles
        for (size_t i = 0; i < hitFaces.size(); i++)
        {
            CARB_ASSERT(hitFaces[i] < triFaceToPrimFace.size());
            hitFaces[i] = triFaceToPrimFace[hitFaces[i]];
        }

        if (db.inputs.verbose())
        {
            CARB_LOG_INFO("OgnRaycast -- hit!");
            for (size_t i = 0; i < hitPoints.size(); i++)
            {
                CARB_LOG_INFO("Hit point %zu: %f, %f, %f", i, hitPoints[i][0], hitPoints[i][1], hitPoints[i][2]);
                if (sourceType == BUNDLE_PRIM)
                {
                    CARB_LOG_INFO("Hit prim: %s", db.tokenToString(hitPaths[i]));
                }
                CARB_LOG_INFO("Hit face: %d", hitFaces[i]);
            }
        }

        // write to output
        auto& pointsOut = db.outputs.points();
        auto& normalsOut = db.outputs.normals();
        auto& faceIndicesOut = db.outputs.faceIndices();
        auto& distancesOut = db.outputs.distances();
        auto& pathsOut = db.outputs.paths();
        if (hitPoints.size() > 0)
        {
            pointsOut.resize(hitPoints.size());
            normalsOut.resize(hitNormals.size());
            faceIndicesOut.resize(hitFaces.size());
            distancesOut.resize(hitDistances.size());
            pathsOut.resize(hitPaths.size());

            memcpy(pointsOut.data(), hitPoints.data(), hitPoints.size() * sizeof(vec3f));
            memcpy(normalsOut.data(), hitNormals.data(), hitNormals.size() * sizeof(vec3f));
            memcpy(faceIndicesOut.data(), hitFaces.data(), hitFaces.size() * sizeof(int));
            memcpy(distancesOut.data(), hitDistances.data(), hitDistances.size() * sizeof(float));
            memcpy(pathsOut.data(), hitPaths.data(), hitPaths.size() * sizeof(NameToken));
        }
        else
        {
            pointsOut.resize(0);
            normalsOut.resize(0);
            faceIndicesOut.resize(0);
            distancesOut.resize(0);
            pathsOut.resize(0);
        }

        db.state.prevPoint() = db.inputs.point();
        db.state.prevDirection() = db.inputs.direction();
        db.state.prevSourceType() = db.inputs.sourceType();
        db.state.prevQueryType() = db.inputs.queryType();
        db.state.prevRange() = db.inputs.range();
        db.state.prevClosestHitOnly() = db.inputs.closestHitOnly();
        db.state.prevRadius() = db.inputs.radius();
        db.state.prevVerbose() = db.inputs.verbose();

        return true;
    }
};

REGISTER_OGN_NODE()

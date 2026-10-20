// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "PhysXUtils.h"

#include "Utils.h"

#include <physx/include/cooking/PxCooking.h>
#include <physx/include/foundation/PxAllocatorCallback.h>
#include <physx/include/foundation/PxErrorCallback.h>
#include <physx/include/foundation/PxFoundation.h>
#include <physx/include/foundation/PxMat44.h>
#include <physx/include/foundation/PxPhysicsVersion.h>
#include <physx/include/foundation/PxTransform.h>
#include <physx/include/geometry/PxGeometryQuery.h>
#include <physx/include/geometry/PxMeshQuery.h>
#include <physx/include/geometry/PxTriangle.h>

#include <limits>

namespace omni
{
namespace genproc
{

using omni::math::linalg::matrix4f;
using omni::math::linalg::quatd;
using omni::math::linalg::quatf;
using omni::math::linalg::vec3d;

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;

class Allocator : public physx::PxAllocatorCallback
{
public:
    ~Allocator() override
    {
    }
    void* allocate(size_t size, const char* typeName, const char* filename, int line) override
    {
        return malloc(size);
    }
    void deallocate(void* ptr) override
    {
        free(ptr);
    }
};
// This has no data to construct, (apart from the virtual table pointer),
// or destruct, so can be static.
static Allocator s_allocator;

class ErrorCallback : public physx::PxErrorCallback
{
public:
    ~ErrorCallback() override
    {
    }
    void reportError(physx::PxErrorCode::Enum code, const char* message, const char* file, int line) override
    {
        const char* typeString = "error";
        const char* const pattern = "PhysX %s in OgnBuildAccelTree: \"%s\"; file \"%s\" line %d\n";
        switch (code)
        {
        case physx::PxErrorCode::Enum::eNO_ERROR:
            return;
        case physx::PxErrorCode::Enum::eDEBUG_INFO:
            CARB_LOG_INFO(pattern, "debug info", message, file, line);
            return;
        case physx::PxErrorCode::Enum::eDEBUG_WARNING:
            CARB_LOG_WARN(pattern, "warning", message, file, line);
            return;
        case physx::PxErrorCode::Enum::eINVALID_PARAMETER:
            typeString = "invalid parameter";
            break;
        case physx::PxErrorCode::Enum::eINVALID_OPERATION:
            typeString = "invalid operation";
            break;
        case physx::PxErrorCode::Enum::eOUT_OF_MEMORY:
            typeString = "out of memory";
            break;
        case physx::PxErrorCode::Enum::eINTERNAL_ERROR:
            typeString = "internal error";
            break;
        case physx::PxErrorCode::Enum::eABORT:
            typeString = "abort";
            break;
        case physx::PxErrorCode::Enum::ePERF_WARNING:
            CARB_LOG_WARN(pattern, "perf warning", message, file, line);
            return;
        default:
            break;
        }
        CARB_LOG_ERROR(pattern, typeString, message, file, line);
    }
};
// This has no data to construct, (apart from the virtual table pointer),
// or destruct, so can be static.
static ErrorCallback s_errorCallback;

physx::PxFoundation* getPhysxFoundation()
{
    // Note that according to the Physx docs, only one foundation should exist per process.
    // So we'll check whether a PxFoundation exists, and only create one if one does not
    // already exist.
    // Two caveats: 1. these Check/Create steps are not an atomic operation, leaving potential
    // for error in a multithreaded setting.
    // 2. the PxFoundation object also has a `release' function in its interface. Should we call it,
    // and if so when? On extension disable?

    physx::PxFoundation* foundation = PxIsFoundationValid();
    if (foundation == nullptr)
    {
        foundation = PxCreateFoundation(PX_PHYSICS_VERSION, s_allocator, s_errorCallback);
    }
    return foundation;
}

physx::PxTriangleMesh* triPointsToPxTriangleMesh(const vec3f* points,
                                                 const size_t pointsCount,
                                                 const int* triIndices,
                                                 const size_t triIndicesCount)
{
    // although foundation is unused here apart from checking for non-null,
    // we need to ensure it has been created before invoking PxCreateTriangleMesh
    physx::PxFoundation* foundation = getPhysxFoundation();
    if (foundation == nullptr)
    {
        return nullptr;
    }

    const size_t triCount = triIndicesCount / 3;

    if (pointsCount == 0 || triCount == 0)
    {
        // No triangles. This is not necessarily an error.
        return nullptr;
    }

    const physx::PxTolerancesScale scale;
    physx::PxCookingParams params(scale);
    params.midphaseDesc.setToDefault(physx::PxMeshMidPhase::eBVH34);
    // NOTE: the physx bvh has an upper bound on its number of nodes; exceeding this number leads to incorrect
    // results, e.g. not detecting a ray intersection when one should. To push this problem further down
    // the road, we'll increase the number of triangles per leaf node to the maximum allowed value (15)
    params.midphaseDesc.mBVH34Desc.numPrimsPerLeaf = 15;
    // params.midphaseDesc.mBVH34Desc.quantized = false;
    params.meshPreprocessParams |= physx::PxMeshPreprocessingFlag::eDISABLE_ACTIVE_EDGES_PRECOMPUTE;
    params.meshPreprocessParams |= physx::PxMeshPreprocessingFlag::eDISABLE_CLEAN_MESH;

    physx::PxTriangleMeshDesc meshDesc;
    meshDesc.points.count = physx::PxU32(pointsCount);
    meshDesc.points.stride = sizeof(float) * 3;
    meshDesc.points.data = points;
    meshDesc.triangles.count = physx::PxU32(triCount);
    meshDesc.triangles.stride = sizeof(int) * 3;
    meshDesc.triangles.data = triIndices;
    return PxCreateTriangleMesh(params, meshDesc);
}

void triPointsToPxTriangleMesh(const vec3f* points,
                               const size_t pointsCount,
                               const int* triIndices,
                               const size_t triIndicesCount,
                               UniquePhysXPtr<physx::PxTriangleMesh>& triangleMesh)
{
    triangleMesh.reset(triPointsToPxTriangleMesh(points, pointsCount, triIndices, triIndicesCount));
}

bool getMeshIntersection(const vec3f& origin,
                         const vec3f& direction,
                         const physx::PxTriangleMeshGeometry& triMeshGeometry,
                         const physx::PxReal maxDistance,
                         vec3f& hitPosition,
                         vec3f& hitNormal,
                         int* hitFace /* = nullptr */,
                         float* hitDistance /* = nullptr */)
{
    const physx::PxTransform pose = physx::PxTransform(physx::PxIdentity);
    const physx::PxVec3 pxOrigin = physx::PxVec3(origin[0], origin[1], origin[2]);
    const physx::PxVec3 pxDirection = physx::PxVec3(direction[0], direction[1], direction[2]).getNormalized();

    physx::PxHitFlags hitFlags =
        physx::PxHitFlag::ePOSITION | physx::PxHitFlag::eMESH_BOTH_SIDES | physx::PxHitFlag::eNORMAL;
    if (hitFace != nullptr)
        hitFlags |= physx::PxHitFlag::eFACE_INDEX;
    const physx::PxU32 maxRaycastHits = 1;
    physx::PxGeomRaycastHit rayHit;
    physx::PxU32 hitCount =
        physx::PxGeometryQuery::raycast(pxOrigin, pxDirection, triMeshGeometry, pose, maxDistance, hitFlags,
                                        maxRaycastHits, &rayHit, physx::PxU32(sizeof(physx::PxGeomRaycastHit)));

    if (hitCount != 0)
    {
        hitPosition = vec3f(rayHit.position[0], rayHit.position[1], rayHit.position[2]);
        hitNormal = vec3f(rayHit.normal[0], rayHit.normal[1], rayHit.normal[2]);
        if (hitFace != nullptr)
            (*hitFace) = (int)rayHit.faceIndex;
        if (hitDistance != nullptr)
            (*hitDistance) = (float)rayHit.distance;
    }

    return hitCount != 0;
}

bool getMeshClosestPoint(const vec3f& origin, const physx::PxTriangleMeshGeometry& triMeshGeometry, vec3f& closestPoint)
{
    const physx::PxTransform pose = physx::PxTransform(physx::PxIdentity);
    const physx::PxVec3 pxOrigin(origin[0], origin[1], origin[2]);
    physx::PxVec3 pxClosest;

    physx::PxReal pxDistance = physx::PxGeometryQuery::pointDistance(pxOrigin, triMeshGeometry, pose, &pxClosest);

    closestPoint = vec3f(pxClosest[0], pxClosest[1], pxClosest[2]);

    // positive distance: distance squared to object
    // 0: point is inside object
    // -1: object is of unsupported type
    return pxDistance >= physx::PxReal(0);
}

bool IsPointWithinMesh(const physx::PxVec3& testPos,
                       const physx::PxTriangleMeshGeometry& triMeshGeometry,
                       physx::PxU32& nearestTriIndex,
                       physx::PxVec3& nearestSurfacePosOut,
                       physx::PxVec3& normalOut)
{
    const physx::PxTransform identityPose = physx::PxTransform(physx::PxIdentity);

    // if we have to raycast, how far do we need to look? never greater than the diagonal of the mesh
    //  bounds.
    physx::PxBounds3 meshBounds;
    physx::PxGeometryQuery::computeGeomBounds(meshBounds, triMeshGeometry, identityPose);
    const physx::PxReal raycastDistance = meshBounds.getDimensions().magnitude();

    physx::PxReal distance = physx::PxGeometryQuery::pointDistance(
        testPos, triMeshGeometry, identityPose, &nearestSurfacePosOut, &nearestTriIndex);

    // distance of -1 means geometry type not supported, which can never happen.
    CARB_ASSERT(distance >= 0.0f);

    bool isInside = false; // ...until we prove otherwise

    // direct hit on surface may be highly unlikely, but still possible. we'll consider this "inside"
    if (distance == 0)
    {
        isInside = true;
    }
    else
    {
        // there's lots of situations where a simple normal or raycast hit count can fail. run three tests 3x and count
        // the votes
        //  we'll try to punch our way out towards the three closest planes
        const float x = testPos.x < 0 ? -1.0f : 1.0f, y = testPos.y < 0 ? -1.0f : 1.0f, z = testPos.z < 0 ? -1.0f : 1.0f;
        const physx::PxVec3 raycastDirections[] = { { x, 0, 0 }, { 0, y, 0 }, { 0, 0, z } };

        int numInsideVotes = 0;
        for (physx::PxVec3 raycastDirection : raycastDirections)
        {
            // if the raycast fills this, the result probably can't be trusted. 16 seems enormous
            const size_t MAX_RAYCAST_HITS = 16;
            physx::PxGeomRaycastHit rayHits[MAX_RAYCAST_HITS];

            const physx::PxHitFlags hitFlags =
                physx::PxHitFlag::ePOSITION | physx::PxHitFlag::eMESH_BOTH_SIDES | physx::PxHitFlag::eMESH_MULTIPLE;
            physx::PxU32 hitCount = physx::PxGeometryQuery::raycast(
                testPos, raycastDirection, triMeshGeometry, identityPose, raycastDistance, hitFlags, MAX_RAYCAST_HITS,
                rayHits, physx::PxU32(sizeof(physx::PxGeomRaycastHit)));
            bool oddHitCount = hitCount % 2;
            bool isInsideSurface = (oddHitCount == true);

            numInsideVotes += int(isInsideSurface);
        }

        isInside = (numInsideVotes > 1);
    }

    if (isInside)
    {
        physx::PxTriangle triangle;
        physx::PxMeshQuery::getTriangle(triMeshGeometry, identityPose, nearestTriIndex, triangle);
        triangle.normal(normalOut);
    }

    return isInside;
}

size_t getMultihitMeshIntersection(const vec3f& origin,
                                   const vec3f& direction,
                                   const physx::PxTriangleMeshGeometry& triMeshGeometry,
                                   const physx::PxReal maxDistance,
                                   std::vector<vec3f>& hitPositions,
                                   std::vector<vec3f>& hitNormals,
                                   std::vector<int>* hitFaces /* = nullptr */,
                                   std::vector<float>* hitDistances /* = nullptr */,
                                   const physx::PxU32 maxRaycastHits /* = 16*/)
{
    const physx::PxTransform pose = physx::PxTransform(physx::PxIdentity);
    const physx::PxVec3 pxOrigin = physx::PxVec3(origin[0], origin[1], origin[2]);
    const physx::PxVec3 pxDirection = physx::PxVec3(direction[0], direction[1], direction[2]).getNormalized();

    physx::PxHitFlags hitFlags = physx::PxHitFlag::ePOSITION | physx::PxHitFlag::eMESH_BOTH_SIDES |
                                 physx::PxHitFlag::eNORMAL | physx::PxHitFlag::eMESH_MULTIPLE;
    if (hitFaces != nullptr)
        hitFlags |= physx::PxHitFlag::eFACE_INDEX;

    std::vector<physx::PxGeomRaycastHit> rayHits(maxRaycastHits);

    physx::PxU32 hitCount =
        physx::PxGeometryQuery::raycast(pxOrigin, pxDirection, triMeshGeometry, pose, maxDistance, hitFlags,
                                        maxRaycastHits, rayHits.data(), physx::PxU32(sizeof(physx::PxGeomRaycastHit)));

    if (hitCount > 0)
    {
        hitPositions.resize(hitCount);
        hitNormals.resize(hitCount);
        if (hitFaces != nullptr)
            hitFaces->resize(hitCount);
        if (hitDistances != nullptr)
            hitDistances->resize(hitCount);
        for (size_t i = 0; i < (size_t)hitCount; i++)
        {
            hitPositions[i] = vec3f(rayHits[i].position[0], rayHits[i].position[1], rayHits[i].position[2]);
            hitNormals[i] = vec3f(rayHits[i].normal[0], rayHits[i].normal[1], rayHits[i].normal[2]);
            if (hitFaces != nullptr)
                (*hitFaces)[i] = (int)rayHits[i].faceIndex;
            if (hitDistances != nullptr)
                (*hitDistances)[i] = (float)rayHits[i].distance;
        }
    }

    return (size_t)hitCount;
}

bool bboxIsEmpty(const std::pair<vec3f, vec3f>& bbox)
{
    return bbox.first[0] > bbox.second[0] || bbox.first[1] > bbox.second[1] || bbox.first[2] > bbox.second[2];
}

void getPrimBBoxes(ConstBundlePrims& bundlePrims,
                   const bool usePrimExtent,
                   std::vector<matrix4d>& transformOut,
                   std::vector<std::pair<vec3f, vec3f>>& bboxOut)
{
    const size_t numPrims = bundlePrims.getPrimCount();
    transformOut.resize(numPrims);
    bboxOut.resize(numPrims);

    std::vector<matrix4d> primTransforms;
    getPrimTransforms(bundlePrims, primTransforms);

    if (usePrimExtent)
    {
        ConstBundlePrim& commonAttrs = bundlePrims.getConstCommonAttrs();
        BundleAttrib const* minCornerAttr = commonAttrs.getConstAttr(NameToken("bboxMinCorner"));
        BundleAttrib const* maxCornerAttr = commonAttrs.getConstAttr(NameToken("bboxMaxCorner"));
        BundleAttrib const* bboxTransformAttr = commonAttrs.getConstAttr(NameToken("bboxTransform"));
        const vec3d* minCornerData = nullptr;
        const vec3d* maxCornerData = nullptr;
        const matrix4d* bboxTransformData = nullptr;

        if (minCornerAttr != nullptr && minCornerAttr->size() == numPrims)
        {
            minCornerData = minCornerAttr->getData<vec3d>();
        }
        if (maxCornerAttr != nullptr && maxCornerAttr->size() == numPrims)
        {
            maxCornerData = maxCornerAttr->getData<vec3d>();
        }
        if (bboxTransformAttr != nullptr && bboxTransformAttr->size() == numPrims)
        {
            bboxTransformData = bboxTransformAttr->getData<matrix4d>();
        }

        matrix4d bboxTransform;
        vec3f minPoint, maxPoint;
        for (size_t primIndex = 0; primIndex < numPrims; primIndex++)
        {
            const matrix4d& transform = primTransforms[primIndex];

            if (bboxTransformData)
                bboxTransform = bboxTransformData[primIndex];
            else
                bboxTransform.SetIdentity();

            //// object-space bounding box
            // default bbox is "infinitely inside-out"
            minPoint = vec3f(std::numeric_limits<float>::max());
            maxPoint = vec3f(std::numeric_limits<float>::lowest());
            if (minCornerData != nullptr && maxCornerData != nullptr)
            {
                minPoint = vec3f(minCornerData[primIndex]);
                maxPoint = vec3f(maxCornerData[primIndex]);
            }

            transformOut[primIndex] = transform * bboxTransform; // TODO: verify order..
            bboxOut[primIndex] = std::pair<vec3f, vec3f>(minPoint, maxPoint);

            // XXX currently, a prim's local transform is considered both in its overall transform and in its
            // bboxTransform, leading it to be double counted here...

            vec3f translation = vec3f(transform.ExtractTranslation());
            // std::cout<<"world translation: "<<translation[0]<<", "<<translation[1]<<", "<<translation[2]<<std::endl;
            translation = vec3f(bboxTransform.ExtractTranslation());
            // std::cout<<"bbox translation: "<<translation[0]<<", "<<translation[1]<<", "<<translation[2]<<std::endl;
        }
    }
    else
    {
        vec3f minCorner, maxCorner;
        for (size_t primIndex = 0; primIndex < numPrims; primIndex++)
        {
            const matrix4d& transform = primTransforms[primIndex];

            //// object-space bounding box
            // default bbox is "infinitely inside-out"
            minCorner = vec3f(std::numeric_limits<float>::max());
            maxCorner = vec3f(std::numeric_limits<float>::lowest());

            ConstBundlePrim* prim = bundlePrims.getConstPrim(primIndex);
            BundleAttrib const* pointsAttr = prim->getConstAttr(NameToken("points"));
            const size_t numPoints = pointsAttr != nullptr ? pointsAttr->size() : 0;
            const vec3f* points = numPoints > 0 ? pointsAttr->getData<vec3f>() : nullptr;

            if (points)
            {
                for (size_t i = 0; i < numPoints; i++)
                {
                    const vec3f worldPoint = transform.Transform(points[i]);
                    for (size_t d = 0; d < vec3f::dimension; d++)
                    {
                        minCorner[d] = std::min(minCorner[d], worldPoint[d]);
                        maxCorner[d] = std::max(maxCorner[d], worldPoint[d]);
                    }
                }
            }
            else
            {
                CARB_LOG_ERROR_ONCE("getPrimBBoxes: No points attribute found in input prim");
            }

            transformOut[primIndex].SetIdentity();
            bboxOut[primIndex] = std::pair<vec3f, vec3f>(minCorner, maxCorner);
        }
    }
}

void getSphereGeometry(ConstBundlePrims& bundlePrims,
                       const bool usePrimExtent,
                       std::vector<physx::PxSphereGeometry>& geometryOut,
                       std::vector<physx::PxTransform>& poseOut)
{
    const size_t numPrims = bundlePrims.getPrimCount();
    geometryOut.resize(numPrims);
    poseOut.resize(numPrims);

    std::vector<matrix4d> bboxTransform;
    std::vector<std::pair<vec3f, vec3f>> bbox;

    getPrimBBoxes(bundlePrims, usePrimExtent, bboxTransform, bbox);

    for (size_t i = 0; i < numPrims; i++)
    {
        if (bboxIsEmpty(bbox[i]))
        {
            geometryOut[i] = physx::PxSphereGeometry(0.f);
            poseOut[i] = physx::PxTransform(physx::PxIdentity);
        }
        else
        {
            // NOTE: PhysX sphere must be centered, so we need to do one more transformation here.
            float maxLength = 0.f;
            vec3f offset(0);
            for (size_t d = 0; d < vec3f::dimension; d++)
            {
                maxLength = std::max(maxLength, bbox[i].second[d] - bbox[i].first[d]);
                offset[d] = 0.5f * (bbox[i].second[d] + bbox[i].first[d]);
            }
            matrix4d offsetMatrix;
            offsetMatrix.SetTranslate(vec3d(offset));

            matrix4d transform = bboxTransform[i] * offsetMatrix; // TODO: verify order

            geometryOut[i] = physx::PxSphereGeometry(0.5f * maxLength);

            // NOTE: PxTransform is a rigid frame -- just translation and rotation.
            // Scaling must be baked into the geometry.
            quatf rotation = quatf(transform.ExtractRotation());
            vec3f translation = vec3f(transform.ExtractTranslation());
            poseOut[i] = physx::PxTransform(translation[0], translation[1], translation[2],
                                            physx::PxQuat(rotation.GetImaginary()[0], rotation.GetImaginary()[1],
                                                          rotation.GetImaginary()[2], rotation.GetReal()));
        }
    }
}

bool getMeshIntersectionViaSweep(const vec3f& direction,
                                 const physx::PxGeometry& geom0,
                                 const physx::PxTransform& pose0,
                                 const physx::PxGeometry& geom1,
                                 const physx::PxTransform& pose1,
                                 const physx::PxReal maxDistance,
                                 vec3f& hitPosition,
                                 vec3f& hitNormal,
                                 int* hitFace /* = nullptr*/,
                                 float* hitDistance /* = nullptr */)
{
    const physx::PxVec3 pxDirection = physx::PxVec3(direction[0], direction[1], direction[2]);
    physx::PxGeomSweepHit sweepHit;
    physx::PxHitFlags hitFlags = physx::PxHitFlag::eDEFAULT | physx::PxHitFlag::ePRECISE_SWEEP;
    if (hitFace != nullptr)
        hitFlags |= physx::PxHitFlag::eFACE_INDEX;
    const float inflation = 0.f;
    physx::PxGeometryQueryFlags queryFlags = physx::PxGeometryQueryFlag::eDEFAULT;
    // bool validGeom0 = physx::PxGeometryQuery::isValid(geom0);
    // bool validGeom1 = physx::PxGeometryQuery::isValid(geom1);
    // std::cout<<"valid 0: "<<validGeom0<<std::endl;
    // std::cout<<"valid 1: "<<validGeom1<<std::endl;
    bool hasHit = physx::PxGeometryQuery::sweep(
        pxDirection, maxDistance, geom0, pose0, geom1, pose1, sweepHit, hitFlags, inflation, queryFlags);

    if (hasHit)
    {
        hitPosition = vec3f(sweepHit.position[0], sweepHit.position[1], sweepHit.position[2]);
        hitNormal = vec3f(sweepHit.normal[0], sweepHit.normal[1], sweepHit.normal[2]);
        if (hitFace != nullptr)
            (*hitFace) = (int)sweepHit.faceIndex;
        if (hitDistance != nullptr)
            (*hitDistance) = (float)sweepHit.distance;
    }

    return hasHit;
}

bool pointInsideMesh(const vec3f& point, const physx::PxTriangleMeshGeometry& triMeshGeometry)
{
    // This isn't a very good inside test... we're just casting a ray in an arbitrary direction.

    const vec3f direction(0.f, 0.f, 1.f); // TODO: randomize this? try a few samples?
    const physx::PxU32 maxRaycastHits = 16;
    const physx::PxReal maxDistance = std::numeric_limits<physx::PxReal>::max();

    const physx::PxTransform pose = physx::PxTransform(physx::PxIdentity);
    const physx::PxVec3 pxOrigin = physx::PxVec3(point[0], point[1], point[2]);
    const physx::PxVec3 pxDirection = physx::PxVec3(direction[0], direction[1], direction[2]).getNormalized();

    physx::PxBounds3 bounds = triMeshGeometry.triangleMesh->getLocalBounds();

    // NOTE: this step is unnecessary since pose is just identity, but for the sake of semantic
    // correctness, this is moving from local space to world space...
    bounds = physx::PxBounds3::transformSafe(pose, bounds);

    bool inside = false;
    if (bounds.contains(pxOrigin))
    {
        physx::PxHitFlags hitFlags = physx::PxHitFlag::ePOSITION | physx::PxHitFlag::eMESH_BOTH_SIDES |
                                     physx::PxHitFlag::eNORMAL | physx::PxHitFlag::eMESH_MULTIPLE;

        std::vector<physx::PxGeomRaycastHit> rayHits(maxRaycastHits);

        physx::PxU32 hitCount = physx::PxGeometryQuery::raycast(pxOrigin, pxDirection, triMeshGeometry, pose,
                                                                maxDistance, hitFlags, maxRaycastHits, rayHits.data(),
                                                                physx::PxU32(sizeof(physx::PxGeomRaycastHit)));

        inside = hitCount % 2;

        // If we hit the maximum number of intersections, the mod2 check isn't reliable.
        if (hitCount == maxRaycastHits)
        {
            CARB_LOG_WARN("Point Inside Mesh test -- maximum hits reached; inside test result is unreliable.");
        }
    }

    return inside;
}

} // namespace genproc
} // namespace omni

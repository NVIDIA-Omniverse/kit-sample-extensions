// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#define CARB_EXPORTS

#include "../include/IMeshRaycast.h"
#include "UsdPCH.h"

#include <carb/PluginUtils.h>
#include <carb/eventdispatcher/IEventDispatcher.h>
#include <carb/extras/Hash.h>
#include <carb/settings/SettingsUtils.h>
#include <carb/tasking/TaskingUtils.h>
#include <carb/tokens/TokensUtils.h>

#include <cooking/PxCooking.h>
#include <cooking/PxTriangleMeshDesc.h>
#include <extensions/PxTetrahedronMeshExt.h>
#include <foundation/PxFoundation.h>
#include <geometry/PxMeshQuery.h>
#include <geometry/PxTriangleMesh.h>
#include <omni/activity/IActivity.h>
#include <omni/ext/IExt.h>
#include <omni/geometry/Curves.h>
#include <omni/kit/IApp.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/usd/UsdContext.h>
#include <omni/usd/UsdContextIncludes.h>
#include <pxr/usd/usdGeom/basisCurves.h>
#include <pxr/usd/usdGeom/capsule.h>
#include <pxr/usd/usdGeom/cone.h>
#include <pxr/usd/usdGeom/cube.h>
#include <pxr/usd/usdGeom/cylinder.h>
#include <pxr/usd/usdGeom/points.h>
#include <pxr/usd/usdGeom/sphere.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <PxPhysicsAPI.h>
#include <chrono>
#include <cmath>
#include <limits>
#include <memory>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#define EXTENSION_NAME "omni.meshraycast.plugin"

#define REPORT_OVERLAP_HIT_MT 1
#define ADD_NEW_BOUNDS_MT 1

using namespace carb;
using namespace physx;
using namespace pxr;

using SdfPathUSet = std::unordered_set<SdfPath, SdfPath::Hash>;

const struct PluginImplDesc kPluginImpl = { EXTENSION_NAME, "raycast on usd geometry", "NVIDIA",
                                            PluginHotReload::eEnabled, "dev" };

namespace omni
{
namespace meshraycast
{

struct RaycastContext
{
    SdfPathUSet allowedMeshPaths;
    SdfPathUSet disallowedMeshPaths;
    bool disallowedPathIncludeDescendants{ true };
    std::function<bool(const char*)> hitFilterFn;
};

class CarbErrorCallback : public PxErrorCallback
{
public:
    CarbErrorCallback() = default;

    ~CarbErrorCallback() override = default;

    void reportError(PxErrorCode::Enum code, const char* message, const char* file, int line) override
    {
        switch (code)
        {
            case PxErrorCode::eINVALID_PARAMETER:
            case PxErrorCode::eINVALID_OPERATION:
            case PxErrorCode::eINTERNAL_ERROR:
            case PxErrorCode::eABORT:
            case PxErrorCode::eOUT_OF_MEMORY:
                CARB_LOG_ERROR("PhysX error: %s, FILE %s, LINE %d", message, file, line);
                break;
            case PxErrorCode::eDEBUG_INFO:
                CARB_LOG_INFO("PhysX info: %s, FILE %s, LINE %d", message, file, line);
                break;
            case PxErrorCode::eDEBUG_WARNING:
            case PxErrorCode::ePERF_WARNING:
                CARB_LOG_WARN("PhysX warning: %s, FILE %s, LINE %d", message, file, line);
                break;
            case PxErrorCode::eNO_ERROR:
            case PxErrorCode::eMASK_ALL:
                break;
        }
    }
};

static PxDefaultAllocator s_allocator;
static CarbErrorCallback s_errorCallback;

struct GeomInfo
{
    PxGeometryHolder geomHolder;
    PxTransform pose;
};

struct Axis
{
    enum Enum
    {
        eX,
        eY,
        eZ
    };
};

static const double tolerance = 1e-4;
static const PxF32 gConeOrCylinderWidth = 2.0f;
static const PxF32 gConeOrCylinderRadius = 1.0f;
static const PxU32 gCylinderNumCirclePoints = 30;
static const PxU32 gConeNumCirclePoints = 30;

static constexpr int64_t kBvhRefreshFastIntervalSeconds = -1;
static constexpr int64_t kBvhRefreshSlowIntervalSeconds = 10;

static constexpr char kBvhPreReservedSizeSettingPath[] = "exts/omni.kit.mesh.raycast/bvhPreReservedSize";
static constexpr char kBvhNumPrimsPerLeafSettingPath[] = "exts/omni.kit.mesh.raycast/bvhNumPrimsPerLeaf";
static constexpr char kBvhBuildOnFirstRequiredSettingPath[] = "exts/omni.kit.mesh.raycast/bvhBuildOnFirstRequired";

static void checkNonUniformScale(const GfVec3d& scale, const SdfPath& primPath)
{
    if (abs(scale[0] - scale[1]) > tolerance || abs(scale[0] - scale[2]) > tolerance ||
        abs(scale[2] - scale[1]) > tolerance)
    {
        CARB_LOG_WARN(
            "Non-uniform scale may result in a non matching collision representation on prim: %s", primPath.GetText());
    }
}

static bool isSupportedPrimType(const UsdPrim& prim)
{
    // NOT include xform and no_type prim
    return prim && (prim.IsA<UsdGeomMesh>() || prim.IsA<UsdGeomGprim>() || prim.IsA<UsdGeomBasisCurves>()) &&
           !prim.IsA<UsdGeomCamera>() && !prim.IsA<UsdGeomPoints>();
}

static bool isNotSupportedPrimType(const UsdPrim& prim)
{
    // include xform and no_type prim
    return prim && (prim.IsA<UsdGeomPoints>() || prim.IsA<UsdGeomCamera>());
}

class MeshRaycast final : public IMeshRaycast, public PxBVH::RaycastCallback, public PxBVH::OverlapCallback
{
public:
    void startup() override
    {
        m_foundation = PxCreateFoundation(PX_PHYSICS_VERSION, s_allocator, s_errorCallback);
        m_raycastEventStream = carb::events::getCachedEventsInterface()->createEventStream();
        m_defaultContext = std::make_unique<RaycastContext>();

        auto settings = carb::getCachedInterface<carb::settings::ISettings>();
        settings->setDefaultBool(kBvhBuildOnFirstRequiredSettingPath, true);

        m_preReservedSize.startTracking(kBvhPreReservedSizeSettingPath);
        m_numPrimsPerLeaf.startTracking(kBvhNumPrimsPerLeafSettingPath);
        m_buildBvhOnFirstRequired.startTracking(kBvhBuildOnFirstRequiredSettingPath);

        if (m_defaultCookingParams.midphaseDesc.getType() == PxMeshMidPhase::Enum::eBVH34)
        {
            m_defaultCookingParams.midphaseDesc.mBVH34Desc.numPrimsPerLeaf = m_numPrimsPerLeaf.get();
        }

        m_tasking = carb::getCachedInterface<carb::tasking::ITasking>();

#if REPORT_OVERLAP_HIT_MT
        m_overlapVerticesMutex = std::make_unique<carb::tasking::MutexWrapper>();
#endif

#if ADD_NEW_BOUNDS_MT
        m_incomingMutex = std::make_unique<carb::tasking::MutexWrapper>();
#endif

        m_BVH = nullptr;

        m_CylinderMeshX = nullptr;
        m_CylinderMeshY = nullptr;
        m_CylinderMeshZ = nullptr;

        m_ConeMeshX = nullptr;
        m_ConeMeshY = nullptr;
        m_ConeMeshZ = nullptr;

        m_usdContext = omni::usd::UsdContext::getContext();
        auto stream = m_usdContext->getStageEventStream();
        if (!stream)
        {
            CARB_LOG_ERROR("OMFP-2344: UsdContext without event stream ready!");
            return;
        }
        m_stageEvtSub = createSubscriptionToPop(
            stream.get(),
            [this](carb::events::IEvent* e) {
                switch (static_cast<omni::usd::StageEventType>(e->type))
                {
                    case omni::usd::StageEventType::eOpened:
                        onStageOpened();
                        break;
                    case omni::usd::StageEventType::eClosing:
                        onStageClosing();
                        break;
                    default:
                        break;
                }
            },
            0, "MeshRayCast stage update");

        if (m_usdContext->getStageState() == omni::usd::StageState::eOpened)
        {
            onStageOpened();
        }

        auto ed = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
        m_updateEvtSub = ed->observeEvent(carb::RStringKey("omni.kit.mesh.raycast/update"),
                                          carb::eventdispatcher::kDefaultOrder, omni::kit::kGlobalEventUpdate,
                                          [this](const carb::eventdispatcher::Event& e) { onUpdate(false); });
    }

    void shutdown() override
    {
        onStageClosing();

        m_preReservedSize.stopTracking();
        m_numPrimsPerLeaf.stopTracking();
        m_buildBvhOnFirstRequired.stopTracking();

        m_stageEvtSub = nullptr;
        m_foundation->release();
        m_raycastEventStream = nullptr;
        m_updateEvtSub.reset();

#if REPORT_OVERLAP_HIT_MT
        m_overlapVerticesMutex = nullptr;
#endif

#if ADD_NEW_BOUNDS_MT
        m_incomingMutex = nullptr;
#endif
    }

    RaycastContext* createContext() override
    {
        return new RaycastContext();
    }

    void destroyContext(RaycastContext* context) override
    {
        delete context;
    }

    void setBvhRefreshRate(BvhRefreshRate rate, bool waitForUpdate) override
    {
        // Refresh the BVH now to catch up to latest changes
        m_refreshRate = rate;

        // OM-72233: assume setBvhRefreshRate to fast means start using raycast
        if (m_sceneBuilt == false and rate == BvhRefreshRate::eFast)
        {
            buildScene(rate);
        }
        else if (waitForUpdate)
        {
            onUpdate(true);
        }
    }

    BvhRefreshRate getBvhRefreshRate() const override
    {
        return m_refreshRate;
    }

    void setHitFilterFn(const std::function<bool(const char*)>& fn, RaycastContext* context /* = nullptr*/) override
    {
        context = getActualContext(context);
        context->hitFilterFn = fn;
    }

    void setAllowedMeshPaths(const char* const* paths, size_t count, RaycastContext* context /* = nullptr*/) override
    {
        context = getActualContext(context);

        context->allowedMeshPaths.clear();
        for (size_t i = 0; i < count; i++)
        {
            context->allowedMeshPaths.insert(SdfPath(paths[i]));
        }
    }

    void setDisallowedMeshPaths(const char* const* paths,
                                size_t count,
                                bool includeDescendants,
                                RaycastContext* context /* = nullptr*/) override
    {
        context = getActualContext(context);

        context->disallowedMeshPaths.clear();
        context->disallowedPathIncludeDescendants = includeDescendants;
        for (size_t i = 0; i < count; i++)
        {
            context->disallowedMeshPaths.insert(SdfPath(paths[i]));
        }
    }

    HitResult closestRaycast(const Float3& origin,
                             const Float3& dir,
                             float dist,
                             const RaycastContext* context /* = nullptr*/) override
    {
        CARB_PROFILE_FUNCTION(1);
        ScopedContext scope(this, context);

        m_hitResult.meshIndex = -1;
        if (m_BVH)
        {
            m_castMode = CastMode::eRay;
            m_rayOrigin = PxVec3(origin.x, origin.y, origin.z);
            m_rayDir = PxVec3(dir.x, dir.y, dir.z);
            m_BVH->raycast(m_rayOrigin, m_rayDir, dist, *this);
            m_castMode = CastMode::eNone;
        }
        return m_hitResult;
    }

    BoundResult closestRaycastBound(const Float3& origin,
                                    const Float3& dir,
                                    float dist,
                                    const RaycastContext* context /* = nullptr*/) override
    {
        CARB_PROFILE_FUNCTION(1);
        ScopedContext scope(this, context);

        m_boundResult.meshIndex = -1;
        m_boundResult.distance = dist;
        if (m_BVH)
        {
            m_castMode = CastMode::eBound;
            m_rayOrigin = PxVec3(origin.x, origin.y, origin.z);
            m_rayDir = PxVec3(dir.x, dir.y, dir.z);
            m_BVH->raycast(m_rayOrigin, m_rayDir, dist, *this);
            m_castMode = CastMode::eNone;
        }
        return m_boundResult;
    }

    bool get_prim_doubleside(const SdfPath& primPath)
    {
        auto stage = m_usdContext->getStage();
        auto meshPrim = stage->GetPrimAtPath(primPath);
        auto dsAttr = meshPrim.GetAttribute(UsdGeomTokens->doubleSided);
        bool ds = false;
        if (dsAttr)
        {
            dsAttr.Get(&ds);
        }
        return ds;
    }

    bool reportHit(PxU32 boundsIndex, PxReal& distance) override
    {
        // CARB_PROFILE_FUNCTION(1);
        auto primPath = m_boundsIndexToMeshPath[boundsIndex];

        // If the path is not in allowed paths, continue searching
        if (!isPathAllowed(primPath))
        {
            return true;
        }

        if (m_castMode == CastMode::eBound)
        {
            PxVec3 pos;
            if (getPrimPhysxPos(primPath, pos))
            {
                float prim_distance = (pos - m_rayOrigin).magnitude();
                if (prim_distance <= m_boundResult.distance)
                {
                    m_boundResult.distance = prim_distance;
                    m_boundResult.meshIndex = boundsIndex;
                    distance = prim_distance;
                }
            }

            return true;
        }

        if (getPhysxGeometry(primPath, false))
        {
            PxHitFlags hitFlags = PxHitFlag::ePOSITION | PxHitFlag::eNORMAL;
            if (get_prim_doubleside(primPath))
                hitFlags |= PxHitFlag::eMESH_BOTH_SIDES;

            GeomInfo geomInfo = m_geomMap[primPath];

            switch (m_castMode)
            {
                case CastMode::eRay:
                {
                    PxGeomRaycastHit rayHit;
                    PxU32 hitCount = PxGeometryQuery::raycast(m_rayOrigin, m_rayDir, geomInfo.geomHolder.any(),
                                                              geomInfo.pose, distance, hitFlags, PxU32(1), &rayHit,
                                                              PxU32(sizeof(PxGeomRaycastHit)));

                    if (hitCount > 0 && distance > rayHit.distance)
                    {
                        distance = rayHit.distance;
                        m_hitResult.meshIndex = boundsIndex;
                        m_hitResult.position = Float3({ rayHit.position.x, rayHit.position.y, rayHit.position.z });
                        m_hitResult.normal = Float3({ rayHit.normal.x, rayHit.normal.y, rayHit.normal.z });
                        m_hitResult.faceIndex = uint32_t(-1);

                        if (geomInfo.geomHolder.getType() == PxGeometryType::eTRIANGLEMESH)
                        {
                            auto idxMapEntry = m_trimeshTriIdxToUsdFaceIdxMap.find(primPath);
                            if (idxMapEntry != m_trimeshTriIdxToUsdFaceIdxMap.end())
                            {
                                const auto& triIdxToUsdFace = idxMapEntry->second;
                                auto triMesh = geomInfo.geomHolder.triangleMesh().triangleMesh;
                                const auto& remap = triMesh->getTrianglesRemap();
                                const auto remappedIndex = remap[rayHit.faceIndex];
                                m_hitResult.faceIndex = triIdxToUsdFace[remappedIndex];
                            }
                        }
                    }

                    break;
                }
                case CastMode::eSphere:
                {
                    PxGeomSweepHit sweepHit;
                    bool result = PxGeometryQuery::sweep(m_rayDir, distance, m_shpere, m_transform,
                                                         geomInfo.geomHolder.any(), geomInfo.pose, sweepHit, hitFlags);

                    if (result && distance >= sweepHit.distance)
                    {
                        m_overlapIndices.push_back(boundsIndex);
                    }

                    break;
                }
                default:
                    break;
            }
        }
        return true;
    }

    std::unordered_set<size_t> getVertIndices(const UsdGeomMesh& meshPrim,
                                              const std::unordered_set<size_t>& overlapFaceIndices,
                                              const size_t minFaceIndex,
                                              const size_t maxFaceIndex) const
    {
        CARB_PROFILE_ZONE(1, "getVertIndices");

        std::unordered_set<size_t> overlapVertIndices;

        // Get the vertex index from USD prim.
        // Do not use triMesh->getTriangles() and triMesh->getVertices(). If the mesh has unused points,
        // they will be optimized out and result in wrong overlap vert index
        VtArray<GfVec3f> meshPoints;
        VtArray<int32_t> faceVertexCounts;
        VtArray<int32_t> faceVertexIndices;

        meshPrim.GetPointsAttr().Get(&meshPoints);
        meshPrim.GetFaceVertexCountsAttr().Get(&faceVertexCounts);
        meshPrim.GetFaceVertexIndicesAttr().Get(&faceVertexIndices);

        const GfMatrix4d localToWorld = computeWorldTransform(meshPrim.GetPrim());
        PxReal radiusSqr = m_shpere.radius * m_shpere.radius;

        size_t vertexOffset = 0;
        for (size_t i = 0; i <= maxFaceIndex; i++)
        {
            const int32_t faceVertexCount = faceVertexCounts[i];

            if (i >= minFaceIndex)
            {
                if (overlapFaceIndices.find(i) != overlapFaceIndices.end())
                {
                    for (size_t fvi = 0; fvi < faceVertexCount; fvi++)
                    {
                        const int32_t vertIndex = faceVertexIndices[vertexOffset + fvi];

                        if (overlapVertIndices.find(vertIndex) != overlapVertIndices.end())
                        {
                            continue;
                        }

                        const auto& position = meshPoints[vertIndex];

                        GfVec3f vWorld = GfVec3f(localToWorld.Transform(position));

                        if ((m_rayOrigin - *reinterpret_cast<PxVec3*>(&vWorld)).magnitudeSquared() <= radiusSqr)
                        {
                            overlapVertIndices.insert(vertIndex);
                        }
                    }
                }
            }

            vertexOffset += faceVertexCount;
        }

        return overlapVertIndices;
    }

    HitResult closestRaycastMesh(std::string& meshPath,
                                 const carb::Float3& origin,
                                 const carb::Float3& dir,
                                 float dist,
                                 bool forceCooking) override
    {
        CARB_PROFILE_FUNCTION(1);

        m_hitResult.meshIndex = -1;
        auto primPath = SdfPath(meshPath);
        if (getPhysxGeometry(primPath, forceCooking))
        {
            GeomInfo geomInfo = m_geomMap[primPath];

            PxHitFlags hitFlags = PxHitFlag::ePOSITION | PxHitFlag::eNORMAL;
            if (get_prim_doubleside(primPath))
                hitFlags |= PxHitFlag::eMESH_BOTH_SIDES;
            PxGeomRaycastHit rayHit;
            PxVec3 pxOrigin = PxVec3(origin.x, origin.y, origin.z);
            PxVec3 pxDir = PxVec3(dir.x, dir.y, dir.z);
            PxU32 hitCount = PxGeometryQuery::raycast(pxOrigin, pxDir, geomInfo.geomHolder.any(), geomInfo.pose, dist,
                                                      hitFlags, PxU32(1), &rayHit, PxU32(sizeof(PxGeomRaycastHit)));

            if (hitCount > 0)
            {
                m_hitResult.meshIndex = 0;
                m_hitResult.position = Float3({ rayHit.position.x, rayHit.position.y, rayHit.position.z });
                m_hitResult.normal = Float3({ rayHit.normal.x, rayHit.normal.y, rayHit.normal.z });
                m_hitResult.faceIndex = uint32_t(-1);
                if (geomInfo.geomHolder.getType() == PxGeometryType::eTRIANGLEMESH)
                {
                    auto idxMapEntry = m_trimeshTriIdxToUsdFaceIdxMap.find(primPath);
                    if (idxMapEntry != m_trimeshTriIdxToUsdFaceIdxMap.end())
                    {
                        const auto& triIdxToUsdFace = idxMapEntry->second;
                        auto triMesh = geomInfo.geomHolder.triangleMesh().triangleMesh;
                        const auto& remap = triMesh->getTrianglesRemap();
                        const auto& remappedIndex = remap[rayHit.faceIndex];
                        m_hitResult.faceIndex = triIdxToUsdFace[remappedIndex];
                    }
                }
            }
        }
        return m_hitResult;
    }

    OverlapResult spherecast(const carb::Float3& origin,
                             const carb::Float3& dir,
                             float radius,
                             float dist,
                             const RaycastContext* context = nullptr) override
    {
        CARB_PROFILE_FUNCTION(1);
        ScopedContext scope(this, context);

        m_overlapIndices.clear();
        if (m_BVH)
        {
            m_castMode = CastMode::eSphere;
            m_shpere.radius = radius;
            m_rayOrigin = PxVec3(origin.x, origin.y, origin.z);
            m_rayDir = PxVec3(dir.x, dir.y, dir.z);
            m_transform = PxTransform(m_rayOrigin);

            m_BVH->sweep(m_shpere, m_transform, m_rayDir, dist, *this);
            m_castMode = CastMode::eNone;
        }
        OverlapResult result{ nullptr, 0 };

        auto size = m_overlapIndices.size();
        if (size > 0)
        {
            result.meshIndices = new size_t[size];
            result.size = size;
            memcpy(result.meshIndices, m_overlapIndices.data(), size * sizeof(size_t));
        }

        return result;
    }

    void freeOverlapResult(OverlapResult& result) override
    {
        if (result.size > 0)
        {
            delete[] result.meshIndices;
            result.size = 0;
        }
    }

    // Reports one overlap hit.
    // boundsIndex	[in] Index of touched bounds
    // return false to abort the query
    bool reportHit(PxU32 boundsIndex) override
    {
#if REPORT_OVERLAP_HIT_MT
        auto primPath = m_boundsIndexToMeshPath[boundsIndex];
        {
            auto stage = m_usdContext->getStage();
            auto prim = stage->GetPrimAtPath(primPath);

            // If the path is not in allowed paths, continue searching
            if (!isPathAllowed(primPath))
            {
                return true;
            }

            if (isSupportedPrimType(prim))
            {
                // xformCache is not thread safe, so fetch it here in main thread
                GfMatrix4d localToWorld = computeWorldTransform(prim);

                m_overlapBoundsIndices.emplace_back(boundsIndex, localToWorld);
            }
        }
#else
        reportHitJob(boundsIndex);
#endif

        return true;
    }

    // This job is run by carb::tasking if REPORT_OVERLAP_HIT_MT is on, otherwise it runs on main thread.
    void reportHitJob(PxU32 boundsIndex, const GfMatrix4d* cachedXform = nullptr)
    {
        // CARB_PROFILE_FUNCTION(1);
        const SdfPath primPath = m_boundsIndexToMeshPath[boundsIndex];
        auto meshPrim = UsdGeomMesh::Get(m_stage, primPath);
        if (!meshPrim)
        {
            return;
        }

#if !REPORT_OVERLAP_HIT_MT
        // If the path is not in allowed paths, continue searching
        if (!isPathAllowed(primPath))
        {
            return;
        }
#endif

        if (getPhysxGeometry(primPath, false, cachedXform))
        {
            CARB_ASSERT(m_castMode == CastMode::eOverlapVertices);
            PxU32 numOverlaps = 0;

            GeomInfo geomInfo = m_geomMap[primPath];

            if (geomInfo.geomHolder.getType() == PxGeometryType::eTRIANGLEMESH)
            {
                auto triMesh = geomInfo.geomHolder.triangleMesh().triangleMesh;

                std::vector<PxU32> results;
                results.resize(triMesh->getNbTriangles());
                bool overflow;

                {
                    CARB_PROFILE_ZONE(1, "PxMeshQuery::findOverlapTriangleMesh");
                    numOverlaps = PxMeshQuery::findOverlapTriangleMesh(
                        m_shpere, m_transform, geomInfo.geomHolder.triangleMesh(), geomInfo.pose, results.data(),
                        PxU32(results.size()), 0, overflow);
                }

                if (numOverlaps)
                {
                    CARB_PROFILE_ZONE(1, "remap overlap faces");

                    results.resize(numOverlaps);

                    std::unordered_set<size_t> overlapFaceIndices;
                    overlapFaceIndices.reserve(numOverlaps);
                    size_t minFaceIndex = std::numeric_limits<size_t>::max();
                    size_t maxFaceIndex = std::numeric_limits<size_t>::min();
                    auto idxMapEntry = m_trimeshTriIdxToUsdFaceIdxMap.find(primPath);
                    if (idxMapEntry != m_trimeshTriIdxToUsdFaceIdxMap.end())
                    {
                        const auto trianglesRemaps = triMesh->getTrianglesRemap();
                        const auto& triIdxToUsdFace = idxMapEntry->second;
                        for (const PxU32 index : results)
                        {
                            const PxU32 remappedIndex = trianglesRemaps[index];
                            if (remappedIndex < triIdxToUsdFace.size())
                            {
                                const size_t faceIndex = triIdxToUsdFace[remappedIndex];
                                overlapFaceIndices.insert(faceIndex);
                                if (faceIndex >= maxFaceIndex)
                                {
                                    maxFaceIndex = faceIndex;
                                }
                                if (faceIndex <= minFaceIndex)
                                {
                                    minFaceIndex = faceIndex;
                                }
                            }
                        }
                    }

                    VtArray<int32_t> faceVertexCounts;
                    meshPrim.GetFaceVertexCountsAttr().Get(&faceVertexCounts);

                    if (maxFaceIndex >= faceVertexCounts.size())
                    {
                        CARB_LOG_ERROR("%llu >= %llu", maxFaceIndex, faceVertexCounts.size());
                    }

                    std::unordered_set<size_t> overlapVertIndices =
                        getVertIndices(meshPrim, overlapFaceIndices, minFaceIndex, maxFaceIndex);

                    {
                        CARB_PROFILE_ZONE(1, "accumulate result");
                        // If indices is empty, we still return the mesh that's overlapped with brush

#if REPORT_OVERLAP_HIT_MT
                        std::unique_lock<carb::tasking::MutexWrapper> lock(*m_overlapVerticesMutex);
#endif
                        auto& overlapVertices = m_overlapVertices[boundsIndex];
                        auto& overlapFaces = m_overlapFaces[boundsIndex];

#if REPORT_OVERLAP_HIT_MT
                        // Unlock it. From this point each thread won't access same memory location in the maps
                        lock.unlock();
#endif

                        overlapVertices.reserve(overlapVertIndices.size());
                        overlapVertices.assign(overlapVertIndices.begin(), overlapVertIndices.end());
                        m_totalOverlapVerticesCount.fetch_add(overlapVertIndices.size(), std::memory_order_relaxed);

                        overlapFaces.reserve(overlapFaceIndices.size());
                        overlapFaces.assign(overlapFaceIndices.begin(), overlapFaceIndices.end());
                        m_totalOverlapFacesCount.fetch_add(overlapFaceIndices.size(), std::memory_order_relaxed);
                    }
                }
            }
            else
            {
                // TODO: Handle other types
            }
        }
    }

    OverlapVerticesResult overlapVertices(const carb::Float3& origin,
                                          float radius,
                                          const RaycastContext* context /* = nullptr*/) override
    {
        CARB_PROFILE_FUNCTION(1);

        ScopedContext scope(this, context);

        m_overlapVertices.clear();
        m_overlapBoundsIndices.clear();
        m_overlapFaces.clear();
        m_totalOverlapVerticesCount = 0;
        m_totalOverlapFacesCount = 0;
        if (m_BVH)
        {
            m_castMode = CastMode::eOverlapVertices;
            m_shpere.radius = radius;
            m_rayOrigin = PxVec3(origin.x, origin.y, origin.z);
            m_transform = PxTransform(m_rayOrigin);

            m_BVH->overlap(m_shpere, m_transform, *this);
            m_overlapVertices.reserve(m_overlapBoundsIndices.size());

#if REPORT_OVERLAP_HIT_MT
            m_tasking->parallelFor<size_t>(0, m_overlapBoundsIndices.size(), [this](size_t i) {
                const auto& pair = m_overlapBoundsIndices[i];
                reportHitJob(pair.first, &pair.second);
            });
#endif

            m_castMode = CastMode::eNone;
        }

        OverlapVerticesResult result{ 0 };
        {
            CARB_PROFILE_ZONE(1, "pack overlap result");

            auto vertSize = m_overlapVertices.size();
            auto faceSize = m_overlapFaces.size();
            if (vertSize > 0 && vertSize == faceSize)
            {
                CARB_PROFILE_BEGIN(1, "Allocate Buffers");

                result.meshSize = vertSize;
                result.meshIndices = new int32_t[vertSize];

                result.vertexIndicesSize = new size_t[vertSize];
                result.vertexIndices = new size_t[m_totalOverlapVerticesCount.load(std::memory_order_relaxed)];

                result.faceIndicesSize = new size_t[faceSize];
                result.faceIndices = new size_t[m_totalOverlapFacesCount.load(std::memory_order_relaxed)];
                CARB_PROFILE_END(1);

                size_t resultMeshIdx = 0;
                size_t vertexIndicesOffset = 0;
                size_t faceIndicesOffset = 0;
                CARB_PROFILE_BEGIN(1, "Fill Buffers");
                for (const auto& entry : m_overlapVertices)
                {
                    result.meshIndices[resultMeshIdx] = entry.first;
                    result.vertexIndicesSize[resultMeshIdx] = entry.second.size();
                    memcpy(&result.vertexIndices[vertexIndicesOffset], entry.second.data(),
                           entry.second.size() * sizeof(size_t));
                    vertexIndicesOffset += entry.second.size();

                    // add overlapped faces for the same mesh index
                    const auto& facesEntry = m_overlapFaces.find(entry.first);
                    if (facesEntry != m_overlapFaces.end())
                    {
                        result.faceIndicesSize[resultMeshIdx] = facesEntry->second.size();
                        memcpy(&result.faceIndices[faceIndicesOffset], facesEntry->second.data(),
                               facesEntry->second.size() * sizeof(size_t));
                        faceIndicesOffset += facesEntry->second.size();
                    }
                    else
                    {
                        CARB_LOG_ERROR("Mismatch between overlapped faces and overlapped vertices");
                    }

                    resultMeshIdx++;
                }
                CARB_PROFILE_END(1);
            }
            else if (vertSize != faceSize)
            {
                CARB_LOG_ERROR("Overlap Vertices count %llu not equal to overlap Faces count %llu", vertSize, faceSize);
            }
        }

        return result;
    }

    void freeOverlapVerticesResult(OverlapVerticesResult& result) override
    {
        if (result.vertexIndices)
        {
            delete[] result.vertexIndices;
        }

        if (result.faceIndices)
        {
            delete[] result.faceIndices;
        }

        if (result.meshIndices)
        {
            delete[] result.meshIndices;
        }

        if (result.vertexIndicesSize)
        {
            delete[] result.vertexIndicesSize;
        }

        result = { 0 };
    }

    const char* getMeshPathFromIndex(int32_t index) override
    {
        auto entry = m_boundsIndexToMeshPath.find(index);
        if (entry != m_boundsIndexToMeshPath.end())
        {
            return entry->second.GetText();
        }
        return "";
    }

    size_t getMeshPathCount() const override
    {
        return m_boundsIndexToMeshPath.size();
    }

    void getMeshPaths(const char** paths, size_t count) const override
    {
        size_t index = 0;
        for (const auto& entry : m_boundsIndexToMeshPath)
        {
            if (index >= count)
            {
                break;
            }
            paths[index++] = entry.second.GetText();
        }
    }

    carb::events::IEventStream* getMeshRaycastEventStream() override
    {
        return m_raycastEventStream.get();
    }

    void getFloodPoints(const std::string& meshPath,
                        const float density,
                        const bool forceCooking,
                        std::vector<carb::Float3>& positions,
                        std::vector<carb::Float3>& normals) override
    {
        auto primPath = SdfPath(meshPath);
        if (getPhysxGeometry(primPath, false))
        {
            auto stage = m_usdContext->getStage();
            auto prim = stage->GetPrimAtPath(primPath);
            if (!prim.IsValid())
                return;

            GeomInfo geomInfo = m_geomMap[primPath];

            if (prim.IsA<UsdGeomMesh>())
            {
                PxTriangleMeshGeometry triMeshGeometry = geomInfo.geomHolder.triangleMesh();

                auto triMesh = triMeshGeometry.triangleMesh;
                auto scale = triMeshGeometry.scale.scale;
                if (triMesh->getTriangleMeshFlags() & PxTriangleMeshFlag::e16_BIT_INDICES)
                    samplingOnTriMesh<PxU16>(triMesh, geomInfo.pose, scale, density, positions, normals);
                else
                    samplingOnTriMesh<PxU32>(triMesh, geomInfo.pose, scale, density, positions, normals);
            }
            else if (prim.IsA<UsdGeomCylinder>() || prim.IsA<UsdGeomCone>())
            {
                PxConvexMeshGeometry convexMeshGeometry = geomInfo.geomHolder.convexMesh();
                auto convexMesh = convexMeshGeometry.convexMesh;
                auto scale = convexMeshGeometry.scale.scale;
                samplingOnConvexMesh(convexMesh, geomInfo.pose, scale, density, positions, normals);
            }
            else if (prim.IsA<UsdGeomSphere>())
            {
                PxSphereGeometry sphere = geomInfo.geomHolder.sphere();
                samplingOnSphere(geomInfo.pose, sphere.radius, density, positions, normals);
            }
            else if (prim.IsA<UsdGeomCube>())
            {
                PxBoxGeometry box = geomInfo.geomHolder.box();
                samplingOnBox(geomInfo.pose, box.halfExtents, density, positions, normals);
            }
            else if (prim.IsA<UsdGeomCapsule>())
            {
                PxCapsuleGeometry capsule = geomInfo.geomHolder.capsule();
                samplingOnCapsule(geomInfo.pose, capsule.halfHeight, capsule.radius, density, positions, normals);
            }
        }
    }

    bool getVertexLocalPositions(const char* meshPath,
                                 const std::vector<size_t>& vertIndexes,
                                 std::vector<carb::Float3>& positions) const override
    {
        // Do not use triMesh->getVertices();. If mesh has unused points it will give wrong result.
        auto meshPrim = UsdGeomMesh::Get(m_stage, SdfPath(meshPath));

        if (meshPrim)
        {
            VtArray<GfVec3f> meshPoints;
            meshPrim.GetPointsAttr().Get(&meshPoints);
            positions.reserve(vertIndexes.size());
            for (auto i = 0; i < vertIndexes.size(); i++)
            {
                auto vertIdx = vertIndexes[i];
                if (vertIdx < meshPoints.size())
                {
                    const auto& vert = meshPoints[vertIdx];
                    carb::Float3 position;
                    position.x = vert[0];
                    position.y = vert[1];
                    position.z = vert[2];
                    positions.push_back(position);
                }
                else
                {
                    positions.clear();
                    return false;
                }
            }
            return true;
        }

        return false;
    }

    CurveTessellateResult tessellateCurve(const char* path, size_t stepsPerSegment, bool fillTangents) const override
    {
        CARB_PROFILE_FUNCTION(1);

        using namespace omni::geometry::curves;

        using omni::math::linalg::safeCastToOmni;
        using omni::math::linalg::vec3f;

        CurveTessellateResult result{ 0 };

        UsdGeomBasisCurves primCurve = UsdGeomBasisCurves::Get(m_stage, SdfPath(path));

        if (!primCurve)
        {
            return result;
        }

        VtArray<pxr::GfVec3f> pointsUSD;
        if (!primCurve.GetPointsAttr().Get(&pointsUSD))
        {
            return result;
        }

        auto curve = createSplineCurveFromBasisCurvesPrim(primCurve);
        if (!curve)
        {
            return result;
        }

        std::vector<vec3f> points(safeCastToOmni(pointsUSD.data()), safeCastToOmni(pointsUSD.data() + pointsUSD.size()));

        VtIntArray curveVertexCounts;
        primCurve.GetCurveVertexCountsAttr().Get(&curveVertexCounts);
        size_t curveCount = curveVertexCounts.size();

        size_t startIdx = 0;
        std::vector<size_t> positonCounts;
        std::vector<vec3f> flattenedTessellatedPositions;
        std::vector<size_t> tangentCounts;
        std::vector<vec3f> flattenedTessellatedTangents;

        positonCounts.reserve(curveCount);
        tangentCounts.reserve(curveCount);

        result.curveCount = curveCount;

        for (size_t i = 0; i < curveCount; i++)
        {
            std::vector<vec3f> tessellatedPositions;
            std::vector<vec3f> tessellatedTangents;

            const size_t count = curveVertexCounts[i];
            std::vector<vec3f> controlPoints(points.begin() + startIdx, points.begin() + startIdx + count);
            curve->tessellate(controlPoints.data(), controlPoints.size(), tessellatedPositions, stepsPerSegment, false,
                              fillTangents ? &tessellatedTangents : nullptr);

            positonCounts.push_back(tessellatedPositions.size());
            if (tessellatedPositions.size())
            {
                flattenedTessellatedPositions.reserve(flattenedTessellatedPositions.size() + tessellatedPositions.size());
                flattenedTessellatedPositions.insert(
                    flattenedTessellatedPositions.end(), tessellatedPositions.begin(), tessellatedPositions.end());
            }

            tangentCounts.push_back(tessellatedTangents.size());
            if (tessellatedTangents.size())
            {
                flattenedTessellatedTangents.reserve(flattenedTessellatedTangents.size() + tessellatedTangents.size());
                flattenedTessellatedTangents.insert(
                    flattenedTessellatedTangents.end(), tessellatedTangents.begin(), tessellatedTangents.end());
            }

            startIdx += count;
        }

        result.positionCounts = new size_t[positonCounts.size()];
        memcpy(result.positionCounts, positonCounts.data(), sizeof(size_t) * positonCounts.size());

        result.positions = new vec3f[flattenedTessellatedPositions.size()];
        memcpy(result.positions, flattenedTessellatedPositions.data(),
               sizeof(vec3f) * flattenedTessellatedPositions.size());

        result.tangentCounts = new size_t[tangentCounts.size()];
        memcpy(result.tangentCounts, tangentCounts.data(), sizeof(size_t) * tangentCounts.size());

        result.tangents = new vec3f[flattenedTessellatedTangents.size()];
        memcpy(result.tangents, flattenedTessellatedTangents.data(), sizeof(vec3f) * flattenedTessellatedTangents.size());

        return result;
    }

    void freeCurveTessellateResult(CurveTessellateResult& result) const override
    {
        if (result.positionCounts)
        {
            delete[] result.positionCounts;
            result.positionCounts = nullptr;
        }

        if (result.positions)
        {
            delete[] result.positions;
            result.positions = nullptr;
        }

        if (result.tangentCounts)
        {
            delete[] result.tangentCounts;
            result.tangentCounts = nullptr;
        }

        if (result.tangents)
        {
            delete[] result.tangents;
            result.tangents = nullptr;
        }
    }

    bool sampleCurveSegmentAtT(const char* path,
                               size_t curveIndex,
                               size_t segmentIndex,
                               float t,
                               usdrt::GfVec3f* position,
                               usdrt::GfVec3f* tangent) const override
    {
        CARB_PROFILE_FUNCTION(1);
        using namespace omni::geometry::curves;

        using omni::math::linalg::safeCastToOmni;
        using omni::math::linalg::vec3f;

        UsdGeomBasisCurves primCurve = UsdGeomBasisCurves::Get(m_stage, SdfPath(path));

        if (!primCurve)
        {
            return false;
        }

        VtArray<pxr::GfVec3f> pointsUSD;
        if (!primCurve.GetPointsAttr().Get(&pointsUSD))
        {
            return false;
        }

        auto curve = createSplineCurveFromBasisCurvesPrim(primCurve);
        if (!curve)
        {
            return false;
        }

        std::vector<vec3f> points(safeCastToOmni(pointsUSD.data()), safeCastToOmni(pointsUSD.data() + pointsUSD.size()));

        VtIntArray curveVertexCounts;
        primCurve.GetCurveVertexCountsAttr().Get(&curveVertexCounts);
        size_t curveCount = curveVertexCounts.size();

        std::vector<vec3f> tessellatedPositions;
        std::vector<vec3f> tessellatedTangents;

        size_t curveVertexOffset = 0;
        for (size_t i = 0; i < curveCount; i++)
        {
            size_t count = curveVertexCounts[i];
            if (i == curveIndex)
            {
                const size_t count = curveVertexCounts[i];
                std::vector<vec3f> controlPoints(
                    points.begin() + curveVertexOffset, points.begin() + curveVertexOffset + count);
                curve->tessellate(controlPoints.data(), controlPoints.size(), tessellatedPositions,
                                  std::vector<float>{ float(segmentIndex + t) },
                                  tangent ? &tessellatedTangents : nullptr);

                break;
            }
            curveVertexOffset += count;
        }

        if (tessellatedPositions.size() == 1)
        {
            *position = tessellatedPositions[0];
            if (tangent && tessellatedTangents.size() == 1)
            {
                *tangent = tessellatedTangents[0];
            }
            return true;
        }

        return false;
    }

private:
    enum class CastMode
    {
        eNone,
        eRay,
        eSphere,
        eOverlapVertices,
        eBound
    };

    struct UsdStageNoticeListener : public TfWeakBase
    {
        UsdStageNoticeListener(MeshRaycast* meshRaycast, UsdStageWeakPtr& stage)
            : m_meshRaycast(meshRaycast), m_stage(stage)
        {
            registerListener();
        }

        ~UsdStageNoticeListener()
        {
            revokeListener();
        }

        void registerListener()
        {
            m_usdNoticeListenerKey = TfNotice::Register(TfCreateWeakPtr(this), &UsdStageNoticeListener::handleNotice);
        }

        void revokeListener()
        {
            if (m_usdNoticeListenerKey.IsValid())
            {
                TfNotice::Revoke(m_usdNoticeListenerKey);
            }
        }

        void handleNotice(const UsdNotice::ObjectsChanged& objectsChanged)
        {
            if (m_stage && m_stage != objectsChanged.GetStage())
            {
                return;
            }

            // Store changed paths and handle later to minimize impact on USD notice

            for (const auto& path : objectsChanged.GetResyncedPaths())
            {
                m_resyncedPaths.push_back(path);
            }

            for (const auto& path : objectsChanged.GetChangedInfoOnlyPaths())
            {
                m_changedPaths.insert(path);
            }
        }

        void onUpdate(bool force)
        {
            if (!m_stage)
            {
                return;
            }

            auto now = std::chrono::high_resolution_clock::now();
            if (force or
                now - m_meshRaycast->m_lastBvhRefreshTime >= ((m_meshRaycast->m_refreshRate == BvhRefreshRate::eFast) ?
                                                                  std::chrono::seconds(kBvhRefreshFastIntervalSeconds) :
                                                                  std::chrono::seconds(kBvhRefreshSlowIntervalSeconds)))
            {
                handleUsdChanges();
                m_meshRaycast->m_lastBvhRefreshTime = now;
            }
        }

        bool hasPrefixesIn(const SdfPath& path, const SdfPathUSet& paths) const
        {
            auto prefixes = path.GetPrimPath().GetPrefixes();
            for (const auto& prefix : prefixes)
            {
                if (paths.find(prefix) != paths.end())
                {
                    return true;
                }
            }

            return false;
        }

        void handleUsdChanges()
        {
            CARB_PROFILE_FUNCTION(1);

            if (m_resyncedPaths.empty() && m_changedPaths.empty())
            {
                return;
            }

            SdfPath::RemoveDescendentPaths(&m_resyncedPaths);
            SdfPathUSet pathsToReadd, pathsToRemove;

            // If newly added path is or contains mesh descendant, rebuild BVH
            // If remove path was in BVH, rebuild
            for (const auto& path : m_resyncedPaths)
            {
                auto primPath = path.GetAbsoluteRootOrPrimPath();
                auto resyncedPrim = m_stage->GetPrimAtPath(primPath);
                if (resyncedPrim.IsValid())
                {
                    auto imageable = UsdGeomImageable(resyncedPrim);
                    if (imageable and imageable.ComputeVisibility() == UsdGeomTokens->invisible)
                    {
                        pathsToRemove.insert(primPath);
                    }
                    else
                    {
                        // if mesh is added, or removed then added again, or some of its descendants changed and this is
                        // the nearest common ancestor
                        auto buildablePaths = m_meshRaycast->getBuildableDescendantPaths(primPath);
                        pathsToReadd.insert(buildablePaths.begin(), buildablePaths.end());
                    }
                }
                else
                {
                    // if mesh is removed
                    if (m_meshRaycast->m_meshPathBoundsIndices.find(primPath) !=
                        m_meshRaycast->m_meshPathBoundsIndices.end())
                    {
                        pathsToRemove.insert(primPath);
                    }
                }
            }

            // Need to handleChangedPaths before requestRebuildBVH, so old bounds are up to date for info changed only
            // paths
            handleChangedPaths(pathsToReadd, pathsToRemove);
            if (!pathsToReadd.empty() || !pathsToRemove.empty())
            {
                m_meshRaycast->requestRebuildBVH(pathsToReadd, pathsToRemove);
            }

            m_resyncedPaths.clear();
        }

        bool updateBvh(const SdfPath& primPath)
        {
            CARB_PROFILE_FUNCTION(1);
            bool ret = false;

            auto boundIndexEntry = m_meshRaycast->m_meshPathBoundsIndices.find(primPath);
            if (boundIndexEntry != m_meshRaycast->m_meshPathBoundsIndices.end())
            {
                const MeshPathsData& indices = boundIndexEntry->second;
                for (PxU32 index : indices.selfAndDescendantsIndices)
                {
                    SdfPath& thisPrimPath = m_meshRaycast->m_boundsIndexToMeshPath[index];
                    auto prim = m_stage->GetPrimAtPath(thisPrimPath);
                    if (isSupportedPrimType(prim))
                    {
                        auto bbox = m_meshRaycast->computeWorldBoundingBox(prim);
                        auto _min = bbox.GetMin();
                        auto _max = bbox.GetMax();

                        PxBounds3 pxBound(PxVec3((float)_min[0], (float)_min[1], (float)_min[2]),
                                          PxVec3((float)_max[0], (float)_max[1], (float)_max[2]));

                        ret |= m_meshRaycast->m_BVH->updateBounds(index, pxBound);

                        if (ret)
                        {
                            // transform changed, update geomInfo (pose/scale) if presents
                            updateGeomInfo(prim);
                        }
                    }
                }
            }
            return ret;
        }

        void updateGeomInfo(const UsdPrim& prim)
        {
            auto geomInfoEntry = m_meshRaycast->m_geomMap.find(prim.GetPath());
            if (geomInfoEntry != m_meshRaycast->m_geomMap.end())
            {
                const GfMatrix4d localToWorld = m_meshRaycast->computeWorldTransform(prim);

                pxr::GfVec3d translation;
                pxr::GfMatrix4d rotMat(1.0);
                pxr::GfVec3d doubleScale(1.0);
                pxr::GfMatrix4d scaleOrientMatUnused, perspMatUnused;
                localToWorld.Factor(&scaleOrientMatUnused, &doubleScale, &rotMat, &translation, &perspMatUnused);
                rotMat.Orthonormalize(false);
                pxr::GfQuatd quat = rotMat.ExtractRotationQuat();

                PxTransform pose;
                pose.p = PxVec3((float)translation[0], (float)translation[1], (float)translation[2]);
                pose.q = PxQuat((float)quat.GetImaginary()[0], (float)quat.GetImaginary()[1],
                                (float)quat.GetImaginary()[2], (float)quat.GetReal());

                auto& geomInfo = geomInfoEntry->second;
                geomInfo.pose = pose;
                if (geomInfo.geomHolder.getType() == PxGeometryType::eTRIANGLEMESH)
                {
                    PxVec3 pxScale = PxVec3((float)doubleScale[0], (float)doubleScale[1], (float)doubleScale[2]);

                    geomInfo.geomHolder.triangleMesh().scale = PxMeshScale(pxScale);
                }
            }
        }

        void handleChangedPaths(SdfPathUSet& pathsToReadd, SdfPathUSet& pathsToRemove)
        {
            CARB_PROFILE_FUNCTION(1);

            SdfPathVector pathsToUpdateBvh;
            std::unordered_set<SdfPath, SdfPath::Hash> pathsToClearTriMesh;

            pathsToUpdateBvh.reserve(m_changedPaths.size());
            for (const auto& path : m_changedPaths)
            {
                if (hasPrefixesIn(path, pathsToReadd) || hasPrefixesIn(path, pathsToRemove))
                {
                    continue;
                }

                auto primPath = path.GetPrimPath();
                auto nameToken = path.GetNameToken();

                if (m_meshRaycast->m_meshPathBoundsIndices.find(primPath) == m_meshRaycast->m_meshPathBoundsIndices.end())
                {
                    if (nameToken == UsdGeomTokens->visibility and isVisible(primPath))
                    {
                        // add it in BVH
                        // although the visible changed prefixes will in m_changedPaths, we should add them before this
                        // primpath.
                        auto prefixes = primPath.GetPrefixes();
                        bool support = true;
                        for (const auto& prefix : prefixes)
                        {
                            auto prim = m_stage->GetPrimAtPath(prefix);
                            if (isNotSupportedPrimType(prim))
                            {
                                support = false;
                                break;
                            }
                        }
                        if (!support)
                            continue;

                        for (const auto& prefix : prefixes)
                        {
                            if (m_meshRaycast->m_meshPathBoundsIndices.find(prefix) ==
                                m_meshRaycast->m_meshPathBoundsIndices.end())
                            {
                                auto prim = m_stage->GetPrimAtPath(prefix);
                                if (isSupportedPrimType(prim))
                                {
                                    pathsToReadd.insert(prefix);
                                }
                            }
                        }

                        auto buildablePaths = m_meshRaycast->getBuildableDescendantPaths(primPath);
                        for (auto path : buildablePaths)
                        {
                            pathsToReadd.insert(path);
                        }
                    }
                    continue;
                }

                // If the changed info can affect ray cast result, clear the cached triangle info
                // Add more attributes to track if necessary.
                if (nameToken == UsdGeomTokens->points || nameToken == UsdGeomTokens->extent)
                {
                    pathsToClearTriMesh.insert(primPath);

                    // Updates the bounds in BVH
                    if (nameToken == UsdGeomTokens->extent)
                    {
                        pathsToUpdateBvh.push_back(primPath);
                    }
                }
                else if (UsdGeomXform::IsTransformationAffectedByAttrNamed(nameToken))
                {
                    // If mesh transform changed, world bound will change. Update the BVH
                    // No need to clear m_geomMap
                    pathsToUpdateBvh.push_back(primPath);
                }
                else if (nameToken == UsdGeomTokens->visibility)
                {
                    // remove it from BVH
                    if (!isVisible(primPath))
                    {
                        pathsToRemove.insert(primPath);
                    }
                    else
                    {
                        // only the prim be added by custom script
                        CARB_LOG_INFO("it queryable but invisible: %s\n", primPath.GetText());
                    }
                }
            }

            // tri mesh needs to be rebuilt since points changed
            for (const auto& path : pathsToClearTriMesh)
            {
                m_meshRaycast->m_geomMap.erase(path);
            }

            // removes all descendants. If a prim's ancestor's transform has changed, the prim itself's bounds need to
            // be updated too. updateBvh will process all descendants of paths in pathsToUpdateBvh
            PXR_NS::SdfPath::RemoveDescendentPaths(&pathsToUpdateBvh);

            bool needsRefit = false;
            for (const auto& path : pathsToUpdateBvh)
            {
                needsRefit |= updateBvh(path);
            }

            if (needsRefit)
            {
                if (pathsToReadd.empty() && pathsToRemove.empty())
                {
                    m_meshRaycast->m_BVH->partialRefit();
                }
            }

            m_changedPaths.clear();
        }

    private:
        TfNotice::Key m_usdNoticeListenerKey;
        MeshRaycast* m_meshRaycast;
        UsdStageWeakPtr m_stage;

        std::unordered_set<SdfPath, SdfPath::Hash> m_changedPaths;
        SdfPathVector m_resyncedPaths;

        bool isVisible(SdfPath& primPath)
        {
            auto prim = m_stage->GetPrimAtPath(primPath);
            // OM-66407: this prim maybe removed at same time
            if (prim.IsValid())
            {
                UsdGeomImageable imageable = UsdGeomImageable(prim);
                return imageable.ComputeVisibility() != UsdGeomTokens->invisible;
            }
            return false;
        }
    };

    struct MeshPathsData
    {
        PxU32 selfIndex = std::numeric_limits<PxU32>::max(); // Invalid for ancestor-only entries
        std::unordered_set<PxU32> selfAndDescendantsIndices; // all bounds indices of itself and all its descendants
    };

    class ScopedContext
    {
    public:
        ScopedContext(MeshRaycast* meshRaycast, const RaycastContext* context) : m_meshRaycast(meshRaycast)
        {
            m_prevContext = meshRaycast->m_currentContext;
            meshRaycast->m_currentContext = (context == nullptr ? meshRaycast->m_defaultContext.get() : context);
        }

        ~ScopedContext()
        {
            m_meshRaycast->m_currentContext = m_prevContext;
        }

    private:
        MeshRaycast* m_meshRaycast = nullptr;
        const RaycastContext* m_prevContext = nullptr;
    };

    PxFoundation* m_foundation;
    physx::PxTolerancesScale m_defaultScale;
    physx::PxCookingParams m_defaultCookingParams{ m_defaultScale };

    carb::events::IEventStreamPtr m_raycastEventStream;

    PxConvexMesh* m_CylinderMeshX;
    PxConvexMesh* m_CylinderMeshY;
    PxConvexMesh* m_CylinderMeshZ;

    PxConvexMesh* m_ConeMeshX;
    PxConvexMesh* m_ConeMeshY;
    PxConvexMesh* m_ConeMeshZ;

    UsdStageWeakPtr m_stage;

    bool m_sceneBuilt = false;
    PxBVH* m_BVH = nullptr;
    std::vector<PxU32> m_freeBoundsIndices;

    BvhRefreshRate m_refreshRate = BvhRefreshRate::eSlow;
    std::chrono::high_resolution_clock::time_point m_lastBvhRefreshTime;

    // Maps from a SdfPath to ALL bounds indices it affects.
    // e.g. path "/Foo" will contain the index of itself and also the index of "/Foo/bar"
    // It is so that if "/Foo" is deleted, we can find all its descendants quickly and remove them too.
    std::unordered_map<SdfPath, MeshPathsData, SdfPath::Hash> m_meshPathBoundsIndices, m_incomingMeshPathBoundsIndices;
    std::unordered_map<PxU32, SdfPath> m_boundsIndexToMeshPath, m_incomingBoundsIndexToMeshPath;
#if ADD_NEW_BOUNDS_MT
    // carb_sdk_plugins\include\carb\PluginCoreUtils.h:
    // "The interface types need not be trivially constructed or destructed, but their constructors and destructors MUST
    // NOT use any Carbonite framework *functions." Both MutexWrapper and ConditionVariableWrapper acquires ITasking
    // interface in their constructor and destructor, thus they have to be created/released in startup/shutdown.
    std::unique_ptr<carb::tasking::MutexWrapper> m_incomingMutex;
#endif

    std::unordered_map<SdfPath, GeomInfo, SdfPath::Hash> m_geomMap;
    std::unordered_map<SdfPath, std::vector<size_t>, SdfPath::Hash> m_trimeshTriIdxToUsdFaceIdxMap;
    std::unordered_map<carb::extras::hash128_t, PxTriangleMesh*> m_cookedTriMeshes;

    carb::tasking::ITasking* m_tasking = nullptr;
    carb::tasking::CounterWrapper* m_overlapJobsCounter = nullptr;

    carb::settings::ThreadSafeLocalCache<int32_t> m_numPrimsPerLeaf;
    carb::settings::ThreadSafeLocalCache<int64_t> m_preReservedSize;
    carb::settings::ThreadSafeLocalCache<bool> m_buildBvhOnFirstRequired;

    carb::eventdispatcher::ObserverGuard m_updateEvtSub;

    std::unique_ptr<RaycastContext> m_defaultContext;
    const RaycastContext* m_currentContext = nullptr;

    PxVec3 m_rayOrigin;
    PxVec3 m_rayDir;

    PxSphereGeometry m_shpere;
    PxTransform m_transform;

    HitResult m_hitResult;
    BoundResult m_boundResult;
    std::vector<size_t> m_overlapIndices;

    std::vector<std::pair<PxU32, GfMatrix4d>> m_overlapBoundsIndices;
#if REPORT_OVERLAP_HIT_MT
    std::unique_ptr<carb::tasking::MutexWrapper> m_overlapVerticesMutex; // see comment above from PluginCoreUtils for
                                                                         // why it's in an std::unique_ptr
#endif
    std::unordered_map<PxU32, std::vector<size_t>> m_overlapVertices;
    std::unordered_map<PxU32, std::vector<size_t>> m_overlapFaces;
    std::atomic<size_t> m_totalOverlapVerticesCount{ 0 };
    std::atomic<size_t> m_totalOverlapFacesCount{ 0 };

    CastMode m_castMode = CastMode::eNone;

    omni::usd::UsdContext* m_usdContext;
    carb::events::ISubscriptionPtr m_stageEvtSub;
    std::unique_ptr<UsdStageNoticeListener> m_stageChangeListener;

    void onUpdate(bool force)
    {
        if (m_stageChangeListener)
        {
            m_stageChangeListener->onUpdate(force);
        }
    }

    void buildScene(BvhRefreshRate refreshRate)
    {
        CARB_PROFILE_FUNCTION(1);
        auto stage = m_usdContext->getStage();
        if (!stage)
        {
            return;
        }

        m_sceneBuilt = true;
        m_stage = stage;
        m_stageChangeListener = std::make_unique<UsdStageNoticeListener>(this, stage);
        m_refreshRate = refreshRate;

        m_meshPathBoundsIndices.clear();
        m_boundsIndexToMeshPath.clear();
        m_freeBoundsIndices.clear();

        SdfPathUSet pathsToAdd = getBuildableDescendantPaths(SdfPath::AbsoluteRootPath());
        SdfPathUSet pathsToRemove;

        requestRebuildBVH(pathsToAdd, pathsToRemove);
    }

    void onStageOpened()
    {
        OMNI_ACTIVITY_SCOPE("Stage|Opened|Paint Tools Mesh Ray Cast");

        if (!m_buildBvhOnFirstRequired)
        {
            buildScene(BvhRefreshRate::eSlow);
        }
    }

    void onStageClosing()
    {
        m_stage = nullptr;
        m_stageChangeListener.reset();
        if (m_BVH)
        {
            m_BVH->release();
            m_BVH = nullptr;
        }
        m_sceneBuilt = false;

        m_meshPathBoundsIndices.clear();
        m_boundsIndexToMeshPath.clear();
        releaseGeomInfo();

        for (auto& entry : m_cookedTriMeshes)
        {
            entry.second->release();
        }
        m_cookedTriMeshes.clear();
    }

    GfRange3d computeWorldBoundingBox(const UsdPrim& prim, bool useLocalCache = false) const
    {
        // useLocalCache if in multi-threaded mode.
        // computePrimWorldBoundingBox is not thread safe and take a lock slows things down when a lot of meshes wants
        // their bbox.
        if (useLocalCache || prim.IsA<UsdGeomBasisCurves>())
        {
            // note that if the object is invisible due to its display purpose, it may not be included in the bounding
            // box
            // this might be an issue for things like curve that can be visualized by systems other than hydra (e.g.
            // omni.scenevisualization), so handle it with special bboxCache that considers all purpose.

            PXR_NS::UsdGeomBBoxCache bboxCache(
                PXR_NS::UsdTimeCode::Default(),
                PXR_NS::TfTokenVector{ PXR_NS::UsdGeomTokens->default_, PXR_NS::UsdGeomTokens->proxy,
                                       PXR_NS::UsdGeomTokens->guide, PXR_NS::UsdGeomTokens->render },
                true);

            return bboxCache.ComputeWorldBound(prim).ComputeAlignedRange();
        }
        else
        {
            return m_usdContext->computePrimWorldBoundingBox(prim);
        }
    }

    GfMatrix4d computeWorldTransform(const UsdPrim& prim) const
    {
        return m_usdContext->computePrimWorldTransform(prim);
    }

    void rebuildBVH(std::vector<PxBounds3>& pxBoundsToBuild)
    {
        CARB_LOG_INFO("Start rebuild BVH");
        CARB_PROFILE_ZONE(1, "Rebuild BVH");

        PxBVHDesc desc;
        desc.bounds.count = PxU32(pxBoundsToBuild.size());
        desc.bounds.data = pxBoundsToBuild.data();
        desc.bounds.stride = sizeof(PxBounds3);
        desc.buildStrategy = PxBVHBuildStrategy::eFAST;
        desc.numPrimsPerLeaf = m_numPrimsPerLeaf.get();

        m_BVH = PxCreateBVH(desc);

        m_boundsIndexToMeshPath = std::move(m_incomingBoundsIndexToMeshPath);
        m_meshPathBoundsIndices = std::move(m_incomingMeshPathBoundsIndices);

        m_raycastEventStream->dispatch(
            (carb::events::EventType)RaycastEventType::eBvhRebuilt, carb::events::kGlobalSenderId);

        CARB_LOG_INFO("Finish rebuild BVH");
    }

    void addIncomingBound(const UsdPrim& prim,
                          std::vector<PxBounds3>& pxBounds,
                          const PxBounds3& pxBound,
                          const PxU32* addIndex = nullptr)
    {
        CARB_PROFILE_FUNCTION(1);

        PxU32 boundIndex;
        if (addIndex)
        {
            boundIndex = *addIndex;
            pxBounds[boundIndex] = pxBound;
        }
        else
        {
            pxBounds.push_back(pxBound);
            boundIndex = PxU32(pxBounds.size() - 1);
        }

        SdfPath primPath = prim.GetPath();
        auto prefixes = primPath.GetPrefixes();

#if ADD_NEW_BOUNDS_MT
        std::lock_guard<carb::tasking::MutexWrapper> lock(*m_incomingMutex);
#endif

        for (const auto& prefix : prefixes)
        {
            // TODO how much size to reserve on meshPathBoundsIndices?
            auto& indicesData = m_incomingMeshPathBoundsIndices[prefix];
            indicesData.selfAndDescendantsIndices.insert(boundIndex);
            if (prefix == primPath)
            {
                indicesData.selfIndex = boundIndex;
            }
        }
        m_incomingBoundsIndexToMeshPath[boundIndex] = primPath;
    };

    void overrideCurrBound(const UsdPrim& prim, const PxBounds3& pxBound, PxU32 boundIndex)
    {
        CARB_PROFILE_FUNCTION(1);

        PxU32 nbBounds = m_BVH->getNbBounds();
        if (boundIndex < nbBounds)
        {
            auto ret = m_BVH->updateBounds(boundIndex, pxBound);
            if (ret)
                m_stageChangeListener->updateGeomInfo(prim);
        }
        else
        {
            CARB_LOG_WARN("Override index %u is >= bounds size %u", boundIndex, nbBounds);
        }

        SdfPath primPath = prim.GetPath();
        auto prefixes = primPath.GetPrefixes();

        for (const auto& prefix : prefixes)
        {
            // TODO how much size to reserve on meshPathBoundsIndices?
            auto& indicesData = m_meshPathBoundsIndices[prefix];
            indicesData.selfAndDescendantsIndices.insert(boundIndex);
            if (prefix == primPath)
            {
                indicesData.selfIndex = boundIndex;
            }
        }
        m_boundsIndexToMeshPath[boundIndex] = primPath;
    }

    void buildBounds(const UsdPrim& prim,
                     std::vector<PxBounds3>* pxBounds = nullptr,
                     const PxU32* overrideIndex = nullptr,
                     const PxU32* addIndex = nullptr)
    {
        CARB_PROFILE_FUNCTION(1);

        if (overrideIndex && addIndex)
        {
            CARB_LOG_ERROR("Cannot override and add index at the same time!");
            return;
        }

        // if addIndex is not nullptr, this function is called from carb::tasking MT, need to use a local bboxcache
        auto bbox = computeWorldBoundingBox(prim, addIndex != nullptr);
        auto _min = bbox.GetMin();
        auto _max = bbox.GetMax();

        PxBounds3 pxBound(PxVec3((float)_min[0], (float)_min[1], float(_min[2])),
                          PxVec3(float(_max[0]), float(_max[1]), float(_max[2])));

        if (overrideIndex)
        {
            overrideCurrBound(prim, pxBound, *overrideIndex);
        }
        else
        {
            addIncomingBound(prim, *pxBounds, pxBound, addIndex);
        }
    };

    bool findOwnedBoundIndex(const SdfPath& path, PxU32& index) const
    {
        const auto entry = m_meshPathBoundsIndices.find(path);
        if (entry == m_meshPathBoundsIndices.end())
        {
            return false;
        }
        const auto owner = m_boundsIndexToMeshPath.find(entry->second.selfIndex);
        if (owner == m_boundsIndexToMeshPath.end() || owner->second != path)
        {
            return false;
        }
        index = entry->second.selfIndex;
        return true;
    }

    // It is caller's responsibility to make sure pathsToReadd and pathsToRemove is of supported type, and all
    // descendants are pre-populated with getBuildableDescendantPaths (Having only "/Foo" in pathsToReadd will not add
    // "/Foo/bar" ).
    void requestRebuildBVH(SdfPathUSet& pathsToReadd, SdfPathUSet& pathsToRemove)
    {
        CARB_LOG_INFO("Start refresh data for BVH");
        CARB_PROFILE_FUNCTION(1);

        std::unordered_set<PxU32> oldIndicesToRemove;
        for (const auto& path : pathsToRemove)
        {
            const auto& entry = m_meshPathBoundsIndices.find(path);
            if (entry != m_meshPathBoundsIndices.end())
            {
                const auto& descendantsIndices = entry->second.selfAndDescendantsIndices;
                // If we want to remove this path, we need to remove all its descendants as well
                oldIndicesToRemove.insert(descendantsIndices.begin(), descendantsIndices.end());
            }
        }

        size_t newPathToAddCount = 0;
        for (const auto& path : pathsToReadd)
        {
            PxU32 index;
            if (!findOwnedBoundIndex(path, index) || oldIndicesToRemove.count(index))
            {
                newPathToAddCount++;
            }
        }

        if (m_BVH && newPathToAddCount <= m_freeBoundsIndices.size() + oldIndicesToRemove.size())
        {
            // If we have enough room in the BVH, try to do refit instead of rebuild

            // Remove old paths and their indices
            for (const auto index : oldIndicesToRemove)
            {
                auto entry = m_boundsIndexToMeshPath.find(index);
                if (entry != m_boundsIndexToMeshPath.end())
                {
                    const SdfPath& path = entry->second;

                    // The path is removed, clear the geomMap
                    m_geomMap.erase(path);

                    m_meshPathBoundsIndices.erase(path);

                    // Remove the index from all prefixes in m_meshPathBoundsIndices as well
                    const auto prefixes = path.GetPrefixes();
                    for (const SdfPath& prefix : prefixes)
                    {
                        auto prefixEntry = m_meshPathBoundsIndices.find(prefix);
                        if (prefixEntry != m_meshPathBoundsIndices.end())
                        {
                            prefixEntry->second.selfAndDescendantsIndices.erase(index);

                            // If the indices map is empty, remove the entire entry
                            if (prefixEntry->second.selfAndDescendantsIndices.empty())
                            {
                                m_meshPathBoundsIndices.erase(prefixEntry);
                            }
                        }
                    }

                    // erase itself
                    m_boundsIndexToMeshPath.erase(entry);
                }
            }

            // Set removed bounds to empty, put the index into free list
            for (const auto index : oldIndicesToRemove)
            {
                m_BVH->updateBounds(index, PxBounds3::empty());

                // Now the slot is available, put the index into free list
                m_freeBoundsIndices.push_back(index);
                CARB_LOG_INFO("Bound index %d is freed", index);
            }

            for (const auto& path : pathsToReadd)
            {
                auto prim = m_stage->GetPrimAtPath(path);
                PxU32 boundIndex;
                // Prefix entries may describe only descendants. Reuse a bound only
                // when its reverse mapping identifies this path as the owner.
                if (!findOwnedBoundIndex(path, boundIndex))
                {
                    if (!m_freeBoundsIndices.empty())
                    {
                        // If the path does not exist before, get a new index from free list
                        boundIndex = m_freeBoundsIndices.back();
                        m_freeBoundsIndices.pop_back();
                    }
                    else
                    {
                        CARB_LOG_ERROR("Unable to allocate a free slot in existing BVH");
                        break;
                    }
                }
                buildBounds(prim, nullptr, &boundIndex);
                CARB_LOG_INFO("Bound index %d is reused", boundIndex);
            }

            // No need to rebuild BVH, partialRefit on main thread
            m_BVH->partialRefit();
            CARB_LOG_INFO("End refresh data for BVH early. Only refit is needed");
        }
        else
        {
            // There wasn't already a BVH or the BVH is not big enough to refit all data, do a rebuild
            CARB_PROFILE_ZONE(1, "check old bounds");

            std::vector<PxBounds3> pxBounds;
            m_incomingBoundsIndexToMeshPath.clear();
            m_incomingMeshPathBoundsIndices.clear();

            std::atomic<bool> changed{ false };

            PxU32 currBvhSize = 0;
            const PxBounds3* currBvhBounds = nullptr;
            if (m_BVH)
            {
                currBvhSize = m_BVH->getNbBounds();
                currBvhBounds = m_BVH->getBounds();
            }

            pxBounds.reserve(currBvhSize + pathsToReadd.size());
            m_incomingBoundsIndexToMeshPath.reserve(m_boundsIndexToMeshPath.size() + pathsToReadd.size());
            m_incomingMeshPathBoundsIndices.reserve(m_meshPathBoundsIndices.size() + pathsToReadd.size());

            for (PxU32 i = 0; i < currBvhSize; i++)
            {
                // This index is empty, don't copy to new bound
                if (currBvhBounds[i].isEmpty())
                {
                    continue;
                }

                auto meshPathEntry = m_boundsIndexToMeshPath.find(i);
                if (meshPathEntry == m_boundsIndexToMeshPath.end())
                {
                    CARB_LOG_WARN("Failed to find path for bound index");
                    continue;
                }

                const SdfPath& meshPath = meshPathEntry->second;

                // This index is marked for removal, don't copy it to new bound
                if (oldIndicesToRemove.find(i) != oldIndicesToRemove.end())
                {
                    changed.store(true, std::memory_order_relaxed);
                    // The path is removed, clear the geomMap
                    m_geomMap.erase(meshPath);
                    continue;
                }

                if (pathsToReadd.find(meshPath) != pathsToReadd.end())
                {
                    // The path existed and still exists, but it's resynced, re-fetch the data
                    auto prim = m_stage->GetPrimAtPath(meshPath);
                    if (prim.IsValid())
                    {
                        buildBounds(prim, &pxBounds);
                    }

                    changed.store(true, std::memory_order_relaxed);

                    // remove path from the set. remaining path will be added later
                    pathsToReadd.erase(meshPath);

                    // The path is resynced, clear the geomMap so the trimesh has a chance to rebuild
                    m_geomMap.erase(meshPath);
                }
                else
                {
                    // The path is neither re-added nor removed, copy the old data directly
                    auto prim = m_stage->GetPrimAtPath(meshPath);
                    if (prim.IsValid())
                    {
                        addIncomingBound(prim, pxBounds, currBvhBounds[i]);
                    }
                    else
                    {
                        changed.store(true, std::memory_order_relaxed);
                    }
                }
            }

            {
                CARB_PROFILE_ZONE(1, "add new bounds");

                // If we still have new paths remaining, collect data from them and add into bounds
#if ADD_NEW_BOUNDS_MT
                PxU32 nextIdx = (PxU32)pxBounds.size();
                pxBounds.resize(pxBounds.size() + pathsToReadd.size());

                std::vector<SdfPath> pathsVec(pathsToReadd.begin(), pathsToReadd.end());
                m_tasking->parallelFor<PxU32>(
                    nextIdx, (PxU32)pxBounds.size(), [this, &pathsVec, &pxBounds, &changed, offset = nextIdx](PxU32 i) {
                        auto path = pathsVec[i - offset];
                        const auto prim = m_stage->GetPrimAtPath(path);
                        if (prim.IsValid())
                        {
                            buildBounds(prim, &pxBounds, nullptr, &i);
                            changed.store(true, std::memory_order_relaxed);
                        }
                    });

#else
                for (const SdfPath& path : pathsToReadd)
                {
                    auto prim = m_stage->GetPrimAtPath(path);
                    if (prim.IsValid())
                    {
                        buildBounds(prim, &pxBounds);
                        changed.store(true, std::memory_order_relaxed);
                    }
                }
#endif
            }

            if (changed.load(std::memory_order_relaxed))
            {
                // we're about to rebuild BVH, m_freeBoundsIndices no longer valid
                m_freeBoundsIndices.clear();

                // reserve empty slots for later all.
                size_t boundsSize = pxBounds.size();
#if CARB_DEBUG
                // OM-46219: use PxBounds3::empty() cuase assert in debug mode
                size_t preReservedSize = 0;
#else
                size_t preReservedSize = m_preReservedSize.get();
#endif
                pxBounds.resize(boundsSize + preReservedSize, PxBounds3::empty());

                // generate a new free list
                m_freeBoundsIndices.reserve(preReservedSize);
                for (size_t i = boundsSize; i < boundsSize + preReservedSize; i++)
                {
                    m_freeBoundsIndices.push_back(PxU32(i));
                }

                rebuildBVH(pxBounds);
            }
            pxBounds.clear();
        }

        CARB_LOG_INFO("End refresh data for BVH");
    }

    SdfPathUSet getBuildableDescendantPaths(const SdfPath& primPath)
    {
        CARB_PROFILE_FUNCTION(1);

        SdfPathUSet ret;
        auto rootPrim = m_stage->GetPrimAtPath(primPath);
        if (rootPrim.IsValid())
        {
            UsdPrimRange range = UsdPrimRange(rootPrim, PXR_NS::UsdTraverseInstanceProxies(UsdPrimAllPrimsPredicate));
            for (auto it = range.begin(); it != range.end(); ++it)
            {
                auto prim = *it;
                auto imageable = UsdGeomImageable(prim);
                if (imageable)
                {
                    if (imageable.ComputeVisibility() == UsdGeomTokens->invisible)
                    {
                        it.PruneChildren();
                        continue;
                    }
                }

                if (prim.IsA<UsdGeomPointInstancer>())
                {
                    it.PruneChildren();
                    continue;
                }

                if (prim.IsA<UsdGeomCamera>())
                {
                    it.PruneChildren();
                    continue;
                }

                if (isSupportedPrimType(prim))
                {
                    ret.insert(prim.GetPath());
                }
            }
        }
        return ret;
    }

    PxTriangleMesh* cookTriMesh(UsdPrim& prim)
    {
        CARB_PROFILE_FUNCTION(1);

        PxTriangleMesh* triMesh = nullptr;
        if (prim.IsA<UsdGeomMesh>())
        {
            triMesh = cookTriMeshFromGeomMesh(prim);
        }
        return triMesh;
    }

    bool getPrimPhysxPos(const SdfPath& primPath, PxVec3& pos)
    {
        auto stage = m_usdContext->getStage();
        auto prim = stage->GetPrimAtPath(primPath);
        if (!prim.IsValid())
            return false;
        if (!prim.IsA<UsdGeomMesh>() && !prim.IsA<UsdGeomGprim>())
            return false;

        const GfMatrix4d localToWorld = computeWorldTransform(prim);

        pxr::GfVec3d translation;
        translation = localToWorld.ExtractTranslation();

        pos = PxVec3((float)translation[0], (float)translation[1], (float)translation[2]);
        return true;
    }

    bool getPhysxGeometry(const SdfPath& primPath, bool forceCooking, const GfMatrix4d* localToWorldCached = nullptr)
    {
        CARB_PROFILE_FUNCTION(1);

        auto stage = m_usdContext->getStage();
        auto prim = stage->GetPrimAtPath(primPath);
        if (!isSupportedPrimType(prim))
        {
            return false;
        }

        const GfMatrix4d localToWorld = localToWorldCached ? *localToWorldCached : computeWorldTransform(prim);

        pxr::GfVec3d translation;
        pxr::GfMatrix4d rotMat(1.0);
        pxr::GfVec3d doubleScale(1.0);
        pxr::GfMatrix4d scaleOrientMatUnused, perspMatUnused;
        localToWorld.Factor(&scaleOrientMatUnused, &doubleScale, &rotMat, &translation, &perspMatUnused);
        rotMat.Orthonormalize(false);
        pxr::GfQuatd quat = rotMat.ExtractRotationQuat();

        PxTransform pose;
        pose.p = PxVec3((float)translation[0], (float)translation[1], (float)translation[2]);
        pose.q = PxQuat((float)quat.GetImaginary()[0], (float)quat.GetImaginary()[1], (float)quat.GetImaginary()[2],
                        (float)quat.GetReal());

        PxVec3 pxScale = PxVec3((float)doubleScale[0], (float)doubleScale[1], (float)doubleScale[2]);

        GeomInfo geomInfo;
        geomInfo.pose = pose;

        auto it = m_geomMap.find(primPath);
        bool exist = it != m_geomMap.end();
        if (!exist)
        {
            if (prim.IsA<UsdGeomMesh>())
            {
                PxTriangleMesh* triMeshes = cookTriMesh(prim);
                if (triMeshes == nullptr)
                    return false;

                geomInfo.geomHolder.storeAny(PxTriangleMeshGeometry(triMeshes, PxMeshScale(pxScale)));
            }
            else if (prim.IsA<UsdGeomCube>())
            {
                GfVec3f halfExtents;

                pxr::UsdGeomXformable xform(prim);
                const pxr::GfTransform tr(xform.ComputeLocalToWorldTransform(UsdTimeCode()));
                const pxr::GfVec3d sc = tr.GetScale();
                halfExtents = GfVec3f(sc);

                UsdGeomCube shape(prim);
                double sizeAttr;
                shape.GetSizeAttr().Get(&sizeAttr);
                sizeAttr = abs(sizeAttr) * 0.5f; // convert cube edge length to half extend
                halfExtents *= (float)sizeAttr;

                geomInfo.geomHolder.storeAny(PxBoxGeometry(PxVec3(halfExtents[0], halfExtents[1], halfExtents[2])));
            }
            else if (prim.IsA<UsdGeomSphere>())
            {
                float radius = 1.0f;
                pxr::UsdGeomXformable xform(prim);
                const pxr::GfTransform tr(xform.ComputeLocalToWorldTransform(UsdTimeCode()));
                const pxr::GfVec3d sc = tr.GetScale();
                // as we dont support scale in physics and scale can be non uniform
                // we pick the largest scale value as the sphere radius base
                checkNonUniformScale(sc, primPath);
                radius = fmaxf(fmaxf(fabsf(float(sc[1])), fabsf(float(sc[0]))), fabsf(float(sc[2])));

                UsdGeomSphere shape(prim);
                double radiusAttr;
                shape.GetRadiusAttr().Get(&radiusAttr);
                radius *= (float)radiusAttr;

                geomInfo.geomHolder.storeAny(PxSphereGeometry(radius));
            }
            else if (prim.IsA<UsdGeomCylinder>())
            {
                float radius = 1.0f;
                float halfHeight = 1.0f;
                Axis::Enum axis = Axis::eY;

                pxr::UsdGeomXformable xform(prim);

                // Get shape parameters
                {
                    UsdGeomCylinder shape(prim);
                    double radiusAttr;
                    shape.GetRadiusAttr().Get(&radiusAttr);
                    double heightAttr;
                    shape.GetHeightAttr().Get(&heightAttr);
                    radius = (float)radiusAttr;
                    halfHeight = (float)heightAttr * 0.5f;
                }

                {
                    // scale the radius and height based on the scale
                    const pxr::GfTransform tr(xform.ComputeLocalToWorldTransform(UsdTimeCode()));
                    const pxr::GfVec3d sc = tr.GetScale();

                    if (axis == Axis::eX)
                    {
                        halfHeight *= float(sc[0]);
                        if (abs(sc[2] - sc[1]) > tolerance)
                        {
                            CARB_LOG_WARN(
                                "Non-uniform scale may result in a non matching collision representation on prim: %s",
                                prim.GetPrimPath().GetText());
                        }
                        radius *= fmaxf(fabsf(float(sc[1])), fabsf(float(sc[2])));
                    }
                    else if (axis == Axis::eY)
                    {
                        halfHeight *= float(sc[1]);
                        if (abs(sc[2] - sc[0]) > tolerance)
                        {
                            CARB_LOG_WARN(
                                "Non-uniform scale may result in a non matching collision representation on prim: %s",
                                prim.GetPrimPath().GetText());
                        }
                        radius *= fmaxf(fabsf(float(sc[0])), fabsf(float(sc[2])));
                    }
                    else
                    {
                        halfHeight *= float(sc[2]);
                        if (abs(sc[0] - sc[1]) > tolerance)
                        {
                            CARB_LOG_WARN(
                                "Non-uniform scale may result in a non matching collision representation on prim: %s",
                                prim.GetPrimPath().GetText());
                        }
                        radius *= fmaxf(fabsf(float(sc[1])), fabsf(float(sc[0])));
                    }
                }

                PxConvexMesh* convexMesh = getCylinderConvexMesh(axis);
                if (convexMesh)
                {
                    const PxVec3 scale = getConeOrCylinderScale(halfHeight, radius, axis);
                    geomInfo.geomHolder.storeAny(PxConvexMeshGeometry(convexMesh, scale));
                }
            }
            else if (prim.IsA<UsdGeomCapsule>())
            {
                float radius = 1.0f;
                float halfHeight = 1.0f;
                auto axis = pxr::UsdGeomGetStageUpAxis(stage);

                pxr::UsdGeomXformable xform(prim);

                // Get shape parameters
                {
                    UsdGeomCapsule shape(prim);
                    double radiusAttr;
                    shape.GetRadiusAttr().Get(&radiusAttr);
                    double heightAttr;
                    shape.GetHeightAttr().Get(&heightAttr);
                    radius = (float)radiusAttr;
                    halfHeight = (float)heightAttr * 0.5f;
                }

                {
                    // scale the radius and height based on the given axis token
                    // For capsule, we also fix up axis according to what the up axis is defined in usd file
                    const pxr::GfTransform tr(xform.ComputeLocalToWorldTransform(UsdTimeCode()));
                    const pxr::GfVec3d sc = tr.GetScale();
                    checkNonUniformScale(sc, prim.GetPrimPath());

                    const float hRt2 = sqrt(2.0f) / 2.0f;
                    PxQuat fixupQ(PxIdentity);
                    if (axis == UsdGeomTokens->x)
                    {
                        halfHeight *= float(sc[0]);
                        radius *= fmaxf(fabsf(float(sc[1])), fabsf(float(sc[2])));
                    }
                    else if (axis == UsdGeomTokens->y)
                    {
                        halfHeight *= float(sc[1]);
                        radius *= fmaxf(fabsf(float(sc[0])), fabsf(float(sc[2])));

                        fixupQ = PxQuat(hRt2, -hRt2, 0.0f, 0.0f);
                    }
                    else
                    {
                        halfHeight *= float(sc[2]);
                        radius *= fmaxf(fabsf(float(sc[1])), fabsf(float(sc[0])));

                        fixupQ = PxQuat(hRt2, 0.0f, -hRt2, 0.0f);
                    }

                    geomInfo.pose *= PxTransform(fixupQ);
                }

                geomInfo.geomHolder.storeAny(PxCapsuleGeometry(radius, halfHeight));
            }
            else if (prim.IsA<UsdGeomCone>())
            {
                float radius = 1.0f;
                float halfHeight = 1.0f;
                Axis::Enum axis = Axis::eY;

                pxr::UsdGeomXformable xform(prim);

                UsdGeomCone shape(prim);

                // Get shape parameters
                {
                    UsdGeomCone shape(prim);
                    double radiusAttr;
                    shape.GetRadiusAttr().Get(&radiusAttr);
                    double heightAttr;
                    shape.GetHeightAttr().Get(&heightAttr);
                    radius = (float)radiusAttr;
                    halfHeight = (float)heightAttr * 0.5f;
                }

                {
                    // scale the radius and height based on the scale
                    const pxr::GfTransform tr(xform.ComputeLocalToWorldTransform(UsdTimeCode()));
                    const pxr::GfVec3d sc = tr.GetScale();
                    checkNonUniformScale(sc, prim.GetPrimPath());
                    if (axis == Axis::eX)
                    {
                        halfHeight *= float(sc[0]);
                        radius *= fmaxf(fabsf(float(sc[1])), fabsf(float(sc[2])));
                    }
                    else if (axis == Axis::eY)
                    {
                        halfHeight *= float(sc[1]);
                        radius *= fmaxf(fabsf(float(sc[0])), fabsf(float(sc[2])));
                    }
                    else
                    {
                        halfHeight *= float(sc[2]);
                        radius *= fmaxf(fabsf(float(sc[1])), fabsf(float(sc[0])));
                    }
                }

                PxConvexMesh* convexMesh = getConeConvexMesh(axis);
                if (convexMesh)
                {
                    const PxVec3 scale = getConeOrCylinderScale(halfHeight, radius, axis);
                    geomInfo.geomHolder.storeAny(PxConvexMeshGeometry(convexMesh, scale));
                }
            }
            else if (prim.IsA<UsdGeomBasisCurves>())
            {
                // tessellate the curve into mesh representation
                PxTriangleMesh* triMeshes = tessellateTriMeshFromGeomBasisCurves(prim);
                if (triMeshes == nullptr)
                    return false;

                geomInfo.geomHolder.storeAny(PxTriangleMeshGeometry(triMeshes, PxMeshScale(pxScale)));
            }
            else
            {
                CARB_LOG_WARN("Unable to create mesh representation for prim %s, raycast will skip it.",
                              prim.GetPath().GetText());
                return false;
            }

            m_geomMap[primPath] = geomInfo;
        }
        else
        {
            if (forceCooking && prim.IsA<UsdGeomMesh>())
            {
                m_geomMap.erase(it);

                PxTriangleMesh* triMeshes = cookTriMesh(prim);
                if (triMeshes == nullptr)
                    return false;

                geomInfo.geomHolder.storeAny(PxTriangleMeshGeometry(triMeshes, PxMeshScale(pxScale)));
                m_geomMap[primPath] = geomInfo;
            }
        }

        return true;
    }

    std::unique_ptr<omni::geometry::curves::SplineCurve> createSplineCurveFromBasisCurvesPrim(
        const UsdGeomBasisCurves& primCurve) const
    {
        using namespace omni::geometry::curves;

        using omni::math::linalg::safeCastToOmni;
        using omni::math::linalg::vec3f;

        TfToken basisToken;
        primCurve.GetBasisAttr().Get(&basisToken);
        TfToken wrapToken;
        primCurve.GetWrapAttr().Get(&wrapToken);
        TfToken typeToken;
        primCurve.GetTypeAttr().Get(&typeToken);

        eBasisCurveWrap wrapType = eBasisCurveWrap::Pinned;
        if (wrapToken == UsdGeomTokens->nonperiodic)
        {
            wrapType = eBasisCurveWrap::NonPeriodic;
        }
        else if (wrapToken == UsdGeomTokens->periodic)
        {
            wrapType = eBasisCurveWrap::Periodic;
        }
        else if (wrapToken == UsdGeomTokens->pinned)
        {
            wrapType = eBasisCurveWrap::Pinned;
        }

        eBasisCurveType curveType;
        if (basisToken == UsdGeomTokens->bspline)
        {
            curveType = eBasisCurveType::BSpline;
        }
        else if (basisToken == UsdGeomTokens->bezier)
        {
            curveType = eBasisCurveType::Bezier;
        }
        else if (basisToken == UsdGeomTokens->catmullRom)
        {
            curveType = eBasisCurveType::CatmullRom;
        }
        else
        {
            return nullptr;
        }

        return std::make_unique<SplineCurve>(wrapType, curveType);
    }

    PxTriangleMesh* tessellateTriMeshFromGeomBasisCurves(UsdPrim& prim)
    {
        using namespace omni::geometry::curves;

        using omni::math::linalg::safeCastToOmni;
        using omni::math::linalg::vec3f;

        UsdGeomBasisCurves primCurve = UsdGeomBasisCurves(prim);

        VtArray<pxr::GfVec3f> pointsUSD;
        if (!primCurve.GetPointsAttr().Get(&pointsUSD))
        {
            return nullptr;
        }

        auto curve = createSplineCurveFromBasisCurvesPrim(primCurve);

        std::vector<vec3f> points(safeCastToOmni(pointsUSD.data()), safeCastToOmni(pointsUSD.data() + pointsUSD.size()));

        TfToken typeToken;
        primCurve.GetTypeAttr().Get(&typeToken);

        VtFloatArray widthsUsd;
        primCurve.GetWidthsAttr().Get(&widthsUsd);
        std::vector<float> widths(safeCastToOmni(widthsUsd.data()), safeCastToOmni(widthsUsd.data() + widthsUsd.size()));

        TfToken widthsInterpolation = primCurve.GetWidthsInterpolation();

        VtIntArray curveVertexCounts;
        if (!primCurve.GetCurveVertexCountsAttr().Get(&curveVertexCounts))
        {
            curveVertexCounts.push_back((int)points.size());
        }

        VtArray<vec3f> meshPoints;
        std::vector<uint32_t> triIndices;

        auto generateMeshForSegments = [&meshPoints, &triIndices](
                                           const std::vector<vec3f>& points, const std::vector<float>& widths) {
            if (points.size() < 2)
            {
                return;
            }

            for (size_t i = 0; i < points.size() - 1; i++)
            {
                const vec3f& p0 = points[i];
                const vec3f& p1 = points[i + 1];

                vec3f tangent = (p1 - p0).GetNormalized();
                vec3f normal = vec3f::YAxis() ^ tangent;
                if (normal.GetLengthSq() < 1e-8)
                {
                    normal = vec3f::XAxis() ^ tangent;
                }
                normal.Normalize();
                vec3f binormal = (tangent ^ normal).GetNormalized();

                float halfWidth = 0.5f; // fallback value
                if (i < widths.size())
                {
                    halfWidth = widths[i] * 0.5f;
                }

                uint32_t baseIndex;
                if (i == 0)
                {
                    baseIndex = (uint32_t)meshPoints.size();
                    meshPoints.push_back(p0 + normal * halfWidth + binormal * halfWidth);
                    meshPoints.push_back(p0 + normal * halfWidth - binormal * halfWidth);
                    meshPoints.push_back(p0 - normal * halfWidth - binormal * halfWidth);
                    meshPoints.push_back(p0 - normal * halfWidth + binormal * halfWidth);
                }
                else
                {
                    baseIndex = (uint32_t)meshPoints.size() - 4;
                }

                halfWidth = 0.5f; // reset fallback value
                if (i + 1 < widths.size())
                {
                    halfWidth = widths[i + 1] * 0.5f;
                }

                meshPoints.push_back(p1 + normal * halfWidth + binormal * halfWidth);
                meshPoints.push_back(p1 + normal * halfWidth - binormal * halfWidth);
                meshPoints.push_back(p1 - normal * halfWidth - binormal * halfWidth);
                meshPoints.push_back(p1 - normal * halfWidth + binormal * halfWidth);

                // fill index buffer
                const auto& b = baseIndex;
                triIndices.insert(
                    triIndices.end(),
                    // clang-format off
                    {
                        b + 1, b + 0, b + 4,
                        b + 1, b + 4, b + 5,
                        b + 2, b + 1, b + 5,
                        b + 2, b + 5, b + 6,
                        b + 3, b + 2, b + 6,
                        b + 3, b + 6, b + 7,
                        b + 0, b + 3, b + 7,
                        b + 0, b + 7, b + 4,
                    } // clang-format on
                );
            }
        };

        const size_t kCurveStepsPerSegment = 16;

        size_t tessPointsCount = 0;
        size_t tessIndicesCount = 0;
        for (const auto& vertexCount : curveVertexCounts)
        {
            if (vertexCount <= 1)
            {
                continue;
            }

            if (typeToken == pxr::UsdGeomTokens->linear)
            {
                tessPointsCount += vertexCount * 4;
                tessIndicesCount += 24 * (vertexCount - 1);
            }
            else
            {
                size_t tessCount = curve->getTessellationPointCount(vertexCount, kCurveStepsPerSegment);
                tessPointsCount += tessCount * 4;
                tessIndicesCount += 24 * (tessCount - 1);
            }
        }

        meshPoints.reserve(tessPointsCount);
        triIndices.reserve(tessIndicesCount);

        size_t startIdx = 0;
        size_t widthsStartIndex = 0;
        for (size_t i = 0; i < curveVertexCounts.size(); i++)
        {
            const size_t count = curveVertexCounts[i];
            std::vector<vec3f> controlPoints(points.begin() + startIdx, points.begin() + startIdx + count);
            std::vector<float> interpolatedWidths;

            if (typeToken == pxr::UsdGeomTokens->linear)
            {
                if (!widths.empty())
                {
                    if (widthsInterpolation == UsdGeomTokens->constant)
                    {
                        interpolatedWidths.resize(controlPoints.size(), widths[0]);
                    }
                    else if (widthsInterpolation == UsdGeomTokens->varying)
                    {
                        interpolatedWidths.assign(
                            widths.begin() + widthsStartIndex, widths.begin() + widthsStartIndex + count);
                    }
                    else
                    {
                        CARB_LOG_WARN("Unsupported widths interpolation mode %s for %s, fallback to default width",
                                      widthsInterpolation.GetText(), primCurve.GetPath().GetText());
                    }
                }

                generateMeshForSegments(controlPoints, interpolatedWidths);

                widthsStartIndex += curveVertexCounts[i];
            }
            else
            {
                std::vector<vec3f> tessellatedPositions;
                curve->tessellate(
                    controlPoints.data(), controlPoints.size(), tessellatedPositions, kCurveStepsPerSegment);

                std::vector<float> interpolatedWidths;
                if (!widths.empty())
                {
                    if (widthsInterpolation == UsdGeomTokens->constant)
                    {
                        interpolatedWidths.resize(tessellatedPositions.size(), widths[0]);
                    }
                    else if (widthsInterpolation == UsdGeomTokens->varying)
                    {
                        size_t widthsCount = (curveVertexCounts[i] + 2) / 3;
                        interpolatedWidths.reserve(tessellatedPositions.size());
                        for (size_t wi = widthsStartIndex;
                             wi < widthsStartIndex + widthsCount - 1 && wi + 1 < widths.size(); wi++)
                        {
                            float w0 = widths[wi];
                            float w1 = widths[wi + 1];
                            float step = (w1 - w0) / kCurveStepsPerSegment;

                            if (wi == widthsStartIndex)
                            {
                                interpolatedWidths.push_back(w0);
                            }

                            for (size_t lerpi = 1; lerpi < kCurveStepsPerSegment; lerpi++)
                            {
                                interpolatedWidths.push_back(w0 + step * lerpi);
                            }

                            interpolatedWidths.push_back(w1);
                        }

                        if (interpolatedWidths.size() != tessellatedPositions.size())
                        {
                            CARB_LOG_WARN(
                                "Interpolated widths size is not equal to tessellated positions size for %s, fallback to default width",
                                primCurve.GetPath().GetText());
                        }

                        widthsStartIndex += widthsCount;
                    }
                    else if (widthsInterpolation == UsdGeomTokens->vertex)
                    {
                        std::vector<float> widthsThis(
                            widths.begin() + widthsStartIndex, widths.begin() + widthsStartIndex + count);
                        curve->tessellate(
                            widthsThis.data(), widthsThis.size(), interpolatedWidths, kCurveStepsPerSegment);

                        widthsStartIndex += curveVertexCounts[i];
                    }
                    else
                    {
                        CARB_LOG_WARN("Unsupported widths interpolation mode %s for %s, fallback to default width",
                                      widthsInterpolation.GetText(), primCurve.GetPath().GetText());
                    }
                }

                generateMeshForSegments(tessellatedPositions, interpolatedWidths);
            }

            startIdx += curveVertexCounts[i];
        }

        physx::PxTriangleMeshDesc meshDesc;
        meshDesc.points.count = PxU32(meshPoints.size());
        meshDesc.points.stride = sizeof(float) * 3;
        meshDesc.points.data = meshPoints.data();
        meshDesc.triangles.count = (PxU32)(triIndices.size() / 3);
        meshDesc.triangles.stride = sizeof(uint32_t) * 3;
        meshDesc.triangles.data = triIndices.data();

        return createOrFetchTriMesh(meshDesc);
    }

    PxTriangleMesh* createOrFetchTriMesh(const physx::PxTriangleMeshDesc& meshDesc)
    {
        // Try to find identical mesh that is already cooked to avoid slow createTriangleMesh
        auto combinedHash = carb::extras::fnv128hash(
            reinterpret_cast<const uint8_t*>(meshDesc.points.data), meshDesc.points.stride * meshDesc.points.count);
        combinedHash = carb::extras::fnv128hash(reinterpret_cast<const uint8_t*>(meshDesc.triangles.data),
                                                meshDesc.triangles.stride * meshDesc.triangles.count, combinedHash);

        combinedHash = carb::extras::fnv128hash(
            reinterpret_cast<const uint8_t*>(&meshDesc.flags), sizeof(meshDesc.flags), combinedHash);

        PxTriangleMesh* triMesh = nullptr;
        auto cookedMeshEntry = m_cookedTriMeshes.find(combinedHash);
        if (cookedMeshEntry == m_cookedTriMeshes.end())
        {
            CARB_PROFILE_BEGIN(1, "createTriangleMesh");
            triMesh = PxCreateTriangleMesh(m_defaultCookingParams, meshDesc);
            CARB_PROFILE_END(1);

            // TODO hash can have collision on different set of data. Save the points and triangles for a equal compare
            // after a hash compare?
            if (triMesh)
            {
                m_cookedTriMeshes[combinedHash] = triMesh;
            }
            else
            {
                CARB_LOG_WARN("Failed to cook tri mesh");
            }
        }
        else
        {
            // reuse identical cooked mesh
            triMesh = cookedMeshEntry->second;
        }

        return triMesh;
    }

    PxTriangleMesh* cookTriMeshFromGeomMesh(UsdPrim& prim)
    {
        CARB_PROFILE_FUNCTION(1);

        VtArray<GfVec3f> meshPoints;
        VtArray<int> faceCounts;
        VtArray<int> faceIndices;

        prim.GetAttribute(UsdGeomTokens->points).Get(&meshPoints);
        prim.GetAttribute(UsdGeomTokens->faceVertexCounts).Get(&faceCounts);
        prim.GetAttribute(UsdGeomTokens->faceVertexIndices).Get(&faceIndices);

        if (meshPoints.empty() || faceCounts.empty() || faceIndices.empty())
        {
            // invalid mesh, early out
            return nullptr;
        }

        // Mesh to triMesh
        PxU32 triCount = 0;
        for (size_t i = 0; i < faceCounts.size(); ++i)
        {
            if (faceCounts[i] <= 2)
            {
                CARB_LOG_WARN("Skip face with vertex count %d", faceCounts[i]);
                continue;
            }

            triCount += faceCounts[i] - 2; // number of triangles in a face
        }
        PxU32 triIndicesCount = 3 * triCount;

        std::vector<uint32_t> triIndices;
        triIndices.resize(triIndicesCount);

        size_t pxTriIdxOffset = 0;
        size_t usdFaceIdxOffset = 0;
        std::vector<size_t> trimeshTriIdxToUsdFaceIdx;
        trimeshTriIdxToUsdFaceIdx.reserve(triCount);
        for (size_t faceIdx = 0; faceIdx < faceCounts.size(); ++faceIdx)
        {
            size_t faceVertexCount = faceCounts[faceIdx];
            if (faceVertexCount <= 2)
            {
                continue;
            }

            for (size_t faceVertIdx = 0; faceVertIdx < faceVertexCount - 2; ++faceVertIdx)
            {
                triIndices[pxTriIdxOffset] = faceIndices[usdFaceIdxOffset];
                triIndices[pxTriIdxOffset + 1] = faceIndices[usdFaceIdxOffset + faceVertIdx + 1];
                triIndices[pxTriIdxOffset + 2] = faceIndices[usdFaceIdxOffset + faceVertIdx + 2];
                trimeshTriIdxToUsdFaceIdx.push_back(faceIdx);
                pxTriIdxOffset += 3;
            }
            usdFaceIdxOffset += faceVertexCount;
        }

        physx::PxTriangleMeshDesc meshDesc;
        meshDesc.points.count = PxU32(meshPoints.size());
        meshDesc.points.stride = sizeof(float) * 3;
        meshDesc.points.data = meshPoints.data();
        meshDesc.triangles.count = triCount;
        meshDesc.triangles.stride = sizeof(uint32_t) * 3;
        meshDesc.triangles.data = triIndices.data();

        TfToken value;
        UsdGeomGprim(prim).GetOrientationAttr().Get(&value);
        if (value == TfToken("leftHanded"))
        {
            meshDesc.flags |= PxMeshFlag::eFLIPNORMALS;
        }

        m_trimeshTriIdxToUsdFaceIdxMap[prim.GetPrimPath()] = std::move(trimeshTriIdxToUsdFaceIdx);

        return createOrFetchTriMesh(meshDesc);
    }

    template <typename T>
    bool SafeGetAttributeP(T* out, UsdAttribute const& attribute)
    {
        if (attribute.HasValue())
        {
            attribute.Get(out);
            return true;
        }
        return false;
    }

    PxVec3 randomPointOnTriangle(const PxVec3& a, const PxVec3& b, const PxVec3& c)
    {
        float x = float(rand()) / RAND_MAX;
        float y = float(rand()) / RAND_MAX;

        if (x + y > 1)
        {
            x = 1 - x;
            y = 1 - y;
        }

        float z = 1 - x - y;
        return a * x + b * y + c * z;
    }

    void sampleOnTriangle(const PxVec3& a,
                          const PxVec3& b,
                          const PxVec3& c,
                          const PxTransform& pose,
                          const float density,
                          std::vector<carb::Float3>& positions,
                          std::vector<carb::Float3>& normals)
    {
        PxVec3 n = (b - a).cross(c - a);
        float mag = n.normalize();

        auto px_normal = pose.rotate(n);
        carb::Float3 normal = { px_normal.x, px_normal.y, px_normal.z };
        float s = 0.5f * mag * density;
        float num = floor(s);

        // decimal
        float r = float(rand()) / RAND_MAX;
        if (r < s - num)
            num += 1;

        for (int j = 0; j < num; j++)
        {
            auto p = pose.transform(randomPointOnTriangle(a, b, c));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }
    }

    template <typename T>
    void samplingOnTriMesh(const PxTriangleMesh* triMesh,
                           const PxTransform& pose,
                           const PxVec3& scale,
                           const float density,
                           std::vector<carb::Float3>& positions,
                           std::vector<carb::Float3>& normals)
    {
        auto indices = (T*)triMesh->getTriangles();
        auto vertices = triMesh->getVertices();

        for (uint32_t i = 0; i < triMesh->getNbTriangles(); i++)
        {
            PxVec3 a = vertices[indices[i * 3]].multiply(scale);
            PxVec3 b = vertices[indices[i * 3 + 1]].multiply(scale);
            PxVec3 c = vertices[indices[i * 3 + 2]].multiply(scale);

            sampleOnTriangle(a, b, c, pose, density, positions, normals);
        }
    }

    void samplingOnConvexMesh(const PxConvexMesh* convexMesh,
                              const PxTransform& pose,
                              const PxVec3& scale,
                              const float density,
                              std::vector<carb::Float3>& positions,
                              std::vector<carb::Float3>& normals)
    {
        auto indices = convexMesh->getIndexBuffer();
        auto vertices = convexMesh->getVertices();

        for (uint32_t i = 0; i < convexMesh->getNbPolygons(); i++)
        {
            PxHullPolygon polygon;
            convexMesh->getPolygonData(i, polygon);

            for (uint16_t j = 0; j < polygon.mNbVerts - 2; j++)
            {
                PxVec3 a = vertices[indices[polygon.mIndexBase]].multiply(scale);
                PxVec3 b = vertices[indices[polygon.mIndexBase + j + 1]].multiply(scale);
                PxVec3 c = vertices[indices[polygon.mIndexBase + j + 2]].multiply(scale);

                sampleOnTriangle(a, b, c, pose, density, positions, normals);
            }
        }
    }

    void samplingOnSphere(const PxTransform& pose,
                          const float radius,
                          const float density,
                          std::vector<carb::Float3>& positions,
                          std::vector<carb::Float3>& normals)
    {
        float s = 4.0f * PxPi * radius * radius;
        auto num = floor(density * s);

        for (int j = 0; j < num; j++)
        {
            auto z = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto r = PxSqrt(1.0f - z * z);
            float theta = 2.0f * PxPi * float(rand()) / RAND_MAX;
            auto x = r * PxCos(theta);
            auto y = r * PxSin(theta);

            auto p = pose.p + (PxVec3(x, y, z) * radius);
            carb::Float3 pos = { p.x, p.y, p.z };
            carb::Float3 normal = { x, y, z };
            positions.push_back(pos);
            normals.push_back(normal);
        }
    }

    void samplingOnBox(const PxTransform& pose,
                       const PxVec3& halfExtents,
                       const float density,
                       std::vector<carb::Float3>& positions,
                       std::vector<carb::Float3>& normals)
    {
        auto s = 4.0f * halfExtents.x * halfExtents.y;
        auto num = floor(density * s);
        auto n = pose.rotate(PxVec3(0, 0, 1.0f));
        carb::Float3 normal = { n.x, n.y, n.z };

        for (int j = 0; j < num; j++)
        {
            auto x = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto y = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto p = pose.transform(PxVec3(x, y, 1.0f).multiply(halfExtents));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }
        n = pose.rotate(PxVec3(0, 0, -1.0f));
        normal = { n.x, n.y, n.z };
        for (int j = 0; j < num; j++)
        {
            auto x = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto y = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto p = pose.transform(PxVec3(x, y, -1.0f).multiply(halfExtents));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }

        s = 4.0f * halfExtents.x * halfExtents.z;
        num = floor(density * s);
        n = pose.rotate(PxVec3(0, 1.0f, 0));
        normal = { n.x, n.y, n.z };
        for (int j = 0; j < num; j++)
        {
            auto x = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto z = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto p = pose.transform(PxVec3(x, 1.0f, z).multiply(halfExtents));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }
        n = pose.rotate(PxVec3(0, -1.0f, 0));
        normal = { n.x, n.y, n.z };
        for (int j = 0; j < num; j++)
        {
            auto x = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto z = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto p = pose.transform(PxVec3(x, -1.0f, z).multiply(halfExtents));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }

        s = 4.0f * halfExtents.y * halfExtents.z;
        num = floor(density * s);
        n = pose.rotate(PxVec3(1.0f, 0, 0));
        normal = { n.x, n.y, n.z };
        for (int j = 0; j < num; j++)
        {
            auto y = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto z = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto p = pose.transform(PxVec3(1.0f, y, z).multiply(halfExtents));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }

        n = pose.rotate(PxVec3(-1.0f, 0, 0));
        normal = { n.x, n.y, n.z };
        for (int j = 0; j < num; j++)
        {
            auto y = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto z = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto p = pose.transform(PxVec3(-1.0f, y, z).multiply(halfExtents));
            carb::Float3 pos = { p.x, p.y, p.z };
            positions.push_back(pos);
            normals.push_back(normal);
        }
    }

    void samplingOnCapsule(const PxTransform& pose,
                           const float half_height,
                           const float radius,
                           const float density,
                           std::vector<carb::Float3>& positions,
                           std::vector<carb::Float3>& normals)
    {
        // sphere
        float s = 4.0f * PxPi * radius * radius;
        auto num = floor(density * s);

        for (int j = 0; j < num; j++)
        {
            // physx is x up
            auto x = 2.0f * float(rand()) / RAND_MAX - 1.0f;
            auto r = PxSqrt(1.0f - x * x);
            float theta = 2.0f * PxPi * float(rand()) / RAND_MAX;
            auto y = r * PxCos(theta);
            auto z = r * PxSin(theta);

            auto p_local = PxVec3(x, y, z) * radius;
            if (p_local.x > 0)
                p_local.x += half_height;
            else
                p_local.x -= half_height;

            auto p = pose.transform(p_local);
            carb::Float3 pos = { p.x, p.y, p.z };

            auto n = pose.rotate(PxVec3(x, y, z));
            carb::Float3 normal = { n.x, n.y, n.z };

            positions.push_back(pos);
            normals.push_back(normal);
        }

        // cylinder surface
        s = 2.0f * PxPi * radius * 2.0f * half_height;
        num = floor(density * s);

        for (int j = 0; j < num; j++)
        {
            auto x = (2.0f * float(rand()) / RAND_MAX - 1.0f) * half_height;
            float theta = 2.0f * PxPi * float(rand()) / RAND_MAX;
            auto y = radius * PxCos(theta);
            auto z = radius * PxSin(theta);

            auto p = pose.transform(PxVec3(x, y, z));
            carb::Float3 pos = { p.x, p.y, p.z };

            auto n = pose.rotate(PxVec3(x, y, 0));
            carb::Float3 normal = { n.x, n.y, n.z };

            positions.push_back(pos);
            normals.push_back(normal);
        }
    }

    PxConvexMesh* createCylinderConvexMesh(const PxF32 width,
                                           const PxF32 radius,
                                           const PxU32 numCirclePoints,
                                           enum Axis::Enum axis)
    {
#define MAX_NUM_VERTS_IN_CIRCLE 64
        CARB_ASSERT(numCirclePoints <= MAX_NUM_VERTS_IN_CIRCLE);
        PxVec3 verts[2 * MAX_NUM_VERTS_IN_CIRCLE];
        PxU32 numVerts = 2 * numCirclePoints;
        const PxF32 dtheta = 2 * PxPi / (1.0f * numCirclePoints);

        PxU32 axisIndex;
        PxU32 otherIndex0;
        PxU32 otherIndex1;
        if (axis == Axis::eX)
        {
            axisIndex = 0;
            otherIndex0 = 1;
            otherIndex1 = 2;
        }
        else if (axis == Axis::eY)
        {
            axisIndex = 1;
            otherIndex0 = 0;
            otherIndex1 = 2;
        }
        else
        {
            axisIndex = 2;
            otherIndex0 = 0;
            otherIndex1 = 1;
        }

        for (PxU32 i = 0; i < numCirclePoints; i++)
        {
            const PxF32 theta = dtheta * i;
            const PxF32 cosTheta = radius * PxCos(theta);
            const PxF32 sinTheta = radius * PxSin(theta);

            PxVec3& vt0 = verts[2 * i + 0];
            vt0[axisIndex] = -0.5f * width;
            vt0[otherIndex0] = cosTheta;
            vt0[otherIndex1] = sinTheta;

            PxVec3& vt1 = verts[2 * i + 1];
            vt1[axisIndex] = +0.5f * width;
            vt1[otherIndex0] = cosTheta;
            vt1[otherIndex1] = sinTheta;
        }

        // Create descriptor for convex mesh
        PxConvexMeshDesc convexDesc;
        convexDesc.points.count = numVerts;
        convexDesc.points.stride = sizeof(PxVec3);
        convexDesc.points.data = verts;
        convexDesc.flags = PxConvexFlag::eCOMPUTE_CONVEX;

        PxConvexMesh* convexMesh = PxCreateConvexMesh(m_defaultCookingParams, convexDesc);
        return convexMesh;
    }

    PxConvexMesh* getCylinderConvexMesh(enum Axis::Enum axis)
    {
        if (axis == Axis::eX)
        {
            if (!m_CylinderMeshX)
            {
                m_CylinderMeshX = createCylinderConvexMesh(
                    gConeOrCylinderWidth, gConeOrCylinderRadius, gCylinderNumCirclePoints, Axis::eX);
            }
            return m_CylinderMeshX;
        }
        else if (axis == Axis::eY)
        {
            if (!m_CylinderMeshY)
            {
                m_CylinderMeshY = createCylinderConvexMesh(
                    gConeOrCylinderWidth, gConeOrCylinderRadius, gCylinderNumCirclePoints, Axis::eY);
            }
            return m_CylinderMeshY;
        }
        else
        {
            if (!m_CylinderMeshZ)
            {
                m_CylinderMeshZ = createCylinderConvexMesh(
                    gConeOrCylinderWidth, gConeOrCylinderRadius, gCylinderNumCirclePoints, Axis::eZ);
            }
            return m_CylinderMeshZ;
        }
    }

    PxConvexMesh* createConeConvexMesh(const PxF32 width,
                                       const PxF32 radius,
                                       const PxU32 numCirclePoints,
                                       enum Axis::Enum axis)
    {
#define MAX_NUM_VERTS_IN_CIRCLE 64
        CARB_ASSERT(numCirclePoints <= MAX_NUM_VERTS_IN_CIRCLE);
        PxVec3 verts[MAX_NUM_VERTS_IN_CIRCLE + 1];
        PxU32 numVerts = numCirclePoints + 1;
        const PxF32 dtheta = 2 * PxPi / (1.0f * numCirclePoints);

        PxU32 axisIndex;
        PxU32 otherIndex0;
        PxU32 otherIndex1;
        if (axis == Axis::eX)
        {
            axisIndex = 0;
            otherIndex0 = 1;
            otherIndex1 = 2;
        }
        else if (axis == Axis::eY)
        {
            axisIndex = 1;
            otherIndex0 = 0;
            otherIndex1 = 2;
        }
        else
        {
            axisIndex = 2;
            otherIndex0 = 0;
            otherIndex1 = 1;
        }

        for (PxU32 i = 0; i < numCirclePoints; i++)
        {
            const PxF32 theta = dtheta * i;
            const PxF32 cosTheta = radius * PxCos(theta);
            const PxF32 sinTheta = radius * PxSin(theta);

            PxVec3& vt = verts[i];
            vt[axisIndex] = -0.5f * width;
            vt[otherIndex0] = cosTheta;
            vt[otherIndex1] = sinTheta;
        }
        PxVec3& vt = verts[numCirclePoints];
        vt[axisIndex] = 0.5f * width;
        vt[otherIndex0] = 0;
        vt[otherIndex1] = 0;

        // Create descriptor for convex mesh
        PxConvexMeshDesc convexDesc;
        convexDesc.points.count = numVerts;
        convexDesc.points.stride = sizeof(PxVec3);
        convexDesc.points.data = verts;
        convexDesc.flags = PxConvexFlag::eCOMPUTE_CONVEX;

        PxConvexMesh* convexMesh = PxCreateConvexMesh(m_defaultCookingParams, convexDesc);
        return convexMesh;
    }

    PxConvexMesh* getConeConvexMesh(enum Axis::Enum axis)
    {
        if (axis == Axis::eX)
        {
            if (!m_ConeMeshX)
            {
                m_ConeMeshX =
                    createConeConvexMesh(gConeOrCylinderWidth, gConeOrCylinderRadius, gConeNumCirclePoints, Axis::eX);
            }
            return m_ConeMeshX;
        }
        else if (axis == Axis::eY)
        {
            if (!m_ConeMeshY)
            {
                m_ConeMeshY =
                    createConeConvexMesh(gConeOrCylinderWidth, gConeOrCylinderRadius, gConeNumCirclePoints, Axis::eY);
            }
            return m_ConeMeshY;
        }
        else
        {
            if (!m_ConeMeshZ)
            {
                m_ConeMeshZ =
                    createConeConvexMesh(gConeOrCylinderWidth, gConeOrCylinderRadius, gConeNumCirclePoints, Axis::eZ);
            }
            return m_ConeMeshZ;
        }
    }

    PxVec3 getConeOrCylinderScale(const ::physx::PxF32 halfWidth, const ::physx::PxF32 radius, enum Axis::Enum axis)
    {
        PxVec3 scale;
        if (axis == Axis::eX)
        {
            scale.x = halfWidth;
            scale.y = radius;
            scale.z = radius;
        }
        else if (axis == Axis::eY)
        {
            scale.x = radius;
            scale.y = halfWidth;
            scale.z = radius;
        }
        else
        {
            scale.x = radius;
            scale.y = radius;
            scale.z = halfWidth;
        }

        return scale;
    }

    void releaseCylinderMeshes()
    {
        if (m_CylinderMeshX)
        {
            m_CylinderMeshX->release();
            m_CylinderMeshX = nullptr;
        }
        if (m_CylinderMeshY)
        {
            m_CylinderMeshY->release();
            m_CylinderMeshY = nullptr;
        }
        if (m_CylinderMeshZ)
        {
            m_CylinderMeshZ->release();
            m_CylinderMeshZ = nullptr;
        }
    }

    void releaseConeMeshes()
    {
        if (m_ConeMeshX)
        {
            m_ConeMeshX->release();
            m_ConeMeshX = nullptr;
        }
        if (m_ConeMeshY)
        {
            m_ConeMeshY->release();
            m_ConeMeshY = nullptr;
        }
        if (m_ConeMeshZ)
        {
            m_ConeMeshZ->release();
            m_ConeMeshZ = nullptr;
        }
    }

    void releaseGeomInfo()
    {
        releaseCylinderMeshes();
        releaseConeMeshes();

        // triMesh will be released in m_cookedTriMeshes
        m_geomMap.clear();
    }

    bool isPathAllowed(const SdfPath& primPath) const
    {
        auto context = getCurrentContext();
        if (context->hitFilterFn && !context->hitFilterFn(primPath.GetText()))
        {
            return false;
        }

        if (!context->disallowedMeshPaths.empty())
        {
            std::vector<SdfPath> pathsToCheck;
            if (context->disallowedPathIncludeDescendants)
            {
                pathsToCheck = primPath.GetPrefixes();
            }
            else
            {
                pathsToCheck.push_back(primPath);
            }

            for (const auto& path : pathsToCheck)
            {
                if (context->disallowedMeshPaths.find(path) != context->disallowedMeshPaths.end())
                {
                    return false;
                }
            }
        }

        if (!context->allowedMeshPaths.empty() &&
            context->allowedMeshPaths.find(primPath) == context->allowedMeshPaths.end())
        {
            return false;
        }

        return true;
    }

    const RaycastContext* getCurrentContext() const
    {
        if (m_currentContext == nullptr)
        {
            return m_defaultContext.get();
        }
        return m_currentContext;
    }

    RaycastContext* getActualContext(RaycastContext* context) const
    {
        if (context == nullptr)
        {
            return m_defaultContext.get();
        }

        return context;
    }
};

class ExtensionImpl final : public omni::ext::IExt
{
public:
    void onStartup(const char*) final
    {
        CARB_PROFILE_ZONE(1, "IMeshRaycast: ExtensionImpl::onStartup");

        IMeshRaycast* meshRaycast = carb::getCachedInterface<IMeshRaycast>();
        MeshRaycast* impl = static_cast<MeshRaycast*>(meshRaycast);
        impl->startup();
    }

    void onShutdown() final
    {
        CARB_PROFILE_ZONE(1, "IMeshRaycast: ExtensionImpl::onShutdown");
        IMeshRaycast* meshRaycast = carb::getCachedInterface<IMeshRaycast>();
        MeshRaycast* impl = static_cast<MeshRaycast*>(meshRaycast);
        impl->shutdown();
    }
};

} // namespace meshraycast
} // namespace omni

CARB_EXPORT void carbOnPluginStartup()
{
}

CARB_EXPORT void carbOnPluginShutdown()
{
}

CARB_PLUGIN_IMPL(kPluginImpl, omni::meshraycast::ExtensionImpl, omni::meshraycast::MeshRaycast)
CARB_PLUGIN_IMPL_DEPS(omni::kit::IApp, carb::events::IEvents, carb::settings::ISettings, carb::tasking::ITasking)

void fillInterface(omni::meshraycast::ExtensionImpl& iface)
{
}

void fillInterface(omni::meshraycast::MeshRaycast& iface)
{
}

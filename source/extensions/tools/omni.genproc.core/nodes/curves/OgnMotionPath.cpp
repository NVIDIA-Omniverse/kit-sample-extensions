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

#include "../plugins/CurveUtils.h"

#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/timeline/ITimeline.h>

#include <OgnMotionPathDatabase.h>
#include <algorithm>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttributeInfo;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::geometry::curves;
using namespace omni::genproc;

class OgnMotionPath
{
public:
    // static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    //{
    //}

    // static void writeToOutput(OgnMotionPathDatabase& db,
    //                          const std::vector<std::pair<vec3f, vec3f> >& curveEndpoints,
    //                          const std::vector<vec3f>& curveDirections)
    //{
    //}
    static pxr::GfVec3d axisToVec(int axis)
    {
        if (axis == 0)
            return pxr::GfVec3d(1.0, 0.0, 0.0);
        else if (axis == 1)
            return pxr::GfVec3d(0.0, 1.0, 0.0);
        else if (axis == 2)
            return pxr::GfVec3d(0.0, 0.0, 1.0);
        else if (axis == 3)
            return pxr::GfVec3d(-1.0, 0.0, 0.0);
        else if (axis == 4)
            return pxr::GfVec3d(0.0, -1.0, 0.0);
        else if (axis == 5)
            return pxr::GfVec3d(0.0, 0.0, -1.0);
        else
        {
            CARB_LOG_ERROR("%d is an invalid input axis value!\n", axis);
            return pxr::GfVec3d();
        }
    }
    static pxr::GfVec3d getSceneUpVec(const GraphContextObj& context, const NodeObj& nodeObj)
    {
        const INode* const iNode = nodeObj.iNode;
        const IGraphContext* const iContext = context.iContext;

        long int stageId = iContext->getStageId(context);
        auto usdStage = pxr::UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
        pxr::TfToken upAxisToken;
        if (usdStage->GetMetadata(pxr::TfToken("upAxis"), &upAxisToken))
        {
            if (upAxisToken == "X" || upAxisToken == "x")
            {
                return pxr::GfVec3d(1.0, 0.0, 0.0);
            }
            else if (upAxisToken == "Z" || upAxisToken == "z")
            {
                return pxr::GfVec3d(0.0, 0.0, 1.0);
            }
        }
        return pxr::GfVec3d(0.0, 1.0, 0.0);
    }
    static pxr::UsdPrim getUsdPrimFromNode(const GraphContextObj& context, const NodeObj& nodeObj)
    {
        const INode* const iNode = nodeObj.iNode;
        const IGraphContext* const iContext = context.iContext;

        long int stageId = iContext->getStageId(context);
        auto usdStage = pxr::UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
        const char* primPathStr = iNode->getPrimPath(nodeObj);
        pxr::SdfPath primPath(primPathStr);
        return usdStage->GetPrimAtPath(primPath);
    }
    static bool getWorldUpObjectTranslate(OgnMotionPathDatabase& db, pxr::UsdPrim thisPrim, pxr::GfVec3d& wuoPos)
    {
        const pxr::UsdRelationship wuoRelationship = thisPrim.GetRelationship(pxr::TfToken("inputs:worldUpObject"));
        if (wuoRelationship)
        {
            pxr::SdfPathVector wuoPaths;
            wuoRelationship.GetTargets(&wuoPaths);
            if (!wuoPaths.empty())
            {
                auto stage = thisPrim.GetStage();
                auto wuoPrim = stage->GetPrimAtPath(wuoPaths[0]);
                static auto* timeline = carb::getFramework()->tryAcquireInterface<omni::timeline::ITimeline>();
                double timelineTime = timeline->getCurrentTime();
                double fps = timeline->getTimeCodesPerSecond();
                double usdTimecode = timelineTime * fps;
                pxr::UsdGeomXformCache xformCache(usdTimecode);
                auto wuoMtx = xformCache.GetLocalToWorldTransform(wuoPrim);
                wuoPos = wuoMtx.ExtractTranslation();
                return true;
            }
        }
        return false;
    }
    static bool compute(OgnMotionPathDatabase& db)
    {
        ConstBundlePrims curvePrim(db.abi_context(), db.inputs.curveBundle().abi_bundleHandle());
        const size_t curvePrimCount = curvePrim.getPrimCount();

        // TODO: should we check 0 curve count?
        if (curvePrimCount > 1)
        {
            CARB_LOG_ERROR("MotionPath: Only one curve bundle is allowed!");
            return false;
        }

        pxr::UsdPrim thisPrim = getUsdPrimFromNode(db.abi_context(), db.abi_node());
        if (!thisPrim.IsValid())
        {
            CARB_LOG_ERROR("OgnMotionPath :the compute node requires a USD prim in order to access the stage.");
            return false;
        }

        float uValue = db.inputs.uValue();
        if (db.inputs.cycle())
        {
            auto m = fmod(uValue, 1.0f);
            uValue = m >= 0.0f ? m : 1 + m;
        }
        else
        {
            uValue = uValue <= 0.0f ? 0.0f : uValue <= 1.0f ? uValue : 1.0f;
        }

        bool foundCurve = false;
        vec3f pointOnCurve, tangentAtPoint;

        auto processingOp = [&](const bool validCurve, const std::string& errorMessage, const size_t primIndex,
                                const size_t curveIndex, const SplineCurve* curve,
                                const std::vector<vec3f>* controlPoints)
        {
            if (foundCurve)
            {
                return;
            }

            if (!validCurve)
            {
                CARB_LOG_WARN_ONCE(errorMessage.c_str());
                return;
            }

            const bool normalizeLengths = true;
            const size_t samplesPerSegment = 20;
            const std::vector<float> curveDistances =
                approximateDistanceAlongCurve(*curve, *controlPoints, normalizeLengths, samplesPerSegment);
            const size_t segmentCount = curve->getSegmentCount(controlPoints->size());
            std::vector<float> segmentDistances(segmentCount); // TODO: cache these distances in node state until bundle
                                                               // prim dirty ID changes
            for (size_t i = 0; i < segmentCount; i++)
            {
                const size_t lastOffset = (i == segmentCount - 1 ? 1 : 0);
                segmentDistances[i] = curveDistances[(i + 1) * samplesPerSegment + lastOffset - 1];
            }

            size_t segmentIndex = 0;

            while (segmentDistances[segmentIndex] < uValue)
            {
                if (segmentIndex == segmentDistances.size() - 1)
                {
                    break;
                }
                else
                {
                    segmentIndex++;
                }
            }
            const float denom =
                segmentDistances[segmentIndex] - (segmentIndex == 0 ? 0.f : segmentDistances[segmentIndex - 1]);
            const float parametricValue =
                (uValue - (segmentIndex == 0 ? 0.f : segmentDistances[segmentIndex - 1])) / denom;

            const size_t segmentStartIndex = segmentIndex * curve->m_vstep;
            const int order = 0;
            pointOnCurve = curve->evaluateSegment(controlPoints->data(), controlPoints->size(), segmentStartIndex,
                                                  parametricValue, order, &tangentAtPoint);

            foundCurve = true;
        };

        processCurvesInBundle(curvePrim, processingOp);

        if (foundCurve)
        {
            // object local mtx
            auto objForward = axisToVec(db.inputs.forwardAxis());
            auto objUp = axisToVec(db.inputs.upAxis());
            auto objRight = pxr::GfCross(objForward, objUp).GetNormalized();

            // illegal settings
            if (objRight.GetLength() < 0.01)
            {
                CARB_LOG_WARN_ONCE("MotionPath: Illegal settings! Check Forward Axis and Up Axis.");
                return false;
            }

            pxr::GfMatrix4d localMtx = pxr::GfMatrix4d().SetIdentity();
            localMtx.SetRow3(0, objForward);
            localMtx.SetRow3(1, objUp);
            localMtx.SetRow3(2, objRight);

            // get aim vector
            auto aimVec = pxr::GfVec3d(tangentAtPoint.data()).GetNormalized();

            // get up axis
            pxr::GfVec3d upVec;
            auto curvePointPos = pxr::GfVec3d(pointOnCurve.data());
            auto worldUpType = db.inputs.worldUpType();
            if (worldUpType == 2)
            {
                upVec = pxr::GfVec3d(db.inputs.worldUpVector().data());
            }
            else if (worldUpType == 1 && getWorldUpObjectTranslate(db, thisPrim, upVec))
            {
                upVec -= curvePointPos;
            }
            else
            {
                upVec = getSceneUpVec(db.abi_context(), db.abi_node());
            }

            upVec = upVec.GetNormalized();
            auto pathRight = pxr::GfCross(aimVec, upVec).GetNormalized();

            // illegal status
            if (pathRight.GetLength() < 0.01)
            {
                CARB_LOG_WARN_ONCE("MotionPath: Illegal state of Aim/Up Vectors.");
                return false;
            }

            upVec = pxr::GfCross(pathRight, aimVec).GetNormalized();

            pxr::GfMatrix4d rotateMtx = pxr::GfMatrix4d().SetIdentity();
            rotateMtx.SetRow3(0, aimVec);
            rotateMtx.SetRow3(1, upVec);
            rotateMtx.SetRow3(2, pathRight);

            // get object rotation
            auto rot = pxr::GfRotation();
            auto angles = pxr::GfVec3d(db.inputs.aimRotation().data());
            if (fabs(angles[0]) >= 0.001f)
                rot *= pxr::GfRotation(pxr::GfVec3d(1.0, 0.0, 0.0), angles[0]);
            if (fabs(angles[1]) >= 0.001f)
                rot *= pxr::GfRotation(pxr::GfVec3d(0.0, 1.0, 0.0), angles[1]);
            if (fabs(angles[2]) >= 0.001f)
                rot *= pxr::GfRotation(pxr::GfVec3d(0.0, 0.0, 1.0), angles[2]);

            auto outputTransform = localMtx.GetInverse() * pxr::GfMatrix4d().SetRotateOnly(rot) * rotateMtx;
            outputTransform.SetTranslateOnly(curvePointPos);

            db.outputs.transform() = omni::math::linalg::safeCastToOmni(outputTransform);
        }
        else
        {
            CARB_LOG_ERROR("MotionPath: Failed to find prim in input bundle with necessary curve attributes.");
            return false;
        }

        db.state.prevUValue() = db.inputs.uValue();

        return true;
    }
};

REGISTER_OGN_NODE()

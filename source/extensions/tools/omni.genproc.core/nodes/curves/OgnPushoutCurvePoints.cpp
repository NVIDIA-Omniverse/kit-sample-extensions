// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

#include "../plugins/CurveFrame.h" // for arbitraryPerpendicular
#include "../plugins/CurveUtils.h"
#include "../plugins/Utils.h"

#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/quat.h>
#include <omni/math/linalg/vec.h>

#include <OgnPushoutCurvePointsDatabase.h>
#include <algorithm>
#include <cmath>
#include <limits>
#include <unordered_map>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::geometry::curves;
using namespace omni::genproc;

class OgnPushoutCurvePoints
{
public:
    enum CollisionProxy : size_t
    {
        SPHERE = 0,
        BOX,
        NUM_COLLISION_PROXY_TYPES
    };

    enum UpAxisSource : size_t
    {
        STAGE = 0,
        NODE,
        NUM_UP_AXIS_SOURCES
    };

    enum BoxFace : size_t
    {
        MIN_X = 0,
        MIN_Y,
        MIN_Z,
        MAX_X,
        MAX_Y,
        MAX_Z
    };

    struct CurveData
    {
        std::vector<size_t> segmentCounts;
        std::vector<std::vector<vec3f>> displacedPoints;
    };

    static void offsetPointsByTransforms(OgnPushoutCurvePointsDatabase& db,
                                         ConstBundlePrims& curvePrims,
                                         std::unordered_map<size_t, CurveData>& curveData)
    {
        const size_t curvePrimCount = curvePrims.getPrimCount();
        ConstBundlePrim& commonAttrs = curvePrims.getConstCommonAttrs();
        BundleAttrib const* transformAttr = commonAttrs.getConstAttr(db.tokens.transform);
        const matrix4d* transformData = nullptr;
        if (transformAttr != nullptr && transformAttr->size() == curvePrimCount)
        {
            transformData = transformAttr->getData<matrix4d>();
        }

        std::vector<matrix4d> inverseTransform(curvePrimCount);
        for (size_t primIndex = 0; primIndex < curvePrimCount; primIndex++)
        {
            const ConstBundlePrim* curvePrim = curvePrims.getPrim(primIndex);
            matrix4d transform;
            if (transformData == nullptr)
            {
                transform.SetIdentity();
            }
            else
            {
                transform = transformData[primIndex];
            }

            inverseTransform[primIndex] = transform.GetInverse();
        }

        for (auto& iter : curveData)
        {
            const size_t primIndex = iter.first;
            std::vector<std::vector<vec3f>>& points = iter.second.displacedPoints;
            const matrix4d& xform = inverseTransform[primIndex];
            for (auto& oneCurve : points)
            {
                for (auto& onePoint : oneCurve)
                {
                    onePoint = xform.Transform(onePoint);
                }
            }
        }
    }

    static void refitCurves(const int numberOfSegments, std::unordered_map<size_t, CurveData>& curveData)
    {
        for (auto& iter : curveData)
        {
            const std::vector<size_t>& segmentCounts = iter.second.segmentCounts;
            std::vector<std::vector<vec3f>>& points = iter.second.displacedPoints;
            CARB_ASSERT(segmentCounts.size() == points.size());
            for (size_t i = 0; i < segmentCounts.size(); i++)
            {
                std::vector<vec3f> newControlPoints;

                size_t m = segmentCounts[i];
                if (numberOfSegments > 0)
                {
                    m = (size_t)numberOfSegments;
                }

                bool success = fitCubicBezierToPoints(points[i], m, newControlPoints);

                if (success)
                {
                    points[i] = std::move(newControlPoints);
                }
                else
                {
                    CARB_LOG_WARN_ONCE("OgnPushoutCurvePoints: Failed to fit new curve after displacing points.");
                }
            }
        }
    }

    static void writeToPointsOutput(OgnPushoutCurvePointsDatabase& db,
                                    ConstBundlePrims& curvePrims,
                                    std::unordered_map<size_t, CurveData>& curveData)
    {
        BundlePrims pointPrims(db.abi_context(), db.outputs.pointsBundle().abi_bundleHandle());

        const size_t curvePrimCount = curvePrims.getPrimCount();
        ConstBundlePrim& commonAttrs = curvePrims.getConstCommonAttrs();
        BundleAttrib const* transformAttr = commonAttrs.getConstAttr(db.tokens.transform);
        const matrix4d* transformData = nullptr;
        if (transformAttr != nullptr && transformAttr->size() == curvePrimCount)
        {
            transformData = transformAttr->getData<matrix4d>();
        }

        std::vector<matrix4d> curveTransform(curvePrimCount);
        for (size_t primIndex = 0; primIndex < curvePrimCount; primIndex++)
        {
            matrix4d transform;
            if (transformData == nullptr)
            {
                transform.SetIdentity();
            }
            else
            {
                transform = transformData[primIndex];
            }
            curveTransform[primIndex] = transform;
        }

        size_t numOutputPrims = 0;
        for (auto& iter : curveData)
        {
            const std::vector<std::vector<vec3f>>& points = iter.second.displacedPoints;
            numOutputPrims += points.size();
        }

        if (pointPrims.getPrimCount() != numOutputPrims)
        {
            pointPrims.clearContents();
            pointPrims.addPrims(numOutputPrims);
        }

        size_t outputPrimIndex = 0;
        for (auto& iter : curveData)
        {
            const std::vector<std::vector<vec3f>>& points = iter.second.displacedPoints;
            for (const auto& oneCurve : points)
            {
                BundlePrim* pointPrim = pointPrims.getPrim(outputPrimIndex);

                BundleAttrib* pointsAttr = pointPrim->addAttr(
                    db.tokens.points, Type(BaseDataType::eFloat, 3, 1, AttributeRole::ePosition), oneCurve.size());
                vec3f* pointsOut = pointsAttr->getData<vec3f>();
                CARB_ASSERT(pointsOut != nullptr);
                memcpy(pointsOut, oneCurve.data(), oneCurve.size() * sizeof(vec3f));

                outputPrimIndex++;
            }
        }
    }

    static void writeToCurvesOutput(OgnPushoutCurvePointsDatabase& db,
                                    ConstBundlePrims& inputPrims,
                                    std::unordered_map<size_t, CurveData>& curveData)
    {
        BundlePrims outputPrims(db.abi_context(), db.outputs.curvesBundle().abi_bundleHandle());

        const size_t inputPrimCount = inputPrims.getPrimCount();
        ConstBundlePrim& commonAttrs = inputPrims.getConstCommonAttrs();
        BundleAttrib const* transformAttr = commonAttrs.getConstAttr(db.tokens.transform);
        const matrix4d* transformData = nullptr;
        if (transformAttr != nullptr && transformAttr->size() == inputPrimCount)
        {
            transformData = transformAttr->getData<matrix4d>();
        }

        std::vector<matrix4d> inputTransform(inputPrimCount);
        for (size_t primIndex = 0; primIndex < inputPrimCount; primIndex++)
        {
            matrix4d transform;
            if (transformData == nullptr)
            {
                transform.SetIdentity();
            }
            else
            {
                transform = transformData[primIndex];
            }
            inputTransform[primIndex] = transform;
        }

        if (outputPrims.getPrimCount() != curveData.size())
        {
            outputPrims.clearContents();
            outputPrims.addPrims(curveData.size());
        }

        size_t outputPrimIndex = 0;
        for (const auto& iter : curveData)
        {
            const std::vector<std::vector<vec3f>>& points = iter.second.displacedPoints;
            size_t totalPointsCount = 0;
            for (const auto& oneCurve : points)
            {
                totalPointsCount += oneCurve.size();
            }

            BundlePrim* outputPrim = outputPrims.getPrim(outputPrimIndex);

            BundleAttrib* basisAttr =
                outputPrim->addAttr(db.tokens.basis, Type(BaseDataType::eToken, 1, 0, AttributeRole::eNone), 0);
            NameToken* basisToken = basisAttr->getData<NameToken>();
            CARB_ASSERT(basisToken != nullptr);
            *basisToken = db.tokens.bezier;

            BundleAttrib* wrapAttr =
                outputPrim->addAttr(db.tokens.wrap, Type(BaseDataType::eToken, 1, 0, AttributeRole::eNone), 0);
            NameToken* wrapToken = wrapAttr->getData<NameToken>();
            CARB_ASSERT(wrapToken != nullptr);
            *wrapToken = db.tokens.nonperiodic;

            BundleAttrib* pointsAttr = outputPrim->addAttr(
                db.tokens.points, Type(BaseDataType::eFloat, 3, 1, AttributeRole::ePosition), totalPointsCount);
            vec3f* pointsOut = pointsAttr->getData<vec3f>();
            CARB_ASSERT(pointsOut != nullptr);

            BundleAttrib* vertexCountsAttr = outputPrim->addAttr(
                db.tokens.curveVertexCounts, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone), points.size());
            int* vertexCountsOut = vertexCountsAttr->getData<int>();
            CARB_ASSERT(vertexCountsOut != nullptr);

            size_t pointsOffset = 0;
            for (size_t i = 0; i < points.size(); i++)
            {
                const std::vector<vec3f>& oneCurve = points[i];
                for (size_t j = 0; j < oneCurve.size(); j++)
                {
                    pointsOut[pointsOffset + j] = oneCurve[j];
                }
                vertexCountsOut[i] = (int)oneCurve.size();
                pointsOffset += oneCurve.size();
            }

            outputPrimIndex++;
        }
    }

    static bool compute(OgnPushoutCurvePointsDatabase& db)
    {
        auto& context = db.abi_context();

        bool inputsChanged =
            db.inputs.curvesBundle.changes().hasChanged() || db.inputs.collisionBundle.changes().hasChanged() ||
            (db.inputs.samplesPerSegment() != db.state.prevSamplesPerSegment()) ||
            (db.inputs.collisionProxy() != db.state.prevCollisionProxy()) ||
            (db.inputs.pushoutHorizontally() != db.state.prevPushoutHorizontally()) ||
            (db.inputs.upAxisSource() != db.state.prevUpAxisSource()) || (db.inputs.upAxis() != db.state.prevUpAxis()) ||
            (db.inputs.numberOfSegments() != db.state.prevNumberOfSegments());
        if (!inputsChanged)
        {
            return true;
        }

        ConstBundlePrims curvePrims(db.abi_context(), db.inputs.curvesBundle().abi_bundleHandle());

        ConstBundlePrims collisionPrims(db.abi_context(), db.inputs.collisionBundle().abi_bundleHandle());
        const size_t collisionPrimCount = collisionPrims.getPrimCount();

        CollisionProxy collisionProxy = CollisionProxy(db.inputs.collisionProxy());
        if (collisionProxy >= NUM_COLLISION_PROXY_TYPES)
        {
            collisionProxy = CollisionProxy(size_t(NUM_COLLISION_PROXY_TYPES) - 1);
        }

        const bool pushoutHorizontally = db.inputs.pushoutHorizontally();
        const size_t samplesPerSegment =
            db.inputs.samplesPerSegment() > 0 ? (size_t)db.inputs.samplesPerSegment() : (size_t)1;

        // We only care about the up vector if the pushoutHorizontally option is true.
        // We can either pull up from the USD stage or from the node's input.
        //
        // Note that for box pushout, currently only axis-aligned up vectors are supported.
        vec3f up;
        if (pushoutHorizontally)
        {
            UpAxisSource upAxisSource = UpAxisSource(db.inputs.upAxisSource());
            if (upAxisSource >= NUM_UP_AXIS_SOURCES)
            {
                upAxisSource = UpAxisSource(size_t(NUM_UP_AXIS_SOURCES) - 1);
            }

            switch (upAxisSource)
            {
            case STAGE:
            {
                long int stageId = context.iContext->getStageId(context);
                auto stage = pxr::UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
                if (stage == nullptr)
                {
                    return false;
                }

                const pxr::TfToken upAxis = pxr::UsdGeomGetStageUpAxis(stage);
                up = upAxis == pxr::UsdGeomTokens->x ? vec3f(1, 0, 0) :
                     upAxis == pxr::UsdGeomTokens->y ? vec3f(0, 1, 0) :
                                                       vec3f(0, 0, 1);
                break;
            }
            case NODE:
                up = db.inputs.upAxis().GetNormalized();
                if (collisionProxy == BOX)
                {
                    size_t maxDimension = 0;
                    float maxValue = std::abs(up[maxDimension]);
                    for (size_t i = 1; i < vec3f::dimension; i++)
                    {
                        float value = std::abs(up[i]);
                        if (value > maxValue)
                        {
                            maxDimension = i;
                            maxValue = value;
                        }
                    }
                    for (size_t i = 0; i < vec3f::dimension; i++)
                    {
                        if (i != maxDimension && up[i] != 0.f)
                        {
                            CARB_LOG_WARN_ONCE(
                                "PushoutCurvePoints: for box pushout, currently the up vector can only be a primary world axis. The specified up vector will be clamped.");
                            up[i] = 0.f;
                        }
                    }
                    up.Normalize();
                }
                break;
            default:
                CARB_ASSERT(0);
            }
        }

        // sphere bounding volumes
        std::vector<vec3f> centers;
        std::vector<float> radiiSquared;

        // box bounding volumes
        std::vector<std::pair<vec3f, vec3f>> extents;

        if (collisionProxy == SPHERE)
        {
            getPrimBoundingSpheres(collisionPrims, centers, radiiSquared);
        }
        else // collisionProxy == BOX
        {
            getPrimBoundingBoxes(collisionPrims, extents);
        }

        // for each prim containing curves, a list of displaced points
        // std::vector<std::pair<size_t, std::vector<vec3f> > > curvePoints;
        std::unordered_map<size_t, CurveData> curveData;

        auto processingOp = [&](const bool validCurve, const std::string& errorMessage, const size_t primIndex,
                                const size_t curveIndex, const SplineCurve* curve,
                                const std::vector<vec3f>* controlPoints)
        {
            if (!validCurve)
            {
                CARB_LOG_WARN_ONCE(errorMessage.c_str());
                return;
            }

            std::vector<vec3f> points;
            const bool includeSegmentFinalSamples = false;
            curve->tessellate(
                controlPoints->data(), controlPoints->size(), points, samplesPerSegment, includeSegmentFinalSamples);

            const size_t pointsCount = points.size();

            // For either pushout type, we find sections of the curve that are inside the volume and operate on each
            // section independently
            if (collisionProxy == SPHERE)
            {
                // For sphere pushout, we consider the direction between the direction from the sphere center to the
                // first inside point and the direction from the sphere center to the last inside point. We project the
                // in-between points to the sphere surface by raycasting them to the sphere in that direction.

                // If pushoutHorizontally is true, we project out the up-component of that direction.


                // Iterate over each prim. This won't handle overlapping prims / points inside multiple very well;
                // it's just something to start with...
                for (size_t primIndex = 0; primIndex < collisionPrimCount; primIndex++)
                {
                    const vec3f& center = centers[primIndex];
                    const float& radiusSqr = radiiSquared[primIndex];

                    bool hasStart = false, hasEnd = false;
                    size_t startIdx = 0, endIdx = 0;

                    for (size_t i = 0; i < pointsCount; i++)
                    {
                        const bool inside = (points[i] - center).GetLengthSq() < radiusSqr;
                        if (hasStart)
                        {
                            if (!inside)
                            {
                                endIdx = i - 1;
                                hasEnd = true;
                            }
                        }
                        else
                        {
                            if (inside)
                            {
                                startIdx = i;
                                hasStart = true;
                            }
                        }

                        if (i == pointsCount - 1)
                        {
                            hasEnd = true;
                            endIdx = i;
                        }

                        if (hasStart && hasEnd)
                        {
                            // the particles between [startIdx, endIdx] are inside the sphere

                            // NOTE: could also find the intersection of the line segment between startIdx - 1 and
                            // startIdx, and the line segment between endIdx and endIdx + 1...

                            const vec3f d1 = (points[startIdx] - center).GetNormalized();
                            const vec3f d2 = (points[endIdx] - center).GetNormalized();

                            const float smallNumber = 1e-6f;

                            vec3f d;
                            if (1.f - std::abs(d1.Dot(d2)) < smallNumber)
                            {
                                d = arbitraryPerpendicular(d1);
                            }
                            else
                            {
                                d = (d1 + d2).GetNormalized();
                            }

                            if (pushoutHorizontally)
                            {
                                if (1.f - std::abs(d.Dot(up)) < smallNumber)
                                {
                                    d = arbitraryPerpendicular(up);
                                }
                                else
                                {
                                    d = d.GetComplement(up).GetNormalized();
                                }
                            }

                            const vec3f& c = center;
                            const float& r2 = radiusSqr;

                            for (size_t j = startIdx; j <= endIdx; j++)
                            {
                                const vec3f o = points[j];
                                const vec3f oc = (o - c);
                                const float disc =
                                    4.f * d.Dot(oc) * d.Dot(oc) - 4.f * d.GetLengthSq() * (oc.GetLengthSq() - r2);

                                CARB_ASSERT(disc >= 0.f); // otherwise what are we doing here?

                                const float t = (-2.f * d.Dot(oc) + std::sqrt(disc)) / (2.f * d.GetLengthSq());
                                points[j] = o + t * d;
                            }

                            hasStart = false;
                            hasEnd = false;
                        }
                    }
                }
            }
            else // collisionProxy == BOX
            {
                // For box pushout, we project the first and last inside points to the box, then look at the midpoint of
                // the line between those projected points. We project all the inside points to the box face closest to
                // that midpoint.

                // If pushoutHorizontally is true, we only consider box faces whose normals are perpendicular to the up
                // vector (which is constrained to be along one of the primary world axes; no diagonal up business...)
                for (size_t primIndex = 0; primIndex < collisionPrimCount; primIndex++)
                {
                    const vec3f& minCorner = extents[primIndex].first;
                    const vec3f& maxCorner = extents[primIndex].second;

                    bool hasStart = false, hasEnd = false;
                    size_t startIdx = 0, endIdx = 0;

                    for (size_t i = 0; i < pointsCount; i++)
                    {
                        const vec3f& point = points[i];
                        bool inside = true;
                        for (size_t d = 0; d < vec3f::dimension; d++)
                        {
                            inside = inside && (point[d] > minCorner[d] && point[d] < maxCorner[d]);
                        }

                        if (hasStart)
                        {
                            if (!inside)
                            {
                                endIdx = i - 1;
                                hasEnd = true;
                            }
                        }
                        else
                        {
                            if (inside)
                            {
                                startIdx = i;
                                hasStart = true;
                            }
                        }

                        if (i == pointsCount - 1)
                        {
                            hasEnd = true;
                            endIdx = i;
                        }

                        if (hasStart && hasEnd)
                        {
                            // the particles between [startIdx, endIdx] are inside the box

                            BoxFace startFace, endFace;
                            vec3f startPoint = points[startIdx], endPoint = points[endIdx];
                            for (size_t j = 0; j < 2; j++)
                            {
                                const size_t& idx = (j == 0 ? startIdx : endIdx);
                                vec3f& point = (j == 0 ? startPoint : endPoint);
                                BoxFace& face = (j == 0 ? startFace : endFace);

                                vec3f distanceToMin = points[idx] - minCorner;
                                vec3f distanceToMax = points[idx] - maxCorner;
                                for (size_t d = 0; d < vec3f::dimension; d++)
                                {
                                    distanceToMin[d] = std::abs(distanceToMin[d]);
                                    distanceToMax[d] = std::abs(distanceToMax[d]);
                                }
                                float distance = distanceToMin[0];
                                face = MIN_X;
                                if (distanceToMin[1] < distance)
                                {
                                    distance = distanceToMin[1];
                                    face = MIN_Y;
                                }
                                if (distanceToMin[2] < distance)
                                {
                                    distance = distanceToMin[2];
                                    face = MIN_Z;
                                }
                                if (distanceToMax[0] < distance)
                                {
                                    distance = distanceToMax[0];
                                    face = MAX_X;
                                }
                                if (distanceToMax[1] < distance)
                                {
                                    distance = distanceToMax[1];
                                    face = MAX_Y;
                                }
                                if (distanceToMax[2] < distance)
                                {
                                    distance = distanceToMax[2];
                                    face = MAX_Z;
                                }

                                switch (face)
                                {
                                case MIN_X:
                                    point[0] = minCorner[0];
                                    break;
                                case MIN_Y:
                                    point[1] = minCorner[1];
                                    break;
                                case MIN_Z:
                                    point[2] = minCorner[2];
                                    break;
                                case MAX_X:
                                    point[0] = maxCorner[0];
                                    break;
                                case MAX_Y:
                                    point[1] = maxCorner[1];
                                    break;
                                case MAX_Z:
                                    point[2] = maxCorner[2];
                                    break;
                                }
                            }

                            vec3f midpoint = 0.5f * (startPoint + endPoint);

                            // see which face is closest to the midpoint...
                            vec3f distanceToMin = midpoint - minCorner;
                            vec3f distanceToMax = midpoint - maxCorner;
                            for (size_t d = 0; d < vec3f::dimension; d++)
                            {
                                distanceToMin[d] = std::abs(distanceToMin[d]);
                                distanceToMax[d] = std::abs(distanceToMax[d]);
                            }
                            float distance = std::numeric_limits<float>::max();
                            BoxFace midpointFace = MIN_X;
                            if (pushoutHorizontally)
                            {
                                if (up[0] == 0.f)
                                {
                                    if (distanceToMin[0] < distance)
                                    {
                                        distance = distanceToMin[0];
                                        midpointFace = MIN_X;
                                    }
                                    if (distanceToMax[0] < distance)
                                    {
                                        distance = distanceToMax[0];
                                        midpointFace = MAX_X;
                                    }
                                }
                                if (up[1] == 0.f)
                                {
                                    if (distanceToMin[1] < distance)
                                    {
                                        distance = distanceToMin[1];
                                        midpointFace = MIN_Y;
                                    }
                                    if (distanceToMax[1] < distance)
                                    {
                                        distance = distanceToMax[1];
                                        midpointFace = MAX_Y;
                                    }
                                }
                                if (up[2] == 0.f)
                                {
                                    if (distanceToMin[2] < distance)
                                    {
                                        distance = distanceToMin[2];
                                        midpointFace = MIN_Z;
                                    }
                                    if (distanceToMax[2] < distance)
                                    {
                                        distance = distanceToMax[2];
                                        midpointFace = MAX_Z;
                                    }
                                }
                            }
                            else
                            {
                                if (distanceToMin[0] < distance)
                                {
                                    distance = distanceToMin[0];
                                    midpointFace = MIN_X;
                                }
                                if (distanceToMin[1] < distance)
                                {
                                    distance = distanceToMin[1];
                                    midpointFace = MIN_Y;
                                }
                                if (distanceToMin[2] < distance)
                                {
                                    distance = distanceToMin[2];
                                    midpointFace = MIN_Z;
                                }
                                if (distanceToMax[0] < distance)
                                {
                                    distance = distanceToMax[0];
                                    midpointFace = MAX_X;
                                }
                                if (distanceToMax[1] < distance)
                                {
                                    distance = distanceToMax[1];
                                    midpointFace = MAX_Y;
                                }
                                if (distanceToMax[2] < distance)
                                {
                                    distance = distanceToMax[2];
                                    midpointFace = MAX_Z;
                                }
                            }

                            switch (midpointFace)
                            {
                            case MIN_X:
                                for (size_t j = startIdx; j <= endIdx; j++)
                                {
                                    points[j][0] = minCorner[0];
                                }
                                break;
                            case MIN_Y:
                                for (size_t j = startIdx; j <= endIdx; j++)
                                {
                                    points[j][1] = minCorner[1];
                                }
                                break;
                            case MIN_Z:
                                for (size_t j = startIdx; j <= endIdx; j++)
                                {
                                    points[j][2] = minCorner[2];
                                }
                                break;
                            case MAX_X:
                                for (size_t j = startIdx; j <= endIdx; j++)
                                {
                                    points[j][0] = maxCorner[0];
                                }
                                break;
                            case MAX_Y:
                                for (size_t j = startIdx; j <= endIdx; j++)
                                {
                                    points[j][1] = maxCorner[1];
                                }
                                break;
                            case MAX_Z:
                                for (size_t j = startIdx; j <= endIdx; j++)
                                {
                                    points[j][2] = maxCorner[2];
                                }
                                break;
                            }

                            hasStart = false;
                            hasEnd = false;
                        }
                    }
                }
            }

            CurveData& data = curveData[primIndex];
            data.segmentCounts.push_back(curve->getSegmentCount(controlPoints->size()));
            data.displacedPoints.push_back(std::move(points));

            // curvePoints.push_back(std::pair<size_t, std::vector<vec3f> >(primIndex, std::move(points)));
        };

        processCurvesInBundle(curvePrims, processingOp);

        // NOTE: if desired later, we can factor out the transforms from the input prims.
        // But if we uncomment this we also need to add the transforms from the input
        // bundle to the output bundles:
        // offsetPointsByTransforms(db, curvePrims, curveData);

        writeToPointsOutput(db, curvePrims, curveData);

        refitCurves(db.inputs.numberOfSegments(), curveData);

        writeToCurvesOutput(db, curvePrims, curveData);

        db.state.prevNumberOfSegments() = db.inputs.numberOfSegments();
        db.state.prevUpAxis() = db.inputs.upAxis();
        db.state.prevUpAxisSource() = db.inputs.upAxisSource();
        db.state.prevPushoutHorizontally() = db.inputs.pushoutHorizontally();
        db.state.prevCollisionProxy() = db.inputs.collisionProxy();
        db.state.prevSamplesPerSegment() = db.inputs.samplesPerSegment();

        return true;
    }
};

REGISTER_OGN_NODE()

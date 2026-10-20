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

#include "CurveUtils.h"
#include "PhysXUtils.h"
#include "Utils.h"

#include <carb/settings/ISettings.h>

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/ramp/IRamp.h>
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

#include <OgnClosestPointOnCurveDatabase.h>
#include <algorithm>
#include <cmath>
#include <limits>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::geometry::curves;
using namespace omni::genproc;

class OgnClosestPointOnCurve
{
public:
    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
    }

    static void writeToOutput(OgnClosestPointOnCurveDatabase& db,
                              const std::vector<std::pair<vec3f, vec3f>>& curveEndpoints,
                              const std::vector<vec3f>& curveDirections)
    {
    }

    static void updateCachedState(OgnClosestPointOnCurveDatabase& db,
                                  const size_t samplesPerSegment,
                                  ConstBundlePrims& curvePrims,
                                  BundlePrims& cachePrims)
    {
        const size_t curvePrimCount = curvePrims.getPrimCount();
        bool recomputeAll = true; // NOTE: no longer track per-prim dirtiness -- if the input bundle has any change,
                                  // we're going to recompute everything

        auto& context = db.abi_context();

        std::vector<matrix4d> transforms;
        getPrimTransforms(curvePrims, transforms); // it's overkill to get all the xforms only to use one...

        if (recomputeAll)
        {
            cachePrims.clearContents();
            cachePrims.addPrims(curvePrimCount);
        }

        for (size_t primIndex = 0; primIndex < curvePrimCount; primIndex++)
        {
            ConstBundlePrim* curvePrim = curvePrims.getConstPrim(primIndex);
            if (!recomputeAll)
            {
                continue;
            }

            BundlePrim* cachePrim = cachePrims.getPrim(primIndex);
            cachePrim->clearContents();
            cachePrim->setPath(curvePrim->path());

            const matrix4d& transform = transforms[primIndex];

            BundleAttrib const* pointsInAttr = curvePrim->getConstAttr(db.tokens.points);
            BundleAttrib const* curveVertexCountsAttr = curvePrim->getConstAttr(db.tokens.curveVertexCounts);
            BundleAttrib const* curveBasisAttr = curvePrim->getConstAttr(db.tokens.basis);
            BundleAttrib const* wrapTypeAttr = curvePrim->getConstAttr(db.tokens.wrap);

            // Note: it's ok if curveVertexCountsAttr does not exist, in the case of a single curve
            if (pointsInAttr == nullptr || curveBasisAttr == nullptr || wrapTypeAttr == nullptr)
            {
                CARB_LOG_WARN("Input prim does not have basis curve attributes.");
                continue;
            }

            const size_t pointsInCount = pointsInAttr->size();
            if (pointsInCount == 0)
            {
                CARB_LOG_WARN("No points in input prim.");
                continue;
            }
            const vec3f* const pointsIn = pointsInAttr->getData<vec3f>();
            const int* curveVertexCounts =
                curveVertexCountsAttr == nullptr ? nullptr : curveVertexCountsAttr->getData<int>();
            const size_t curveCount = curveVertexCounts == nullptr ? 0 : curveVertexCountsAttr->size();
            const auto* basisToken = curveBasisAttr->getData<omni::graph::core::NameToken>();
            const auto* wrapToken = wrapTypeAttr->getData<omni::graph::core::NameToken>();

            if (pointsIn == nullptr || basisToken == nullptr || wrapToken == nullptr)
            {
                CARB_LOG_WARN("Input prim does not have valid basis curve data.");
                continue;
            }

            eBasisCurveWrap curveWrapType;
            if (*wrapToken == db.tokens.nonperiodic)
            {
                curveWrapType = eBasisCurveWrap::NonPeriodic;
            }
            else if (*wrapToken == db.tokens.periodic)
            {
                curveWrapType = eBasisCurveWrap::Periodic;
            }
            else if (*wrapToken == db.tokens.pinned)
            {
                curveWrapType = eBasisCurveWrap::Pinned;
            }
            else
            {
                CARB_LOG_WARN("Invalid curve wrap type.");
                continue;
            }

            eBasisCurveType curveBasisType;

            if (*basisToken == db.tokens.bspline)
            {
                curveBasisType = eBasisCurveType::BSpline;
            }
            else if (*basisToken == db.tokens.bezier)
            {
                curveBasisType = eBasisCurveType::Bezier;
            }
            else if (*basisToken == db.tokens.catmullRom)
            {
                curveBasisType = eBasisCurveType::CatmullRom;
            }
            else
            {
                CARB_LOG_WARN("Invalid curve basis type.");
                continue;
            }

            std::vector<vec3f> positions, tangents;
            std::vector<int> vertexCountsPerCurve(curveCount == 0 ? 1 : curveCount);
            std::vector<float> segmentDistances;
            std::vector<int> segmentCountsPerCurve(curveCount == 0 ? 1 : curveCount);

            for (size_t curveIndex = 0, startIndex = 0; curveIndex < (curveCount == 0 ? 1 : curveCount); curveIndex++)
            {
                const size_t count = (curveCount == 0 ? pointsInCount : curveVertexCounts[curveIndex]);

                std::vector<vec3f> controlPoints;
                std::transform(pointsIn + startIndex, pointsIn + startIndex + count, std::back_inserter(controlPoints),
                               [&](const vec3f& x) { return transform.Transform(x); });

                startIndex += count;

                SplineCurve curve(curveWrapType, curveBasisType);

                std::vector<vec3f> tessellatedPositions, tessellatedTangents;
                const bool normalizeLengths = true;
                const std::vector<float> curveDistances =
                    approximateDistanceAlongCurve(curve, controlPoints, normalizeLengths, samplesPerSegment,
                                                  &tessellatedPositions, &tessellatedTangents);
                const size_t segmentCount = curve.getSegmentCount(controlPoints.size());
                std::vector<float> curveSegmentDistances(segmentCount);
                for (size_t i = 0; i < segmentCount; i++)
                {
                    const size_t lastOffset = (i == segmentCount - 1 ? 1 : 0);
                    curveSegmentDistances[i] = curveDistances[(i + 1) * samplesPerSegment + lastOffset - 1];
                }

                size_t offset = positions.size();
                positions.resize(offset + tessellatedPositions.size());
                tangents.resize(offset + tessellatedTangents.size());
                for (size_t i = 0; i < tessellatedPositions.size(); i++)
                {
                    positions[offset + i] = tessellatedPositions[i];
                    tangents[offset + i] = tessellatedTangents[i];
                }
                offset = segmentDistances.size();
                segmentDistances.resize(offset + curveSegmentDistances.size());
                for (size_t i = 0; i < curveSegmentDistances.size(); i++)
                {
                    segmentDistances[offset + i] = curveSegmentDistances[i];
                }

                vertexCountsPerCurve[curveIndex] = (int)tessellatedPositions.size();
                segmentCountsPerCurve[curveIndex] = (int)curveSegmentDistances.size();
            }

            BundleAttrib* tessPointsAttr = cachePrim->addAttr(
                db.tokens.points, Type(BaseDataType::eFloat, 3, 1, AttributeRole::ePosition), positions.size());
            vec3f* tessPoints = tessPointsAttr->getData<vec3f>();
            CARB_ASSERT(tessPoints != nullptr);
            memcpy(
                tessPoints, positions.data(), sizeof(typename vec3f::value_type) * vec3f::dimension * positions.size());

            BundleAttrib* tessTangentsAttr = cachePrim->addAttr(
                db.tokens.tangents, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eVector), tangents.size());
            vec3f* tessTangents = tessTangentsAttr->getData<vec3f>();
            CARB_ASSERT(tessTangents != nullptr);
            memcpy(
                tessTangents, tangents.data(), sizeof(typename vec3f::value_type) * vec3f::dimension * tangents.size());

            BundleAttrib* distancesAttr = cachePrim->addAttr(
                db.tokens.distances, Type(BaseDataType::eFloat, 1, 1, AttributeRole::eNone), segmentDistances.size());
            float* distances = distancesAttr->getData<float>();
            CARB_ASSERT(distances != nullptr);
            memcpy(distances, segmentDistances.data(), sizeof(typename vec3f::value_type) * segmentDistances.size());

            BundleAttrib* vertexCountsAttr =
                cachePrim->addAttr(db.tokens.curveVertexCounts, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone),
                                   vertexCountsPerCurve.size());
            int* vertexCounts = vertexCountsAttr->getData<int>();
            CARB_ASSERT(vertexCounts != nullptr);
            memcpy(vertexCounts, vertexCountsPerCurve.data(), sizeof(int) * vertexCountsPerCurve.size());

            BundleAttrib* segmentCountsAttr =
                cachePrim->addAttr(db.tokens.curveSegmentCounts, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone),
                                   segmentCountsPerCurve.size());
            int* segmentCounts = segmentCountsAttr->getData<int>();
            CARB_ASSERT(segmentCounts != nullptr);
            memcpy(segmentCounts, segmentCountsPerCurve.data(), sizeof(int) * segmentCountsPerCurve.size());
        }
    }

    static bool compute(OgnClosestPointOnCurveDatabase& db)
    {
        ConstBundlePrims curvePrims(db.abi_context(), db.inputs.curvesBundle().abi_bundleHandle());
        const size_t curvePrimCount = curvePrims.getPrimCount();

        const bool optionsChanged = (db.state.prevPoint() != db.inputs.point());

        if (!optionsChanged && !db.inputs.curvesBundle.changes().hasChanged())
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        BundlePrims cachePrims(db.abi_context(), db.state.cacheBundle().abi_bundleHandle());

        size_t samplesPerSegment = 100;

        updateCachedState(db, samplesPerSegment, curvePrims, cachePrims);

        const vec3f& point = db.inputs.point();

        bool foundCurve = false;
        vec3f pointOnCurve(0), tangentAtPoint(0);
        float uValueAtPoint;
        float closestDistanceSq = std::numeric_limits<float>::max();
        const float smallNumber = 1.e-6f;

        for (size_t primIndex = 0; primIndex < curvePrimCount && !foundCurve; primIndex++)
        {
            ConstBundlePrim* cachePrim = cachePrims.getConstPrim(primIndex);

            BundleAttrib const* pointsAttr = cachePrim->getConstAttr(db.tokens.points);
            BundleAttrib const* tangentsAttr = cachePrim->getConstAttr(db.tokens.tangents);
            BundleAttrib const* distancesAttr = cachePrim->getConstAttr(db.tokens.distances);
            BundleAttrib const* curveVertexCountsAttr = cachePrim->getConstAttr(db.tokens.curveVertexCounts);
            BundleAttrib const* curveSegmentCountsAttr = cachePrim->getConstAttr(db.tokens.curveSegmentCounts);

            // If anything is missing, just skip this curve.
            // We should have already printed a warning when making the cachePrim.
            if (pointsAttr == nullptr || tangentsAttr == nullptr || distancesAttr == nullptr ||
                curveVertexCountsAttr == nullptr || curveSegmentCountsAttr == nullptr)
            {
                continue;
            }

            const vec3f* const points = pointsAttr->getData<vec3f>();
            const vec3f* const tangents = tangentsAttr->getData<vec3f>();
            const float* const distances = distancesAttr->getData<float>();
            const int* curveVertexCounts = curveVertexCountsAttr->getData<int>();
            const int* curveSegmentCounts = curveSegmentCountsAttr->getData<int>();

            if (points == nullptr || tangents == nullptr || distances == nullptr || curveVertexCounts == nullptr ||
                curveSegmentCounts == nullptr)
            {
                continue;
            }

            CARB_ASSERT(pointsAttr->size() == tangentsAttr->size());
            CARB_ASSERT(curveVertexCountsAttr->size() == curveSegmentCountsAttr->size());

            const size_t curveCount = curveVertexCountsAttr->size();

            for (size_t curveIndex = 0, pointsStart = 0, segmentsStart = 0; curveIndex < curveCount && !foundCurve;
                 curveIndex++)
            {
                const vec3f* curvePoints = points + pointsStart;
                const vec3f* curveTangents = tangents + pointsStart;

                const float* segmentDistances = distances + segmentsStart;

                const size_t vertexCount = curveVertexCounts[curveIndex];
                const size_t segmentCount = curveSegmentCounts[curveIndex];

                pointsStart += vertexCount;
                segmentsStart += segmentCount;

                foundCurve = true;

                size_t closestIndex = 0;
                float closestT = 0.f;
                for (size_t i = 1; i < vertexCount; i++)
                {
                    const vec3f& a = curvePoints[i - 1];
                    const vec3f& b = curvePoints[i];

                    const vec3f ab = b - a;
                    const float ab_length = ab.GetLength();

                    float t = 0.f;

                    if (ab_length > smallNumber)
                    {
                        t = (point - a).GetNormalized().Dot(ab) / ab_length;
                        t = std::max(0.f, std::min(1.f, t)); // clamp to [0, 1]
                    }

                    const vec3f pointOnSegment = (1.f - t) * a + t * b;

                    if ((point - pointOnSegment).GetLengthSq() < closestDistanceSq)
                    {
                        closestDistanceSq = (point - pointOnSegment).GetLengthSq();
                        pointOnCurve = pointOnSegment;

                        closestIndex = i;
                        closestT = t;
                    }
                }

                if (closestIndex != 0)
                {
                    const vec3f& ta = curveTangents[closestIndex - 1];
                    const vec3f& tb = curveTangents[closestIndex];

                    tangentAtPoint = (1.f - closestT) * ta + closestT * tb;

                    size_t index_a = closestIndex - 1;
                    size_t index_b = closestIndex;

                    bool finalSample = (index_b == samplesPerSegment * segmentCount);

                    size_t segment_a = index_a / samplesPerSegment;
                    float u_a = (float)(index_a % samplesPerSegment) / (float)samplesPerSegment;
                    float start_a = segment_a == 0 ? 0.f : segmentDistances[segment_a - 1];
                    float range_a = segment_a == 0 ? segmentDistances[segment_a] :
                                                     segmentDistances[segment_a] - segmentDistances[segment_a - 1];
                    u_a = start_a + u_a * range_a; // TODO: if range_a < smallNumber

                    float u_b;
                    if (finalSample)
                    {
                        // if index_b is the index of the last tessellated point
                        u_b = 1.f;
                    }
                    else
                    {
                        size_t segment_b = index_b / samplesPerSegment;
                        u_b = (float)(index_b % samplesPerSegment) / (float)samplesPerSegment;
                        float start_b = segment_b == 0 ? 0.f : segmentDistances[segment_b - 1];
                        float range_b = segment_b == 0 ? segmentDistances[segment_b] :
                                                         segmentDistances[segment_b] - segmentDistances[segment_b - 1];
                        u_b = start_b + u_b * range_b; // TODO: if range_b < smallNumber
                    }

                    uValueAtPoint = (1.f - closestT) * u_a + closestT * u_b;
                }
            }
        }

        if (foundCurve)
        {
            db.outputs.point() = pointOnCurve;
            db.outputs.tangent() = tangentAtPoint;
            db.outputs.uValue() = uValueAtPoint;
        }
        else
        {
            CARB_LOG_ERROR("ClosestPointOnCurve: Failed to find prim in input bundle with necessary curve attributes.");
            return false;
        }

        db.state.prevPoint() = db.inputs.point();

        return true;
    }
};

REGISTER_OGN_NODE()

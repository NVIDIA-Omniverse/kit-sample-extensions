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
#include "../plugins/Utils.h"

#include <carb/settings/ISettings.h>

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/quat.h>
#include <omni/math/linalg/vec.h>

#include <OgnResampleCurvesDatabase.h>
#include <algorithm>
#include <cmath>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::geometry::curves;
using namespace omni::genproc;

class OgnResampleCurves
{
public:
    enum Mode : size_t
    {
        NUMBER_OF_SEGMENTS = 0,
        STEP,
        NUM_MODE
    };

    static void resampleCurve(OgnResampleCurvesDatabase& db,
                              const SplineCurve& curve,
                              const std::vector<vec3f>& controlPoints,
                              std::vector<vec3f>& resampledControlPoints)
    {
        std::vector<vec3f> tessellatedPositions;
        size_t samplesPerSegment = 20;
        const bool normalizeLengths = false;
        const std::vector<float> curveDistances = approximateDistanceAlongCurve(
            curve, controlPoints, normalizeLengths, samplesPerSegment, &tessellatedPositions);

        Mode mode = Mode(db.inputs.mode());
        if (mode < Mode(0))
            mode = Mode(0);
        if (mode >= NUM_MODE)
            mode = Mode(NUM_MODE - 1);

        const int& numberOfSegments = db.inputs.numberOfSegments();
        const float& stepSize = db.inputs.step();
        // const bool& avoidSharpTurns = db.inputs.avoidSharpTurns(); // currently unused
        const bool& verbose = db.inputs.verbose();

        size_t numResampledSegments = 0;
        switch (mode)
        {
        case STEP:
            numResampledSegments = (size_t)(curveDistances.back() / stepSize);
            break;
        case NUMBER_OF_SEGMENTS:
            numResampledSegments = (size_t)numberOfSegments;
            break;
        default:
            CARB_ASSERT(0);
        }

        numResampledSegments = std::max((size_t)1, numResampledSegments); // need at least one segment

        const size_t original_m = curve.getSegmentCount(controlPoints.size());
        const size_t m = numResampledSegments;
        const size_t n = tessellatedPositions.size();

        if (m >= original_m)
        {
            CARB_LOG_WARN_ONCE("Resampling curve with higher resolution than the input curve is not supported.");
            resampledControlPoints = controlPoints;
            return;
        }

        if (verbose)
        {
            CARB_LOG_INFO("original segment count: %zu", original_m);
            CARB_LOG_INFO("resampling to %zu segments", m);
            CARB_LOG_INFO("tessellation count: %zu", n);
        }

        bool success = fitCubicBezierToPoints(tessellatedPositions, numResampledSegments, resampledControlPoints);

        if (!success)
        {
            resampledControlPoints = controlPoints;
            return;
        }
    }

    static bool compute(OgnResampleCurvesDatabase& db)
    {
        const bool optionsChanged = (db.state.prevMode() != db.inputs.mode()) ||
                                    (db.state.prevStep() != db.inputs.step()) ||
                                    (db.state.prevNumberOfSegments() != db.inputs.numberOfSegments()) ||
                                    (db.state.prevAvoidSharpTurns() != db.inputs.avoidSharpTurns()) ||
                                    (db.state.prevVerbose() != db.inputs.verbose());

        if (!optionsChanged && !db.inputs.curvesBundle.changes().hasChanged())
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        db.outputs.curvesBundle = db.inputs.curvesBundle;
        BundlePrims outputCurvePrims(db.abi_context(), db.outputs.curvesBundle().abi_bundleHandle());
        const size_t curvePrimsCount = outputCurvePrims.getPrimCount();

        // resample curves
        for (size_t primIndex = 0; primIndex < curvePrimsCount; primIndex++)
        {
            BundlePrim* curvePrim = outputCurvePrims.getPrim(primIndex);

            BundleAttrib* pointsAttr = curvePrim->getAttr(db.tokens.points);
            BundleAttrib* curveVertexCountsAttr = curvePrim->getAttr(db.tokens.curveVertexCounts);
            BundleAttrib const* curveBasisAttr = curvePrim->getAttr(db.tokens.basis);
            BundleAttrib const* wrapTypeAttr = curvePrim->getAttr(db.tokens.wrap);

            // Note: it's ok if curveVertexCountsAttr does not exist, in the case of a single curve
            if (pointsAttr == nullptr || curveBasisAttr == nullptr || wrapTypeAttr == nullptr)
            {
                CARB_LOG_WARN("Input prim does not have basis curve attributes.");
                continue;
            }

            const size_t pointsCount = pointsAttr->size();
            if (pointsCount == 0)
            {
                CARB_LOG_WARN("No points in input prim.");
                continue;
            }
            const vec3f* const points = pointsAttr->getData<vec3f>();
            const int* curveVertexCounts =
                curveVertexCountsAttr == nullptr ? nullptr : curveVertexCountsAttr->getData<int>();
            const size_t curveCount = curveVertexCounts == nullptr ? 0 : curveVertexCountsAttr->size();
            const auto* basisToken = curveBasisAttr->getData<omni::graph::core::NameToken>();
            const auto* wrapToken = wrapTypeAttr->getData<omni::graph::core::NameToken>();

            if (points == nullptr || basisToken == nullptr || wrapToken == nullptr)
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

            if (curveBasisType != eBasisCurveType::Bezier)
            {
                CARB_LOG_WARN("Only Bezier curves are currently supported for resampling.");
                continue;
            }

            std::vector<vec3f> resampledCVs;
            std::vector<int> resampledCurveVertexCounts(curveCount == 0 ? 1 : curveCount);

            for (size_t curveIndex = 0, startIndex = 0; curveIndex < (curveCount == 0 ? 1 : curveCount); curveIndex++)
            {
                const size_t count = (curveCount == 0 ? pointsCount : curveVertexCounts[curveIndex]);

                std::vector<vec3f> controlPoints(count);
                memcpy(controlPoints.data(), points + startIndex, count * sizeof(vec3f));
                startIndex += count;

                SplineCurve curve(curveWrapType, curveBasisType);

                std::vector<vec3f> oneCurveResampledCVs;

                resampleCurve(db, curve, controlPoints, oneCurveResampledCVs);

                const size_t offset = resampledCVs.size();
                resampledCVs.resize(offset + oneCurveResampledCVs.size());
                for (size_t i = 0; i < oneCurveResampledCVs.size(); i++)
                {
                    resampledCVs[offset + i] = oneCurveResampledCVs[i];
                }

                resampledCurveVertexCounts[curveIndex] = (int)oneCurveResampledCVs.size();
            }

            pointsAttr->resize(resampledCVs.size());
            vec3f* pointsResampled = pointsAttr->getData<vec3f>();
            CARB_ASSERT(pointsResampled != nullptr);
            memcpy(pointsResampled, resampledCVs.data(), resampledCVs.size() * sizeof(vec3f));

            if (curveVertexCountsAttr)
            {
                curveVertexCountsAttr->resize(resampledCurveVertexCounts.size());
                int* curveVertexCountsResampled = curveVertexCountsAttr->getData<int>();
                CARB_ASSERT(curveVertexCountsResampled != nullptr);
                memcpy(curveVertexCountsResampled, resampledCurveVertexCounts.data(),
                       resampledCurveVertexCounts.size() * sizeof(int));
            }
        }

        db.state.prevMode() = db.inputs.mode();
        db.state.prevStep() = db.inputs.step();
        db.state.prevNumberOfSegments() = db.inputs.numberOfSegments();
        db.state.prevAvoidSharpTurns() = db.inputs.avoidSharpTurns();
        db.state.prevVerbose() = db.inputs.verbose();

        return true;
    }
};

REGISTER_OGN_NODE()

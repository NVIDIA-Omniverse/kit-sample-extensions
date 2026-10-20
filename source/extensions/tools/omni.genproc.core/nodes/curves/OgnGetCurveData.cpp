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
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/ramp/IRamp.h>

#include <OgnGetCurveDataDatabase.h>
#include <algorithm>
#include <cmath>

static omni::ramp::IRamp* s_iRamp = nullptr;

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::geometry::curves;
using namespace omni::genproc;

class OgnGetCurveData
{
public:
    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
        s_iRamp = carb::getFramework()->acquireInterface<omni::ramp::IRamp>();
    }

    static bool compute(OgnGetCurveDataDatabase& db)
    {
        ConstBundlePrims curvePrims(db.abi_context(), db.inputs.curvesBundle().abi_bundleHandle());
        const size_t curvePrimCount = curvePrims.getPrimCount();

        const bool inputsChanged = (db.state.prevSamplesPerSegment() != db.inputs.samplesPerSegment()) ||
                                   (db.state.prevRampPositionsName() != db.inputs.rampPositionsName()) ||
                                   (db.state.prevRampValuesName() != db.inputs.rampValuesName()) ||
                                   (db.state.prevRampInterpolationsName() != db.inputs.rampInterpolationsName()) ||
                                   (db.state.prevRampTagsName() != db.inputs.rampTagsName()) ||
                                   db.inputs.curvesBundle.changes().hasChanged();

        if (!inputsChanged)
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        bool foundCurve = false;

        std::vector<vec3f> tessellatedPositions, tessellatedTangents;
        std::vector<float> uValues;

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

            const size_t samplesPerSegment = (size_t)std::max(1, db.inputs.samplesPerSegment());
            const bool normalizeLengths = true;
            const std::vector<float> curveDistances = approximateDistanceAlongCurve(
                *curve, *controlPoints, normalizeLengths, samplesPerSegment, &tessellatedPositions, &tessellatedTangents);
            const size_t segmentCount = curve->getSegmentCount(controlPoints->size());
            std::vector<float> segmentDistances(segmentCount); // TODO: cache these distances in node state until bundle
                                                               // prim dirty ID changes
            std::vector<float> perSegmentDistance(segmentCount); // TODO: better name for this
            for (size_t i = 0; i < segmentCount; i++)
            {
                const size_t lastOffset = (i == segmentCount - 1 ? 1 : 0);
                segmentDistances[i] = curveDistances[(i + 1) * samplesPerSegment + lastOffset - 1];

                perSegmentDistance[i] = segmentDistances[i] - (i == 0 ? 0 : segmentDistances[i - 1]);
            }

            CARB_ASSERT(tessellatedPositions.size() == segmentCount * samplesPerSegment + 1);
            uValues.resize(tessellatedPositions.size());
            for (size_t i = 0; i < uValues.size() - 1; i++) // note: skipping last element
            {
                size_t segmentIndex = i / samplesPerSegment;
                float fractionWithinSegment = (float)(i - samplesPerSegment * segmentIndex) / (float)samplesPerSegment;
                float startU = (segmentIndex == 0 ? 0.f : segmentDistances[segmentIndex - 1]);
                uValues[i] = startU + fractionWithinSegment * perSegmentDistance[segmentIndex];
            }
            uValues.back() = 1.f;

            foundCurve = true;
        };

        processCurvesInBundle(curvePrims, processingOp);

        const NameToken rampPositionsName = db.inputs.rampPositionsName();
        const NameToken rampValuesName = db.inputs.rampValuesName();
        const NameToken rampInterpolationsName = db.inputs.rampInterpolationsName();
        const NameToken rampTagsName = db.inputs.rampTagsName();

        ConstBundlePrim& commonAttrs = curvePrims.getConstCommonAttrs();
        BundleAttrib const* rampPositionsAttr = commonAttrs.getConstAttr(rampPositionsName);
        BundleAttrib const* rampValuesAttr = commonAttrs.getConstAttr(rampValuesName);
        BundleAttrib const* rampInterpolationsAttr = commonAttrs.getConstAttr(rampInterpolationsName);
        BundleAttrib const* rampTagsAttr = commonAttrs.getConstAttr(rampTagsName);

        size_t rampKeyCount = 0, rampTagsCount = 0;

        const float *rampPositions = nullptr, *rampValues = nullptr;
        const int* rampInterpolations = nullptr;
        const NameToken* rampTags = nullptr;

        bool hasRamp = rampPositionsAttr != nullptr && rampValuesAttr != nullptr && rampInterpolationsAttr != nullptr &&
                       rampTagsAttr != nullptr;

        if (hasRamp)
        {
            rampKeyCount = rampPositionsAttr->size();
            rampTagsCount = rampTagsAttr->size();

            hasRamp = hasRamp && rampKeyCount != 0 && rampTagsCount != 0 && rampKeyCount == rampValuesAttr->size() &&
                      rampKeyCount == rampInterpolationsAttr->size();
        }

        if (hasRamp)
        {
            rampPositions = rampPositionsAttr->getData<float>();
            rampValues = rampValuesAttr->getData<float>();
            rampInterpolations = rampInterpolationsAttr->getData<int>();
            rampTags = rampTagsAttr->getData<NameToken>();

            hasRamp = hasRamp && rampPositions != nullptr && rampValues != nullptr && rampInterpolations != nullptr &&
                      rampTags != nullptr;
        }

        std::vector<NameToken> tags(uValues.size());
        if (foundCurve && hasRamp)
        {
            std::vector<float> animationValues(uValues.size());
            s_iRamp->sampleFloatArray(uValues.size(), animationValues.data(), uValues.data(), 0, rampKeyCount,
                                      rampPositions, rampValues, rampInterpolations);
            std::vector<NameToken> tagOptions(rampTagsCount);
            for (size_t i = 0; i < rampTagsCount; i++)
            {
                tagOptions[i] = NameToken(rampTags[i]);
            }
            for (size_t i = 0; i < tags.size(); i++)
            {
                const float minValue = 0.f;
                const float maxValue = 1.f;
                const size_t tagIndex = std::min(
                    rampTagsCount - 1, (size_t)((animationValues[i] - minValue) / (maxValue - minValue) * rampTagsCount));
                tags[i] = tagOptions[tagIndex];
            }
        }

        if (foundCurve)
        {
            auto& pointsOut = db.outputs.points();
            auto& tangentsOut = db.outputs.tangents();
            auto& uValuesOut = db.outputs.uValues();
            auto& tagsOut = db.outputs.tags();

            pointsOut.resize(tessellatedPositions.size());
            tangentsOut.resize(tessellatedTangents.size());
            uValuesOut.resize(uValues.size());
            tagsOut.resize(hasRamp ? tags.size() : 0);

            memcpy(pointsOut.data(), tessellatedPositions.data(), tessellatedPositions.size() * sizeof(vec3f));
            memcpy(tangentsOut.data(), tessellatedTangents.data(), tessellatedTangents.size() * sizeof(vec3f));
            memcpy(uValuesOut.data(), uValues.data(), uValues.size() * sizeof(float));
            if (hasRamp)
            {
                memcpy(tagsOut.data(), tags.data(), tags.size() * sizeof(NameToken));
            }
        }
        else
        {
            CARB_LOG_ERROR("GetCurveData: Failed to find prim in input bundle with necessary curve attributes.");
            return false;
        }

        db.state.prevSamplesPerSegment() = db.inputs.samplesPerSegment();
        db.state.prevRampPositionsName() = db.inputs.rampPositionsName();
        db.state.prevRampValuesName() = db.inputs.rampValuesName();
        db.state.prevRampInterpolationsName() = db.inputs.rampInterpolationsName();
        db.state.prevRampTagsName() = db.inputs.rampTagsName();

        return true;
    }
};

REGISTER_OGN_NODE()

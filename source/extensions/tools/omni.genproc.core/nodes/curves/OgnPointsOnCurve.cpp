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
#include "../plugins/PhysXUtils.h"
#include "../plugins/Scatter.h"

#include <omni/fabric/IFabric.h>
#include <omni/fabric/Type.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/timeline/ITimeline.h>
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

#include <OgnPointsOnCurveDatabase.h>
#include <algorithm>
#include <random>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::geometry::curves;
using namespace omni::genproc;

class OgnPointsOnCurve
{
    double m_cumulativeTime;

public:
    enum Mode : size_t
    {
        INPUT_ARRAY = 0,
        RANDOM_ARRAY,
        NUM_MODES
    };

    static void getUValues(OgnPointsOnCurveDatabase& db, std::vector<float>& /*out*/ uValues)
    {
        std::mt19937_64 random;

        if (db.inputs.timeBasedSeed())
        {
            static omni::timeline::ITimeline* iTimeline = carb::getCachedInterface<omni::timeline::ITimeline>();
            auto timeline = iTimeline->getTimeline();
            double time;
            if (timeline->isPlaying())
            {
                // If we want time-based randomness, but we're playing the timeline,
                // we'll make the time-based seed consistent between timeline runs...
                time = timeline->getCurrentTime();
            }
            else
            {
                // ... but if we want time-based randomness without playing the timeline,
                // we'll just accumulate a running sum. It doesn't really matter what it
                // is; we're gonna cast it to a uint in a second anyway.

                auto& internalState = db.internalState<OgnPointsOnCurve>();
                auto& context = db.abi_context();
                const float dt = context.iContext->getElapsedTime(context);
                internalState.m_cumulativeTime += dt;
                time = internalState.m_cumulativeTime;
            }
            uint64_t timeInt = reinterpret_cast<uint64_t&>(time);
            random.seed(db.inputs.randomSeed() ^ timeInt);
        }
        else
        {
            random.seed(db.inputs.randomSeed());
        }

        const size_t numberOfSamples = (size_t)(std::max(0, db.inputs.numberOfPoints()));
        uValues.resize(numberOfSamples);
        for (size_t i = 0; i < numberOfSamples; i++)
        {
            uValues[i] = randomFloatBetween(random, 0.f, 1.f);
        }
    }

    static void initialize(const GraphContextObj& context, const NodeObj& nodeObj)
    {
        auto& internalState = OgnPointsOnCurveDatabase::sInternalState<OgnPointsOnCurve>(nodeObj);
        internalState.m_cumulativeTime = 0.;
    }

    static bool compute(OgnPointsOnCurveDatabase& db)
    {
        const auto& uValuesIn = db.inputs.uValues();
        size_t uValuesCount = uValuesIn.size();

        bool optionsChanged = db.state.prevUValues().size() != uValuesCount ||
                              db.state.prevSamplingMode() != db.inputs.samplingMode() ||
                              db.state.prevTimeBasedSeed() != db.inputs.timeBasedSeed() ||
                              db.state.prevRandomSeed() != db.inputs.randomSeed() ||
                              db.state.prevNumberOfPoints() != db.inputs.numberOfPoints();
        optionsChanged =
            optionsChanged || !std::equal(uValuesIn.begin(), uValuesIn.end(), db.state.prevUValues().begin());
        optionsChanged = optionsChanged || db.inputs.curvesBundle.changes().hasChanged();

        Mode samplingMode = Mode(db.inputs.samplingMode());
        if (samplingMode < Mode(0))
            samplingMode = Mode(0);
        if (samplingMode >= NUM_MODES)
            samplingMode = Mode(NUM_MODES - 1);

        // If we're sampling random values and reseeding based on time, we need to recompute
        // every frame even if no options have changed.
        const bool needsUpdate = (samplingMode == RANDOM_ARRAY && db.inputs.timeBasedSeed());

        if (!optionsChanged && !needsUpdate)
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        ConstBundlePrims curvePrims(db.abi_context(), db.inputs.curvesBundle().abi_bundleHandle());

        std::vector<float> uValues;

        if (samplingMode == INPUT_ARRAY)
        {
            uValues.resize(uValuesCount);
            const float* uValuesData = uValuesIn.data();
            for (size_t i = 0; i < uValuesCount; i++)
            {
                uValues[i] = uValuesData[i];
            }
        }
        else // RANDOM_ARRAY
        {
            getUValues(db, uValues);
        }

        std::vector<vec3f> pointsOnCurve, tangentsAtPoint;

        const bool foundCurve = samplePointsOnCurve(curvePrims, uValues, pointsOnCurve, tangentsAtPoint);

        if (foundCurve)
        {
            auto& pointsOut = db.outputs.points();
            auto& tangentsOut = db.outputs.tangents();

            pointsOut.resize(pointsOnCurve.size());
            tangentsOut.resize(tangentsAtPoint.size());

            memcpy(pointsOut.data(), pointsOnCurve.data(), pointsOnCurve.size() * sizeof(vec3f));
            memcpy(tangentsOut.data(), tangentsAtPoint.data(), tangentsAtPoint.size() * sizeof(vec3f));
        }
        else
        {
            CARB_LOG_ERROR("PointsOnCurve: Failed to find prim in input bundle with necessary curve attributes.");
            return false;
        }

        db.state.prevUValues() = db.inputs.uValues();
        db.state.prevSamplingMode() = db.inputs.samplingMode();
        db.state.prevTimeBasedSeed() = db.inputs.timeBasedSeed();
        db.state.prevRandomSeed() = db.inputs.randomSeed();
        db.state.prevNumberOfPoints() = db.inputs.numberOfPoints();

        return true;
    }
};

REGISTER_OGN_NODE()

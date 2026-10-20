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

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/vec.h>

#include <OgnOrderPointsByDistanceDatabase.h>
#include <algorithm>
#include <numeric>

using omni::math::linalg::vec3f;

class OgnOrderPointsByDistance
{
public:
    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
    }

    static bool compute(OgnOrderPointsByDistanceDatabase& db)
    {
        const vec3f& referencePoint = db.inputs.point();
        const auto& pointsIn = db.inputs.points();

        const size_t pointsCount = pointsIn.size();

        bool inputsChanged = (db.inputs.point() != db.state.prevPoint()) || (pointsCount != db.state.prevPoints().size());
        inputsChanged = inputsChanged || !std::equal(pointsIn.begin(), pointsIn.end(), db.state.prevPoints().begin());

        if (!inputsChanged)
        {
            return true;
        }

        auto& pointsOut = db.outputs.points();
        pointsOut.resize(pointsCount);

        if (pointsCount == 0)
        {
            return true;
        }

        const vec3f* points = pointsIn.data();

        std::vector<size_t> indices(pointsCount);
        std::iota(indices.begin(), indices.end(), 0);

        std::vector<float> distancesSquared(pointsCount);
        for (size_t i = 0; i < pointsCount; i++)
        {
            distancesSquared[i] = (points[i] - referencePoint).GetLengthSq();
        }

        std::sort(indices.begin(), indices.end(),
                  [&distancesSquared](const size_t i, const size_t j)
                  { return distancesSquared[i] < distancesSquared[j]; });

        std::transform(indices.begin(), indices.end(), pointsOut.data(), [&points](const size_t i) { return points[i]; });

        db.state.prevPoint() = db.inputs.point();
        db.state.prevPoints() = db.inputs.points();

        return true;
    }
};

REGISTER_OGN_NODE()

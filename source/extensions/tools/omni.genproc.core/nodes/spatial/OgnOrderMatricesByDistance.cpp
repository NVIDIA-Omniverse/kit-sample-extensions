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

#include <carb/settings/ISettings.h>

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>

#include <OgnOrderMatricesByDistanceDatabase.h>
#include <algorithm>
#include <numeric>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3d;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

class OgnOrderMatricesByDistance
{
public:
    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
    }

    static bool compute(OgnOrderMatricesByDistanceDatabase& db)
    {
        const vec3d referencePoint = vec3d(db.inputs.point());
        const auto& matricesIn = db.inputs.matrices();

        const size_t matricesCount = matricesIn.size();

        bool inputsChanged =
            (db.inputs.point() != db.state.prevPoint()) || (matricesCount != db.state.prevMatrices().size());
        if (!inputsChanged)
        {
            inputsChanged =
                inputsChanged || !std::equal(matricesIn.begin(), matricesIn.end(), db.state.prevMatrices().begin());
        }

        if (!inputsChanged)
        {
            return true;
        }

        auto& matricesOut = db.outputs.matrices();
        matricesOut.resize(matricesCount);

        if (matricesCount == 0)
        {
            return true;
        }

        const matrix4d* matrices = matricesIn.data();

        std::vector<size_t> indices(matricesCount);
        std::iota(indices.begin(), indices.end(), 0);

        std::vector<double> distancesSquared(matricesCount);
        for (size_t i = 0; i < matricesCount; i++)
        {
            distancesSquared[i] = (matrices[i].ExtractTranslation() - referencePoint).GetLengthSq();
        }

        std::sort(indices.begin(), indices.end(),
                  [&distancesSquared](const size_t i, const size_t j)
                  { return distancesSquared[i] < distancesSquared[j]; });

        std::transform(
            indices.begin(), indices.end(), matricesOut.data(), [&matrices](const size_t i) { return matrices[i]; });

        db.state.prevPoint() = db.inputs.point();
        db.state.prevMatrices() = db.inputs.matrices();

        return true;
    }
};

REGISTER_OGN_NODE()

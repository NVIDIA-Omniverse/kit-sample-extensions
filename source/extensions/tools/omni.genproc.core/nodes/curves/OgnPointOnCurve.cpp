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
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

#include <OgnPointOnCurveDatabase.h>
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

class OgnPointOnCurve
{
public:
    static bool compute(OgnPointOnCurveDatabase& db)
    {
        const bool optionsChanged =
            db.state.prevUValue() != db.inputs.uValue() || db.inputs.curvesBundle.changes().hasChanged();

        if (!optionsChanged)
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        ConstBundlePrims curvePrims(db.abi_context(), db.inputs.curvesBundle().abi_bundleHandle());

        std::vector<float> uValues = { db.inputs.uValue() };
        std::vector<vec3f> pointsOnCurve, tangentsAtPoint;

        bool foundCurve = samplePointsOnCurve(curvePrims, uValues, pointsOnCurve, tangentsAtPoint);

        if (foundCurve)
        {
            CARB_ASSERT(pointsOnCurve.size() == 1 && tangentsAtPoint.size() == 1);

            db.outputs.point() = pointsOnCurve[0];
            db.outputs.tangent() = tangentsAtPoint[0];
        }
        else
        {
            CARB_LOG_ERROR("PointOnCurve: Failed to find prim in input bundle with necessary curve attributes.");
            return false;
        }

        db.state.prevUValue() = db.inputs.uValue();

        return true;
    }
};

REGISTER_OGN_NODE()

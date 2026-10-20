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

#include "../plugins/PhysXUtils.h"
#include "../plugins/Utils.h"

#include <carb/settings/ISettings.h>

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/quat.h>
#include <omni/math/linalg/vec.h>
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

#include <OgnOrderPrimsByDistanceDatabase.h>
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <random>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::genproc;

class OgnOrderPrimsByDistance
{
public:
    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
    }

    static bool compute(OgnOrderPrimsByDistanceDatabase& db)
    {
        auto& context = db.abi_context();

        ConstBundlePrims inputPrims(db.abi_context(), db.inputs.bundle().abi_bundleHandle());
        const size_t primCount = inputPrims.getPrimCount();

        const bool optionsChanged =
            db.state.prevPoint() != db.inputs.point() || db.state.prevVerbose() != db.inputs.verbose();

        if (!optionsChanged && !db.inputs.bundle.changes().hasChanged())
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        const bool& verbose = db.inputs.verbose();

        BundlePrims outputPrims(db.abi_context(), db.outputs.bundle().abi_bundleHandle());
        outputPrims.clearContents();

        if (primCount == 0)
        {
            return true;
        }

        const vec3f& referencePoint = db.inputs.point();

        std::vector<size_t> indices(primCount);
        std::iota(indices.begin(), indices.end(), 0);

        std::vector<float> distancesSquared(primCount);
        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            UniquePhysXPtr<physx::PxTriangleMesh> triMesh;

            std::vector<vec3f> trianglePoints;
            std::vector<int> triangleIndices;

            bool success = primInBundleToTriangles(inputPrims, primIndex, trianglePoints, triangleIndices);

            if (!success)
            {
                if (verbose)
                {
                    CARB_LOG_WARN("Failed to triangulate prim: %s. Skipping...",
                                  db.tokenToString(inputPrims.getPrim(primIndex)->path()));
                }
                distancesSquared[primIndex] = std::numeric_limits<float>::max();
                continue;
            }

            triPointsToPxTriangleMesh(
                trianglePoints.data(), trianglePoints.size(), triangleIndices.data(), triangleIndices.size(), triMesh);

            physx::PxTriangleMeshGeometry triMeshGeometry(triMesh.get());

            vec3f closestPoint;
            bool hasClosest = getMeshClosestPoint(referencePoint, triMeshGeometry, closestPoint);

            if (!hasClosest)
            {
                if (verbose)
                {
                    CARB_LOG_WARN("Failed closest point query against prim: %s. Skipping...",
                                  db.tokenToString(inputPrims.getPrim(primIndex)->path()));
                }
                distancesSquared[primIndex] = std::numeric_limits<float>::max();
                continue;
            }

            distancesSquared[primIndex] = (closestPoint - referencePoint).GetLengthSq();
        }

        std::sort(indices.begin(), indices.end(),
                  [&distancesSquared](const size_t i, const size_t j)
                  { return distancesSquared[i] < distancesSquared[j]; });

        outputPrims.addPrims(primCount);
        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            BundlePrim* outputPrim = outputPrims.getPrim(primIndex);
            ConstBundlePrim* inputPrim = inputPrims.getConstPrim(indices[primIndex]);
            outputPrim->copyContentsFrom(*inputPrim); // NOTE: this doesn't set prim's path...
            outputPrim->setPath(inputPrim->path());
        }

        if (verbose)
        {
            for (size_t primIndex = 0; primIndex < primCount; primIndex++)
            {
                ConstBundlePrim* outputPrim = outputPrims.getConstPrim(primIndex);
                CARB_LOG_INFO("Sorted prim %zu: %s", primIndex, db.tokenToString(outputPrim->path()));
            }
        }

        db.state.prevPoint() = db.inputs.point();
        db.state.prevVerbose() = db.inputs.verbose();

        return true;
    }
};

REGISTER_OGN_NODE()

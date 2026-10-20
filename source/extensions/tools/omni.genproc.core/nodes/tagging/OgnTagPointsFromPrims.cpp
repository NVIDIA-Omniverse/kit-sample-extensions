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

#include "../plugins/PhysXUtils.h"
#include "../plugins/Utils.h"

#include <carb/settings/ISettings.h>

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <physx/include/geometry/PxTriangleMeshGeometry.h>

#include <OgnTagPointsFromPrimsDatabase.h>
#include <algorithm>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::genproc;

class OgnTagPointsFromPrims
{
public:
    static bool compute(OgnTagPointsFromPrimsDatabase& db)
    {
        auto& context = db.abi_context();

        const auto& pointsIn = db.inputs.points();
        const size_t pointsCount = pointsIn.size();

        bool inputsChanged = (db.state.prevTagName() != db.inputs.tagName()) ||
                             (db.state.prevDefaultTag() != db.inputs.defaultTag()) ||
                             (db.state.prevPoints().size() != pointsCount) || db.inputs.bundle.changes().hasChanged();

        inputsChanged = inputsChanged || !std::equal(pointsIn.begin(), pointsIn.end(), db.state.prevPoints().begin());

        if (!inputsChanged)
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        ConstBundlePrims inputPrims(db.abi_context(), db.inputs.bundle().abi_bundleHandle());
        const size_t primCount = inputPrims.getPrimCount();

        const NameToken defaultTag = db.inputs.defaultTag();
        const NameToken tagName = db.inputs.tagName();
        const vec3f* points = pointsIn.data();

        std::vector<bool> validPrim(primCount);
        std::vector<UniquePhysXPtr<physx::PxTriangleMesh>> triMeshes(primCount);
        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            std::vector<vec3f> points;
            std::vector<int> indices;

            validPrim[primIndex] = primInBundleToTriangles(inputPrims, primIndex, points, indices);

            if (validPrim[primIndex])
            {
                triPointsToPxTriangleMesh(
                    points.data(), points.size(), indices.data(), indices.size(), triMeshes[primIndex]);
            }
        }

        std::vector<NameToken> primTags(primCount);
        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            ConstBundlePrim* prim = inputPrims.getConstPrim(primIndex);
            BundleAttrib const* tagAttr = prim->getConstAttr(tagName);

            if (tagAttr == nullptr)
            {
                validPrim[primIndex] = false;
                continue;
            }

            const auto* tagToken = tagAttr->getData<NameToken>();
            if (tagToken == nullptr)
            {
                validPrim[primIndex] = false;
                continue;
            }

            primTags[primIndex] = *tagToken;
        }

        auto& tagsOut = db.outputs.tags();
        tagsOut.resize(pointsCount);
        NameToken* tags = tagsOut.data();

        for (size_t i = 0; i < pointsCount; i++)
        {
            tags[i] = defaultTag;
        }

        // Note that we're not doing anything smart in the case where a point is inside multiple prims.
        // We're just taking the tag of the first enclosing prim we find.
        for (size_t i = 0; i < pointsCount; i++)
        {
            for (size_t primIndex = 0; primIndex < primCount; primIndex++)
            {
                if (!validPrim[primIndex])
                {
                    continue;
                }

                if (pointInsideMesh(points[i], physx::PxTriangleMeshGeometry(triMeshes[primIndex].get())))
                {
                    tags[i] = primTags[primIndex];
                    continue;
                }
            }
        }

        // for (size_t i = 0; i < pointsCount; i++)
        //{
        //    std::cout<<"tag "<<i<<": "<<iToken->getText(tags[i])<<std::endl;
        //}

        db.state.prevPoints() = db.inputs.points();
        db.state.prevTagName() = db.inputs.tagName();
        db.state.prevDefaultTag() = db.inputs.defaultTag();

        return true;
    }
};

REGISTER_OGN_NODE()

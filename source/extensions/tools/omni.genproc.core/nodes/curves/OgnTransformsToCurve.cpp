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

#include "Utils.h"

#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>

#include <OgnTransformsToCurveDatabase.h>
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

class OgnTransformsToCurve
{
public:
    enum Basis : size_t
    {
        BEZIER = 0,
        BSPLINE,
        CATMULL_ROM,
        NUM_BASIS
    };

    enum Wrap : size_t
    {
        NONPERIODIC = 0,
        PERIODIC,
        PINNED,
        NUM_WRAP
    };

    enum CurveType : size_t
    {
        LINEAR = 0,
        CUBIC = 1,
        NUM_CURVE_TYPE
    };

    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
    }

    static void writeToOutput(OgnTransformsToCurveDatabase& db,
                              const std::vector<std::pair<vec3f, vec3f>>& curveEndpoints,
                              const std::vector<vec3f>& curveDirections)
    {
    }

    static bool compute(OgnTransformsToCurveDatabase& db)
    {
        CARB_LOG_WARN_ONCE(
            "TransformsToCurve -- If the input to this node is from a ReadPrimsV2 node, input prims may be out of order.");

        auto& nodeObj = db.abi_node();
        auto& context = db.abi_context();

        const auto* const iContext = context.iContext;
        const auto* const iBundle = context.iBundle;
        const auto* const iAttributeData = context.iAttributeData;

        static const auto opacityToken = NameToken("primvars:displayOpacity");

        const bool optionsChanged =
            (db.state.prevBasis() != db.inputs.basis()) || (db.state.prevWrap() != db.inputs.wrap()) ||
            (db.state.prevType() != db.inputs.type()) || (db.state.prevTangentLength() != db.inputs.tangentLength());

        if (!optionsChanged && !db.inputs.transformBundle.changes().hasChanged())
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        ConstBundlePrims transformPrims(db.abi_context(), db.inputs.transformBundle().abi_bundleHandle());
        const size_t transformPrimCount = transformPrims.getPrimCount();

        std::vector<matrix4d> transforms;
        getPrimTransforms(transformPrims, transforms); // it's overkill to get all the xforms only to use one...

        Basis basis = Basis(db.inputs.basis());
        if (basis < Basis(0))
            basis = Basis(0);
        if (basis >= NUM_BASIS)
            basis = Basis(NUM_BASIS - 1);

        Wrap wrap = Wrap(db.inputs.wrap());
        if (wrap < Wrap(0))
            wrap = Wrap(0);
        if (wrap >= NUM_WRAP)
            wrap = Wrap(NUM_WRAP - 1);


        CurveType type = CurveType(db.inputs.type());
        if (type < CurveType(0))
            type = CurveType(0);
        if (type >= NUM_CURVE_TYPE)
            type = CurveType(NUM_CURVE_TYPE - 1);

        const float& tangentLength = db.inputs.tangentLength();

        ConstBundlePrim& transformCommonAttrs = transformPrims.getConstCommonAttrs();

        // Optional opacity
        BundleAttrib const* inputOpacityAttr = transformCommonAttrs.getConstAttr(opacityToken);
        const float* opacityData = nullptr;
        if (inputOpacityAttr != nullptr && inputOpacityAttr->size() == transformPrimCount)
        {
            opacityData = inputOpacityAttr->getData<float>();
        }

        // Optional travelling
        BundleAttrib const* inputTravellingAttr = transformCommonAttrs.getConstAttr(db.tokens.travelling);
        const double* travellingData = nullptr;
        if (inputTravellingAttr != nullptr && inputTravellingAttr->size() == transformPrimCount)
        {
            travellingData = inputTravellingAttr->getData<double>();
        }

        // The first and last transform will contribute one CV and one tangent;
        // all other transform will contribute one CV and two tangents
        const size_t pointsCount = 3 * transformPrimCount - 2;

        BundlePrims curvePrims(db.abi_context(), db.outputs.curveBundle().abi_bundleHandle());

        if (curvePrims.getPrimCount() == 0)
        {
            curvePrims.addPrims(1);
        }

        BundlePrim* curvePrim = curvePrims.getPrim(0);

        BundleAttrib* basisAttr =
            curvePrim->addAttr(db.tokens.basis, Type(BaseDataType::eToken, 1, 0, AttributeRole::eNone), 0);
        NameToken* basisToken = basisAttr->getData<NameToken>();
        CARB_ASSERT(basisToken != nullptr);
        switch (basis)
        {
        case BEZIER:
            *basisToken = db.tokens.bezier;
            break;
        case BSPLINE:
            *basisToken = db.tokens.bspline;
            break;
        case CATMULL_ROM:
            *basisToken = db.tokens.catmullRom;
            break;
        default:
            CARB_ASSERT(0);
        }

        BundleAttrib* wrapAttr =
            curvePrim->addAttr(db.tokens.wrap, Type(BaseDataType::eToken, 1, 0, AttributeRole::eNone), 0);
        NameToken* wrapToken = wrapAttr->getData<NameToken>();
        CARB_ASSERT(wrapToken != nullptr);
        switch (wrap)
        {
        case NONPERIODIC:
            *wrapToken = db.tokens.nonperiodic;
            break;
        case PERIODIC:
            *wrapToken = db.tokens.periodic;
            break;
        case PINNED:
            *wrapToken = db.tokens.pinned;
            break;
        default:
            CARB_ASSERT(0);
        }

        BundleAttrib* typeAttr =
            curvePrim->addAttr(db.tokens.type, Type(BaseDataType::eToken, 1, 0, AttributeRole::eNone), 0);
        NameToken* typeToken = typeAttr->getData<NameToken>();
        CARB_ASSERT(typeToken != nullptr);
        switch (type)
        {
        case LINEAR:
            *typeToken = db.tokens.linear;
            break;
        case CUBIC:
            *typeToken = db.tokens.cubic;
            break;
        default:
            CARB_ASSERT(0);
        }

        BundleAttrib* pointsAttr = curvePrim->addAttr(
            db.tokens.points, Type(BaseDataType::eFloat, 3, 1, AttributeRole::ePosition), pointsCount);
        vec3f* points = pointsAttr->getData<vec3f>();
        CARB_ASSERT(points != nullptr);

        float* opacities = nullptr;
        if (opacityData)
        {
            BundleAttrib* outputOpacityAttr =
                curvePrim->addAttr(opacityToken, Type(BaseDataType::eFloat, 1, 1, AttributeRole::eNone), pointsCount);
            opacities = outputOpacityAttr->getData<float>();
        }
        double* travellings = nullptr;
        if (travellingData)
        {
            BundleAttrib* outputTravellingAttr = curvePrim->addAttr(
                db.tokens.travelling, Type(BaseDataType::eDouble, 1, 1, AttributeRole::eNone), pointsCount);
            travellings = outputTravellingAttr->getData<double>();
        }

        BundleAttrib* vertexCountsAttr =
            curvePrim->addAttr(db.tokens.curveVertexCounts, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone), 1);
        int* vertexCounts = vertexCountsAttr->getData<int>();
        CARB_ASSERT(vertexCounts != nullptr);

        vertexCounts[0] = (int)pointsCount; // just one curve

        const vec3f z_axis(0, 0, 1); // TODO: make variable

        for (size_t i = 0; i < transformPrimCount; i++)
        {
            const matrix4d& transform = transforms[i];

            const size_t t0 = 3 * i - 1;
            const size_t cv = 3 * i - 1 + 1;
            const size_t t1 = 3 * i - 1 + 2;

            points[cv] = vec3f(transform.ExtractTranslation());

            if (i > 0)
            {
                points[t0] = points[cv] - tangentLength * transform.TransformDir(z_axis);
            }

            if (i < transformPrimCount - 1)
            {
                points[t1] = points[cv] + tangentLength * transform.TransformDir(z_axis);
            }

            if (opacityData != nullptr && opacities != nullptr)
            {
                opacities[cv] = opacityData[i];
                if (i > 0)
                {
                    opacities[t0] = opacityData[i];
                }
                if (i < transformPrimCount - 1)
                {
                    opacities[t1] = opacityData[i];
                }
            }

            if (travellingData != nullptr && travellings != nullptr)
            {
                travellings[cv] = travellingData[i];
                if (i > 0)
                {
                    travellings[t0] = travellingData[i];
                }
                if (i < transformPrimCount - 1)
                {
                    travellings[t1] = travellingData[i];
                }
            }
        }

        db.state.prevBasis() = db.inputs.basis();
        db.state.prevWrap() = db.inputs.wrap();
        db.state.prevType() = db.inputs.type();
        db.state.prevTangentLength() = db.inputs.tangentLength();

        return true;
    }
};

REGISTER_OGN_NODE()

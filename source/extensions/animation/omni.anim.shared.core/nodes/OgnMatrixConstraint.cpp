// Copyright (c) 2020-2023, NVIDIA CORPORATION. All rights reserved.
//
// NVIDIA CORPORATION and its licensors retain all intellectual property
// and proprietary rights in and to this software, related documentation
// and any modifications thereto. Any use, reproduction, disclosure or
// distribution of this software and related documentation without an express
// license agreement from NVIDIA CORPORATION is strictly prohibited.
//

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include "OgnMatrixConstraintDatabase.h"

#include <carb/logging/Log.h>

#include <omni/graph/core/NodeTypeRegistrar.h>
#include <omni/graph/core/iComputeGraph.h>
#include <omni/usd/UsdContext.h>
#include <omni/usd/UsdUtils.h>

using namespace omni::graph::core;
using namespace pxr;

// This is a node to set the world space transform for a prim specified by relationship target
// to the compute node.
//
// inputs:prim - UsdRelationship, specifies a usd prim from which we set the transform matrix
class OgnMatrixConstraint
{
    static UsdStageWeakPtr getUsdStage(OgnMatrixConstraintDatabase& db)
    {
        auto& context = db.abi_context();
        auto iContext = context.iContext;
        long int stageId = iContext->getStageId(context);
        auto usdStage = pxr::UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
        return usdStage;
    }

public:
    // copy computed data back to usd prim
    static bool compute(OgnMatrixConstraintDatabase& db)
    {
        pxr::UsdGeomXformable xformable = getXformable(db);
        if (!xformable)
        {
            CARB_LOG_WARN("%s is not Xformable", db.inputs.prim.path().c_str());
            return true;
        }

        const pxr::GfMatrix4d transform = db.inputs.transform();
        pxr::UsdTimeCode timeCode(db.inputs.usdTimecode());
        omni::usd::UsdUtils::setLocalTransformFromWorldTransformMatrix(xformable.GetPrim(), transform, timeCode);
        return true;
    }

    static UsdGeomXformable getXformable(OgnMatrixConstraintDatabase& db)
    {
        auto stage = getUsdStage(db);

        const SdfPath primPath(db.inputs.prim.path());
        UsdPrim prim = stage->GetPrimAtPath(primPath);
        UsdGeomXformable xformable(prim);
        return xformable;
    }
};

REGISTER_OGN_NODE()

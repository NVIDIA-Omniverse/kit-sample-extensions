// Copyright (c) 2021-2023, NVIDIA CORPORATION. All rights reserved.
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

#include <carb/Framework.h>
#include <carb/Types.h>
#include <carb/logging/Log.h>

#include <omni/graph/core/ogn/Types.h>
#include <omni/usd/UsdContext.h>
#include <omni/usd/UsdUtils.h>

#include <OgnGetJointXformDatabase.h>


using namespace pxr;
using namespace carb;

using omni::graph::core::BaseDataType;
using omni::graph::core::NameToken;
using omni::graph::core::Type;

class OgnGetJointXform
{
private:
    static void setOutputIdentity(OgnGetJointXformDatabase& db)
    {
        pxr::GfMatrix4d I;
        I.SetIdentity();
        db.outputs.transform() = I;
    }

    static UsdStageWeakPtr getUsdStage(OgnGetJointXformDatabase& db)
    {
        auto& context = db.abi_context();
        auto iContext = context.iContext;
        long int stageId = iContext->getStageId(context);
        auto usdStage = pxr::UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
        return usdStage;
    }

    static UsdGeomXformable getXformable(OgnGetJointXformDatabase& db)
    {
        auto stage = getUsdStage(db);
        const SdfPath primPath(db.inputs.prim.path());
        UsdPrim prim = stage->GetPrimAtPath(primPath);
        UsdGeomXformable xformable(prim);
        return xformable;
    }

public:
    static bool compute(OgnGetJointXformDatabase& db)
    {
        bool result = false;
        const auto& skelPoseBundle = db.inputs.skel();
        const auto jointsAttr = skelPoseBundle.attributeByName(db.tokens.joints);
        const auto jointXformsAttr = skelPoseBundle.attributeByName(db.tokens.jointWorldTransforms);
        const NameToken jointName = db.inputs.jointName();
        std::string jointNameStr(db.tokenToString(jointName));
        if (jointNameStr.length() == 0)
        {
            setOutputIdentity(db);
            return false;
        }

        const auto joints = jointsAttr.getCpu<OgnToken[]>();
        const auto jointXforms = jointXformsAttr.getCpu<double[][16]>();
        int nJoints = (int)joints->size();
        if (jointXforms->size() != nJoints)
        {
            setOutputIdentity(db);
            return false;
        }

        int jntIdx = -1;
        for (int i = 0; i < nJoints; ++i)
        {
            if ((*joints)[i] == jointName)
            {
                jntIdx = i;
                break;
            }
        }
        if (jntIdx < 0)
        {
            setOutputIdentity(db);
            return false;
        }

        memcpy(db.outputs.transform().data(), &(*jointXforms)[jntIdx][0], sizeof(double) * 16);

        pxr::UsdGeomXformable xformable = getXformable(db);
        if (xformable)
            omni::usd::UsdUtils::setLocalTransformFromWorldTransformMatrix(xformable.GetPrim(), db.outputs.transform());

        return true;
    }
};

REGISTER_OGN_NODE()

// SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
#include "../plugins/StageContext.h"
#include <OgnGetXformDatabase.h>
#include <usdrt/scenegraph/ovstage/AuthoredEdits.h>
#include <algorithm>
class OgnGetXform
{
public:
    static bool compute(OgnGetXformDatabase& db)
    {
        const auto& context = db.abi_context();
        const auto stageId = context.iContext->getStageId(context);
        const auto source = PXR_NS::UsdUtilsStageCache::Get().Find(PXR_NS::UsdStageCache::Id::FromLongInt(stageId));
        if (!source)
        {
            db.logError("Get Xform requires an open stage.");
            return false;
        }
        // Kit 111 brings authored USD edits (e.g. TransformPrimCommand) into the runtime scene only for readers that
        // ask. This node reads the scene on every evaluation: record it as a per-update reader, so Kit synchronizes
        // pending authored edits before the next graph evaluation. Safe inside graph evaluation; never waits.
        usdrt::ovstage::NoteAuthoredEditReader(uint64_t(stageId));
        try
        {
            const auto path = db.inputs.prim.path();
            const auto transform = omni::anim::shared::stage::getStageContext().transform(
                source, std::string_view(path.c_str(), path.size()), db.inputs.useLocal(), db.inputs.usdTimecode());
            if (!transform)
            {
                db.logError("Get Xform could not find the prim in ovstage.");
                return false;
            }
            PXR_NS::GfMatrix4d result;
            std::copy(transform->begin(), transform->end(), result.data());
            db.outputs.transform() = result;
            return true;
        }
        catch (const std::exception& error)
        {
            db.logError("Get Xform ovstage read failed: %s", error.what());
            return false;
        }
    }
};
REGISTER_OGN_NODE()

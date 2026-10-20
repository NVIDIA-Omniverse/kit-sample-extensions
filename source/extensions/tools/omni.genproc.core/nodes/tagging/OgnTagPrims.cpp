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

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Type.h>

#include <OgnTagPrimsDatabase.h>

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

class OgnTagPrims
{
public:
    static bool compute(OgnTagPrimsDatabase& db)
    {
        const bool optionsChanged =
            (db.state.prevTagName() != db.inputs.tagName()) || (db.state.prevTagValue() != db.inputs.tagValue());

        if (!optionsChanged && !db.inputs.bundle.changes().hasChanged())
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        db.outputs.bundle = db.inputs.bundle;

        BundlePrims outputPrims(db.abi_context(), db.outputs.bundle().abi_bundleHandle());
        const size_t primCount = outputPrims.getPrimCount();
        const NameToken& tagName = db.inputs.tagName();
        const NameToken& tagValue = db.inputs.tagValue();

        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            BundlePrim* prim = outputPrims.getPrim(primIndex);

            BundleAttrib* tagAttr = prim->addAttr(tagName, Type(BaseDataType::eToken, 1, 0, AttributeRole::eNone), 0);
            NameToken* tagToken = tagAttr->getData<NameToken>();
            CARB_ASSERT(tagToken != nullptr);
            *tagToken = tagValue;
        }

        // update node state
        db.state.prevTagName() = db.inputs.tagName();
        db.state.prevTagValue() = db.inputs.tagValue();

        return true;
    }
};

REGISTER_OGN_NODE()

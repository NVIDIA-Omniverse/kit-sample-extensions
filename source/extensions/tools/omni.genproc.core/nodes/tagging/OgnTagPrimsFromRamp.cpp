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
#include <omni/ramp/IRamp.h>

#include <OgnTagPrimsFromRampDatabase.h>
#include <algorithm>

using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

class OgnTagPrimsFromRamp
{
public:
    static bool compute(OgnTagPrimsFromRampDatabase& db)
    {
        auto& context = db.abi_context();

        ConstBundlePrims inputPrims(db.abi_context(), db.inputs.bundle().abi_bundleHandle());
        const size_t primCount = inputPrims.getPrimCount();

        const auto& rampPositions = db.inputs.rampPositions();
        const auto& rampValues = db.inputs.rampValues();
        const auto& rampInterpolations = db.inputs.rampInterpolations();
        const size_t rampKeyCount = rampPositions.size();
        const auto& rampTags = db.inputs.rampTags();

        CARB_ASSERT(rampKeyCount == rampValues.size() && rampKeyCount == rampInterpolations.size());

        bool rampChanged = (db.state.prevRampPositions().size() != rampPositions.size()) ||
                           (db.state.prevRampValues().size() != rampValues.size()) ||
                           (db.state.prevRampInterpolations().size() != rampInterpolations.size()) ||
                           (db.state.prevRampTags().size() != rampTags.size());

        rampChanged = rampChanged ||
                      !std::equal(rampPositions.begin(), rampPositions.end(), db.state.prevRampPositions().begin());
        rampChanged = rampChanged || !std::equal(rampValues.begin(), rampValues.end(), db.state.prevRampValues().begin());
        rampChanged = rampChanged || !std::equal(rampInterpolations.begin(), rampInterpolations.end(),
                                                 db.state.prevRampInterpolations().begin());
        rampChanged = rampChanged || !std::equal(rampTags.begin(), rampTags.end(), db.state.prevRampTags().begin());

        bool inputsChanged = (db.state.prevRampPositionsName() != db.inputs.rampPositionsName()) ||
                             (db.state.prevRampValuesName() != db.inputs.rampValuesName()) ||
                             (db.state.prevRampInterpolationsName() != db.inputs.rampInterpolationsName()) ||
                             (db.state.prevRampTagsName() != db.inputs.rampTagsName()) || rampChanged ||
                             db.inputs.bundle.changes().hasChanged();

        if (!inputsChanged)
        {
            // Inputs haven't changed since last compute; no need to rerun
            return true;
        }

        db.outputs.bundle = db.inputs.bundle;

        BundlePrims outputPrims(db.abi_context(), db.outputs.bundle().abi_bundleHandle());

        const NameToken rampPositionsName = db.inputs.rampPositionsName();
        const NameToken rampValuesName = db.inputs.rampValuesName();
        const NameToken rampInterpolationsName = db.inputs.rampInterpolationsName();
        const NameToken rampTagsName = db.inputs.rampTagsName();

        const float* positions = rampPositions.data();
        const float* values = rampValues.data();
        const int* interpolations = rampInterpolations.data();
        std::vector<NameToken> tags(rampTags.size());
        for (size_t i = 0; i < rampTags.size(); i++)
        {
            tags[i] = rampTags.data()[i];
        }

        if (rampKeyCount > 0)
        {
            BundlePrim& commonAttrs = outputPrims.getCommonAttrs();

            BundleAttrib* rampPositionsAttr = commonAttrs.addAttr(
                rampPositionsName, Type(BaseDataType::eFloat, 1, 1, AttributeRole::eNone), rampKeyCount);
            float* positionsOut = rampPositionsAttr->getData<float>();
            CARB_ASSERT(positionsOut != nullptr);
            memcpy(positionsOut, positions, rampKeyCount * sizeof(float));

            BundleAttrib* rampValuesAttr = commonAttrs.addAttr(
                rampValuesName, Type(BaseDataType::eFloat, 1, 1, AttributeRole::eNone), rampKeyCount);
            float* valuesOut = rampValuesAttr->getData<float>();
            CARB_ASSERT(valuesOut != nullptr);
            memcpy(valuesOut, values, rampKeyCount * sizeof(float));

            BundleAttrib* rampInterpolationsAttr = commonAttrs.addAttr(
                rampInterpolationsName, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone), rampKeyCount);
            int* interpolationsOut = rampInterpolationsAttr->getData<int>();
            CARB_ASSERT(interpolationsOut != nullptr);
            memcpy(interpolationsOut, interpolations, rampKeyCount * sizeof(int));

            BundleAttrib* rampTagsAttr = commonAttrs.addAttr(
                rampTagsName, Type(BaseDataType::eToken, 1, 1, AttributeRole::eNone), rampTags.size());
            NameToken* tagsOut = rampTagsAttr->getData<NameToken>();
            CARB_ASSERT(tagsOut != nullptr);
            memcpy(tagsOut, tags.data(), tags.size() * sizeof(NameToken));
        }

        // update node state
        db.state.prevRampPositionsName() = db.inputs.rampPositionsName();
        db.state.prevRampValuesName() = db.inputs.rampValuesName();
        db.state.prevRampInterpolationsName() = db.inputs.rampInterpolationsName();
        db.state.prevRampTagsName() = db.inputs.rampTagsName();
        if (rampChanged)
        {
            db.state.prevRampPositions() = rampPositions;
            db.state.prevRampValues() = rampValues;
            db.state.prevRampInterpolations() = rampInterpolations;
            db.state.prevRampTags() = rampTags;
        }

        return true;
    }
};

REGISTER_OGN_NODE()

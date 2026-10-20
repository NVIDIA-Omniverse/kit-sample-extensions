// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/SafeCast.h>

#include <OgnScatterPointsModifierDatabase.h>
#include <unordered_set>
#include <vector>


using omni::math::linalg::safeCastToOmni;
using omni::math::linalg::vec3f;


class OgnScatterPointsModifier
{
public:
    template <class T>
    static bool isSameArray(const omni::graph::core::ogn::const_array<T>& a, omni::graph::core::ogn::array<T>& b)
    {
        return a.size() == b.size() && std::equal(a.begin(), a.end(), b.begin());
    }

    static bool isInputsChanged(OgnScatterPointsModifierDatabase& db)
    {
        const GraphContextObj& context = db.abi_context();
        bool inputsChanged = false;

        if (db.inputs.active() != db.state.prevActive())
        {
            db.state.prevActive() = db.inputs.active();
            inputsChanged |= true;
        }

        const auto& ids = db.inputs.ids();
        auto& prevIds = db.state.prevIds();
        if (!isSameArray<int>(ids, prevIds))
        {
            prevIds = ids;
            inputsChanged |= true;
        }

        const auto& positions = db.inputs.positions();
        auto& prevPositions = db.state.prevPositions();
        if (!isSameArray<vec3f>(positions, prevPositions))
        {
            prevPositions = positions;
            inputsChanged |= true;
        }

        const auto& rotations = db.inputs.rotations();
        auto& prevRotations = db.state.prevRotations();
        if (!isSameArray<vec3f>(rotations, prevRotations))
        {
            prevRotations = rotations;
            inputsChanged |= true;
        }

        const auto& scales = db.inputs.scales();
        auto& prevScales = db.state.prevScales();
        if (!isSameArray<vec3f>(scales, prevScales))
        {
            prevScales = scales;
            inputsChanged |= true;
        }

        const auto& tangents = db.inputs.tangents();
        auto& prevTangents = db.state.prevTangents();
        if (!isSameArray<vec3f>(tangents, prevTangents))
        {
            prevTangents = tangents;
            inputsChanged |= true;
        }

        const auto& normals = db.inputs.normals();
        auto& prevNormals = db.state.prevNormals();
        if (!isSameArray<vec3f>(normals, prevNormals))
        {
            prevNormals = normals;
            inputsChanged |= true;
        }

        const auto& objectIndices = db.inputs.objectIndices();
        auto& prevObjectIndices = db.state.prevObjectIndices();
        if (!isSameArray<int>(objectIndices, prevObjectIndices))
        {
            prevObjectIndices = objectIndices;
            inputsChanged |= true;
        }

        {
            inputsChanged = inputsChanged || db.inputs.bundle.changes().hasChanged();
        }

        return inputsChanged;
    }

    static size_t remapIds(const int* inputIdsData, const size_t inputIdsSize, int pointsSize, std::vector<int>& remappedIds)
    {
        remappedIds.resize(inputIdsSize);
        memcpy(remappedIds.data(), inputIdsData, inputIdsSize * sizeof(int));
        std::unordered_set<int> usedIds(remappedIds.begin(), remappedIds.end());

        size_t remappedCount = 0;
        int nextAvailableRemapId = pointsSize;
        for (size_t i = 0; i < remappedIds.size(); i++)
        {
            auto id = remappedIds[i];

            // If the upstream generated less points than overridden data, remap the extra ids to an available one
            if (id >= pointsSize)
            {
                int prevAvailableRemapId = nextAvailableRemapId;
                for (int i = nextAvailableRemapId - 1; i >= 0; i--)
                {
                    if (usedIds.find(i) == usedIds.end())
                    {
                        nextAvailableRemapId = i;
                        break;
                    }
                }

                // not enough id to remap, break early. The overridden instance will be missing in output data
                if (nextAvailableRemapId == prevAvailableRemapId)
                {
                    break;
                }

                usedIds.erase(id);
                remappedIds[i] = nextAvailableRemapId;
                remappedCount++;
                CARB_LOG_WARN("remapped index %d to %d", id, nextAvailableRemapId);
            }
        }
        return remappedCount;
    }

    static bool compute(OgnScatterPointsModifierDatabase& db)
    {
        auto& nodeObj = db.abi_node();
        const GraphContextObj& context = db.abi_context();
        const IGraphContext* const iContext = context.iContext;

        bool inputsChanged = isInputsChanged(db);
        if (!inputsChanged)
            return true;

        if (!db.inputs.active())
        {
            BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
            outputPrims.clearContents();
            return true;
        }

        ConstBundlePrims inputPrims(context, db.inputs.bundle().abi_bundleHandle());
        ConstBundlePrim& inputPrim = inputPrims.getConstCommonAttrs();

        BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
        outputPrims.clearContents();
        BundlePrim& outputPrim = outputPrims.getCommonAttrs();

        outputPrim.copyContentsFrom(inputPrim);

        const size_t inputIdsSize = db.inputs.ids().size();
        const int* inputIdsData = db.inputs.ids().data();

        if (inputIdsSize == 0)
        {
            return true;
        }

        BundleAttrib* outputPointsAttr = outputPrim.getAttr(db.tokens.points);
        if (outputPointsAttr == nullptr)
        {
            return true;
        }

        vec3f* points = outputPointsAttr->getData<vec3f>();
        const size_t pointsSize = outputPointsAttr->size();

        if (pointsSize)
        {
            const size_t inputPositionsSize = db.inputs.positions().size();
            const vec3f* inputPositionsData = db.inputs.positions().data();

            const size_t inputRotationsSize = db.inputs.rotations().size();
            const vec3f* inputRotationsData = db.inputs.rotations().data();

            const size_t inputScalesSize = db.inputs.scales().size();
            const vec3f* inputScalesData = db.inputs.scales().data();

            const size_t inputTangentsSize = db.inputs.tangents().size();
            const vec3f* inputTangentsData = db.inputs.tangents().data();

            const size_t inputNormalsSize = db.inputs.normals().size();
            const vec3f* inputNormalsData = db.inputs.normals().data();

            const size_t inputObjectIndicesSize = db.inputs.objectIndices().size();
            const int* inputObjectIndicesData = db.inputs.objectIndices().data();

            BundleAttrib* outputRotationsAttr = outputPrim.getAttr(db.tokens.rotations);
            vec3f* rotations = outputRotationsAttr->getData<vec3f>();
            const size_t rotationsSize = outputRotationsAttr->size();

            BundleAttrib* outScalesAttr = outputPrim.getAttr(db.tokens.scales);
            vec3f* scales = outScalesAttr->getData<vec3f>();
            const size_t scalesSize = outScalesAttr->size();

            BundleAttrib* outTangentsAttr = outputPrim.getAttr(db.tokens.tangents);
            vec3f* tangents = outTangentsAttr->getData<vec3f>();
            const size_t tangentsSize = outTangentsAttr->size();

            BundleAttrib* outNormalsAttr = outputPrim.getAttr(db.tokens.normals);
            vec3f* normals = outNormalsAttr->getData<vec3f>();
            const size_t normalsSize = outNormalsAttr->size();

            BundleAttrib* outObjectIndicesAttr = outputPrim.getAttr(db.tokens.objectIndices);
            int* objectIndices = outObjectIndicesAttr->getData<int>();
            const size_t objectIndicesSize = outObjectIndicesAttr->size();

            // Remap the ids if any of it is greater than the pointsSize. We want to preserve the modified instances as
            // much as possible, so that if the input points size is less than overridden id, find another unused id and
            // override that instead.
            std::vector<int> remappedIds;
            size_t remappedCount = remapIds(inputIdsData, inputIdsSize, (int)pointsSize, remappedIds);

            // We need to store the remapped ids from/to so that when the remapped instance is again being manipulated,
            // it can find the original id.
            db.state.remappedIdsFrom().resize(remappedCount);
            db.state.remappedIdsTo().resize(remappedCount);
            int* remappedIdsFromData = db.state.remappedIdsFrom().data();
            int* remappedIdsToData = db.state.remappedIdsTo().data();
            size_t remappedStateIndex = 0;

            for (size_t i = 0; i < remappedIds.size(); i++)
            {
                const int originalId = inputIdsData[i];
                const int id = remappedIds[i];
                if (originalId != id)
                {
                    remappedIdsFromData[remappedStateIndex] = originalId;
                    remappedIdsToData[remappedStateIndex] = id;
                    remappedStateIndex++;
                }

                if (id < pointsSize)
                {
                    points[id] = inputPositionsData[i];
                }
                if (id < rotationsSize)
                {
                    // rotations[id] = inputRotationsData[i];
                }
                if (id < scalesSize)
                {
                    scales[id] = inputScalesData[i];
                }
                if (id < scalesSize)
                {
                    scales[id] = inputScalesData[i];
                }
                if (id < tangentsSize)
                {
                    tangents[id] = inputTangentsData[i];
                }
                if (id < normalsSize)
                {
                    normals[id] = inputNormalsData[i];
                }
                if (id < objectIndicesSize)
                {
                    objectIndices[id] = inputObjectIndicesData[i];
                }
            }
        }

        return true;
    }
};

REGISTER_OGN_NODE()

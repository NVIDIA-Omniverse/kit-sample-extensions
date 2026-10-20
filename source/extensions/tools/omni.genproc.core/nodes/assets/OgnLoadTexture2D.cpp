// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "TextureManager.h"
#include "UsdPCH.h"
#include "Utils.h"

#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/SafeCast.h>

#include <OgnLoadTexture2DDatabase.h>
#include <unordered_set>

namespace omni
{

namespace genproc
{

class OgnLoadTexture2D
{
public:
    static std::vector<std::string> getTexturePaths(const PXR_NS::UsdPrim& prim)
    {
        std::vector<std::string> paths;
        static const PXR_NS::TfToken s_texturesInputs = PXR_NS::TfToken("inputs:textures");

        auto stage = prim.GetStage();
        const PXR_NS::UsdAttribute texturesAttribute = prim.GetAttribute(s_texturesInputs);

        PXR_NS::SdfPathVector texturesConnections;
        texturesAttribute.GetConnections(&texturesConnections);
        for (const PXR_NS::SdfPath& conntection : texturesConnections)
        {
            if (const PXR_NS::UsdAttribute attribute = stage->GetAttributeAtPath(conntection))
            {
                std::string value;
                if (attribute.Get(&value))
                {
                    paths.push_back(std::move(value));
                }
            }
        }
        return paths;
    }

    static bool isInputsChanged(OgnLoadTexture2DDatabase& db, OgnLoadTexture2D& internalState, PXR_NS::UsdPrim& thisPrim)
    {
        const GraphContextObj& context = db.abi_context();
        bool inputsChanged = false;

        if (db.inputs.active() != db.state.prevActive())
        {
            db.state.prevActive() = db.inputs.active();
            inputsChanged |= true;
        }

        {
            std::string combinedTextures;
            const auto texturePaths = getTexturePaths(thisPrim);
            for (const std::string& path : texturePaths)
            {
                combinedTextures += path;
            }

            inputsChanged |= db.state.prevTextures() != combinedTextures;
            db.state.prevTextures() = combinedTextures;
        }

        for (const auto& texEntry : internalState.textures)
        {
            auto tex = internalState.textureManager->getTextureFromId(texEntry.first);
            auto assetVersion = tex->getAssetVersion();
            if (assetVersion > texEntry.second)
            {
                inputsChanged |= true;
                break;
            }
        }

        return inputsChanged;
    }

    static void loadTextures(OgnLoadTexture2DDatabase& db,
                             std::vector<carb::assets::Id>& currTextureAssetIds,
                             OgnLoadTexture2D& internalState,
                             PXR_NS::UsdPrim& thisPrim)
    {
        const auto texturePaths = getTexturePaths(thisPrim);
        auto stage = thisPrim.GetStage();

        if (texturePaths.size())
        {
            PXR_NS::ArResolverContextBinder contextBinder(stage->GetPathResolverContext());
            PXR_NS::ArResolverScopedCache scopedCache;

            currTextureAssetIds.reserve(texturePaths.size());

            for (const std::string& path : texturePaths)
            {
                // resolve the path against prim introduction layer??? // TODO use rootlayer for now
                std::string resolvedPath = PXR_NS::ArGetResolver().Resolve(path);

                // Returns same asset id if path is the same
                currTextureAssetIds.push_back(internalState.textureManager->loadAsset(resolvedPath.c_str()));
            }
        }
    }

    static bool compute(OgnLoadTexture2DDatabase& db)
    {
        auto& nodeObj = db.abi_node();
        const GraphContextObj& context = db.abi_context();
        const IGraphContext* const iContext = context.iContext;

        PXR_NS::UsdPrim thisPrim = getUsdPrimFromNode(context, nodeObj);
        if (!thisPrim.IsValid())
            return false;

        OgnLoadTexture2D& internalState = db.internalState<OgnLoadTexture2D>();

        bool inputsChanged = isInputsChanged(db, internalState, thisPrim);
        if (!inputsChanged)
            return true;

        if (!db.inputs.active())
        {
            BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
            outputPrims.clearContents();
            return true;
        }

        std::vector<carb::assets::Id> currTextureAssetIds;
        loadTextures(db, currTextureAssetIds, internalState, thisPrim);

        BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());

        // TODO don't clear unchanged textures?
        outputPrims.clearContents();
        outputPrims.addPrims(currTextureAssetIds.size());
        std::vector<std::pair<carb::assets::Id, uint64_t>> newTextures;
        for (size_t i = 0; i < outputPrims.getPrimCount(); i++)
        {
            using namespace omni::graph::core;

            const auto tex = internalState.textureManager->getTextureFromId(currTextureAssetIds[i]);

            uint32_t width, height;
            uint8_t bitDpeth, componentCount;
            const uint8_t* data;
            uint64_t snapshotVersion;

            bool valid = tex->getLatestTextureInfo(snapshotVersion, width, height, bitDpeth, componentCount, data);
            newTextures.push_back(std::make_pair(tex->getId(), snapshotVersion));

            BundlePrim* bundlePrim = outputPrims.getPrim(i);
            auto validAttr = bundlePrim->addAttr(db.tokens.valid, Type(BaseDataType::eBool, 1, 0, AttributeRole::eNone));
            auto widthAttr = bundlePrim->addAttr(db.tokens.width, Type(BaseDataType::eUInt, 1, 0, AttributeRole::eNone));
            auto heightAttr =
                bundlePrim->addAttr(db.tokens.height, Type(BaseDataType::eUInt, 1, 0, AttributeRole::eNone));
            auto bitDepthAttr =
                bundlePrim->addAttr(db.tokens.bitDepth, Type(BaseDataType::eUChar, 1, 0, AttributeRole::eNone));
            auto compCountAttr =
                bundlePrim->addAttr(db.tokens.componentCount, Type(BaseDataType::eUChar, 1, 0, AttributeRole::eNone));
            auto dataAttr = bundlePrim->addAttr(db.tokens.data, Type(BaseDataType::eUChar, 1, 1, AttributeRole::eNone));

            validAttr->set(valid);
            if (valid)
            {
                widthAttr->set(width);
                heightAttr->set(height);
                bitDepthAttr->set(bitDpeth);
                compCountAttr->set(componentCount);

                size_t dataSize = width * height * componentCount * bitDpeth / 8;
                dataAttr->resize(dataSize);
                uint8_t* dataPtr = dataAttr->getData<uint8_t>();
                memcpy(dataPtr, data, dataSize);
            }
        }

        // Unload the assets that's no longer in use
        std::unordered_set<carb::assets::Id> currTextureAssetIdsSet(
            currTextureAssetIds.begin(), currTextureAssetIds.end());
        for (const auto& entry : internalState.textures)
        {
            const auto& assetId = entry.first;
            if (currTextureAssetIdsSet.find(entry.first) == currTextureAssetIdsSet.end())
            {
                internalState.textureManager->unloadAsset(assetId);
            }
        }

        internalState.textures.swap(newTextures);

        return true;
    }

    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
        auto& internalState = OgnLoadTexture2DDatabase::sInternalState<OgnLoadTexture2D>(nodeObj);
        internalState.textureManager = std::make_unique<TextureManager>();
    }

    static void release(const NodeObj& nodeObj)
    {
        auto& internalState = OgnLoadTexture2DDatabase::sInternalState<OgnLoadTexture2D>(nodeObj);
        internalState.textureManager.reset();
    }

private:
    std::unique_ptr<TextureManager> textureManager;
    std::vector<std::pair<carb::assets::Id, uint64_t>> textures; // assetId to snapshotVersion
};

REGISTER_OGN_NODE()

}
}

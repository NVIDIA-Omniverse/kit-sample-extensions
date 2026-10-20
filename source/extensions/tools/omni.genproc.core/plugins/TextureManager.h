// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <carb/assets/AssetsUtils.h>
#include <carb/imaging/IImaging.h>

#include <atomic>
#include <mutex>
#include <unordered_map>

namespace carb
{
namespace datasource
{
struct IDataSource;
struct Connection;
}
}

namespace omni
{
namespace genproc
{

using ScopedTextureAsset = carb::assets::ScopedSnapshot<carb::imaging::Image>;

class Texture
{
public:
    Texture(const carb::assets::Id& id, const std::string& path);
    ~Texture();

    bool getLatestTextureInfo(uint64_t& version,
                              uint32_t& width,
                              uint32_t& height,
                              uint8_t& bitDepth,
                              uint8_t& componentCount,
                              const uint8_t*& data);

    carb::assets::Id getId() const
    {
        return m_id;
    }

    const std::string& getPath() const
    {
        return m_path;
    }

    uint64_t getAssetVersion() const;

private:
    void onAssetChanged();

    carb::assets::IAssets* m_assets;
    carb::imaging::IImaging* m_imaging;

    const carb::assets::Id m_id;
    const std::string m_path;
    ScopedTextureAsset m_snapshot;
    uint64_t m_assetVersion = 2;
    uint64_t m_snapshotVersion = 1;
    mutable std::mutex m_snapshotMutex;
};

class TextureManager
{
public:
    TextureManager();

    ~TextureManager();

    carb::assets::Id loadAsset(const std::string& filePath);

    void unloadAsset(const carb::assets::Id& id);

    Texture* getTextureFromId(const carb::assets::Id& id) const;

private:
    carb::assets::IAssets* m_assets;
    carb::assets::Pool m_assetPool;
    carb::datasource::IDataSource* m_dataSource;
    carb::datasource::Connection* m_connection;
    carb::imaging::IImaging* m_imaging;
    std::unordered_map<std::string, carb::assets::Id> m_pathToIds;
    std::unordered_map<carb::assets::Id, std::unique_ptr<Texture>> m_idToTextures;
};
}
}

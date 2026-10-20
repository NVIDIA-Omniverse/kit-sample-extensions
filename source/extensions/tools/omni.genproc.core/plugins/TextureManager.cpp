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

#include <carb/InterfaceUtils.h>
#include <carb/datasource/DataSourceUtils.h>
#include <carb/imaging/ImagingUtils.h>

namespace omni
{
namespace genproc
{

Texture::Texture(const carb::assets::Id& id, const std::string& path) : m_id(id), m_path(path)
{
    m_assets = carb::getCachedInterface<carb::assets::IAssets>();
    m_imaging = carb::getCachedInterface<carb::imaging::IImaging>();

    m_assets->subscribeToChangeEvent(
        m_id,
        [](carb::assets::Id id, void* userData)
        {
            Texture* _this = reinterpret_cast<Texture*>(userData);
            if (id == _this->m_id)
            {
                _this->onAssetChanged();
            }
        },
        this);

    m_assets->yieldForAsset(m_id);
}

Texture::~Texture()
{
    m_assets->unsubscribeToChangeEvent(m_id);
}

bool Texture::getLatestTextureInfo(
    uint64_t& version, uint32_t& width, uint32_t& height, uint8_t& bitDepth, uint8_t& componentCount, const uint8_t*& data)
{
    {
        std::lock_guard<std::mutex> lock(m_snapshotMutex);
        if (m_assetVersion != m_snapshotVersion)
        {
            m_snapshot = m_assets->takeSnapshot<carb::imaging::Image>(m_id);
            m_snapshotVersion = m_assetVersion;
        }
    }

    version = m_snapshotVersion;
    if (!m_snapshot)
    {
        return false;
    }

    width = m_imaging->getImageWidth(m_snapshot.get(), 0);
    height = m_imaging->getImageHeight(m_snapshot.get(), 0);
    data = m_imaging->getImageData(m_snapshot.get(), 0);
    carb::imaging::DataFormat format = m_imaging->getImageDataFormat(m_snapshot.get());

    using carb::Format;

    // First, get the bit depth
    switch (format)
    {
    case Format::eR8_UNORM:
    case Format::eR8_SNORM:
    case Format::eR8_UINT:
    case Format::eR8_SINT:
    case Format::eRG8_UNORM:
    case Format::eRG8_SNORM:
    case Format::eRG8_UINT:
    case Format::eRG8_SINT:
    case Format::eBGRA8_UNORM:
    case Format::eBGRA8_SRGB:
    case Format::eRGBA8_UNORM:
    case Format::eRGBA8_SNORM:
    case Format::eRGBA8_UINT:
    case Format::eRGBA8_SINT:
    case Format::eRGBA8_SRGB:
        bitDepth = 8;
        break;

    case Format::eR16_UNORM:
    case Format::eR16_SNORM:
    case Format::eR16_UINT:
    case Format::eR16_SINT:
    case Format::eR16_SFLOAT:
    case Format::eRG16_UNORM:
    case Format::eRG16_SNORM:
    case Format::eRG16_UINT:
    case Format::eRG16_SINT:
    case Format::eRG16_SFLOAT:
    case Format::eRGBA16_UNORM:
    case Format::eRGBA16_SNORM:
    case Format::eRGBA16_UINT:
    case Format::eRGBA16_SINT:
    case Format::eRGBA16_SFLOAT:
        bitDepth = 16;
        break;

    case Format::eR32_UINT:
    case Format::eR32_SINT:
    case Format::eR32_SFLOAT:
    case Format::eRG32_UINT:
    case Format::eRG32_SINT:
    case Format::eRG32_SFLOAT:
    case Format::eRGB32_UINT:
    case Format::eRGB32_SINT:
    case Format::eRGB32_SFLOAT:
    case Format::eRGBA32_UINT:
    case Format::eRGBA32_SINT:
    case Format::eRGBA32_SFLOAT:
        bitDepth = 32;
        break;

    case Format::eUnknown:
    default:
        bitDepth = 0;
        componentCount = 0;
        return false;
    }

    // Second, get the component count
    switch (format)
    {
    case Format::eR8_UNORM:
    case Format::eR8_SNORM:
    case Format::eR8_UINT:
    case Format::eR8_SINT:
    case Format::eR16_UNORM:
    case Format::eR16_SNORM:
    case Format::eR16_UINT:
    case Format::eR16_SINT:
    case Format::eR16_SFLOAT:
    case Format::eR32_UINT:
    case Format::eR32_SINT:
    case Format::eR32_SFLOAT:
        componentCount = 1;
        break;

    case Format::eRG8_UNORM:
    case Format::eRG8_SNORM:
    case Format::eRG8_UINT:
    case Format::eRG8_SINT:
    case Format::eRG16_UNORM:
    case Format::eRG16_SNORM:
    case Format::eRG16_UINT:
    case Format::eRG16_SINT:
    case Format::eRG16_SFLOAT:
    case Format::eRG32_UINT:
    case Format::eRG32_SINT:
    case Format::eRG32_SFLOAT:
        componentCount = 2;
        break;

    case Format::eRGB32_UINT:
    case Format::eRGB32_SINT:
    case Format::eRGB32_SFLOAT:
        componentCount = 3;
        break;

    case Format::eBGRA8_UNORM:
    case Format::eBGRA8_SRGB:
    case Format::eRGBA8_UNORM:
    case Format::eRGBA8_SNORM:
    case Format::eRGBA8_UINT:
    case Format::eRGBA8_SINT:
    case Format::eRGBA8_SRGB:
    case Format::eRGBA16_UNORM:
    case Format::eRGBA16_SNORM:
    case Format::eRGBA16_UINT:
    case Format::eRGBA16_SINT:
    case Format::eRGBA16_SFLOAT:
    case Format::eRGBA32_UINT:
    case Format::eRGBA32_SINT:
    case Format::eRGBA32_SFLOAT:
        componentCount = 4;
        break;

    case Format::eUnknown:
    default:
        CARB_ASSERT(0, "This should have returned above!");
    }

    return true;
}

uint64_t Texture::getAssetVersion() const
{
    std::lock_guard<std::mutex> lock(m_snapshotMutex);
    return m_assetVersion;
}

void Texture::onAssetChanged()
{
    std::lock_guard<std::mutex> lock(m_snapshotMutex);
    m_assetVersion += 1;
}

TextureManager::TextureManager()
{
    carb::Framework* framework = carb::getFramework();
    m_assets = carb::getCachedInterface<carb::assets::IAssets>();
    m_assetPool = m_assets->createPool("ScatterTextures");

    m_dataSource = framework->acquireInterface<carb::datasource::IDataSource>("carb.datasource-omniclient.plugin");
    m_connection = carb::datasource::connectAndWait(carb::datasource::ConnectionDesc{ "" }, m_dataSource);

    m_imaging = carb::getCachedInterface<carb::imaging::IImaging>();
}

TextureManager::~TextureManager()
{
    m_idToTextures.clear();
    m_pathToIds.clear();

    m_dataSource->disconnect(m_connection);
    m_assets->destroyPool(m_assetPool);
}

carb::assets::Id TextureManager::loadAsset(const std::string& filePath)
{
    const auto& idEntry = m_pathToIds.find(filePath);
    if (idEntry != m_pathToIds.end())
    {
        return idEntry->second;
    }

    carb::imaging::LoadImageParameters loadImageParameters{};
    auto id = m_assets->loadAsset<carb::imaging::Image>(
        m_dataSource, m_connection, filePath.c_str(), m_assetPool, loadImageParameters);
    m_pathToIds[filePath] = id;
    m_idToTextures[id] = std::make_unique<Texture>(id, filePath);
    return id;
}

void TextureManager::unloadAsset(const carb::assets::Id& id)
{
    const auto tex = getTextureFromId(id);
    if (tex)
    {
        m_assets->unloadAsset(id);
        m_pathToIds.erase(tex->getPath());
        m_idToTextures.erase(id);
    }
}

Texture* TextureManager::getTextureFromId(const carb::assets::Id& id) const
{
    const auto& entry = m_idToTextures.find(id);
    if (entry != m_idToTextures.end())
    {
        return entry->second.get();
    }
    return nullptr;
}
}
}

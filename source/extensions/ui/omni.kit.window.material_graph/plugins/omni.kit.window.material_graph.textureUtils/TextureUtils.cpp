// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#define CARB_EXPORTS

#include <carb/Framework.h>
#include <carb/PluginUtils.h>
#include <carb/Format.h>
#include <carb/extras/Path.h>
#include <carb/imaging/IImaging.h>
#include <carb/omniclient/IOmniClient.h>

#include "TextureUtils.h"
#include <omni/log/LogChannel.h>

#include <cstdlib>
#include <cstring>
#include <memory>
#include <vector>

#define PLUGIN_NAME "omni.kit.window.material_graph.textureUtils.plugin"

const struct carb::PluginImplDesc kPluginImpl = { PLUGIN_NAME, "Texture utilities plugin for Material Graph", "NVIDIA",
                                                  carb::PluginHotReload::eDisabled, "dev" };

CARB_PLUGIN_IMPL(kPluginImpl, omni::kit::materialGraph::TextureUtilsPlugin)

CARB_PLUGIN_IMPL_DEPS(carb::imaging::IImaging, carb::omniclient::IOmniClient)

OMNI_LOG_ADD_CHANNEL(kExtChannel,
                     "omni.kit.window.material_graph",
                     "Messages related to omni::kit::materialGraph::TextureUtilsPlugin.")


namespace
{
static bool readOmniClientFile(carb::omniclient::IOmniClient* omniclient, const char* url, std::vector<uint8_t>& buffer)
{
    if (!omniclient)
    {
        return false;
    }

    struct Request
    {
        std::vector<uint8_t>* buffer;
        bool result;
    } request{ &buffer, false };

    OmniClientRequestId requestId = omniclient->readFile(
        url, &request,
        [](void* userData, OmniClientResult result, char const* /*version*/, struct OmniClientContent* content)
            OMNICLIENT_CALLBACK_NOEXCEPT {
                Request* request = reinterpret_cast<Request*>(userData);
                request->result = (result == eOmniClientResult_Ok);
                if (request->result && content && content->buffer && content->size > 0)
                {
                    request->buffer->assign(static_cast<const uint8_t*>(content->buffer),
                                            static_cast<const uint8_t*>(content->buffer) + content->size);
                }
                else
                {
                    request->result = false;
                }
            });

    omniclient->wait(requestId);
    return request.result;
}

// Load an image file into a carb::imaging::Image.
static carb::imaging::Image* loadImage(carb::imaging::IImaging* imaging, const char* url)
{
    if (!url || !url[0])
    {
        OMNI_LOG_WARN(kExtChannel, "texture info: empty path");
        return nullptr;
    }

    std::vector<uint8_t> buffer;
    auto omniclient = carb::getCachedInterface<carb::omniclient::IOmniClient>();
    if (!omniclient)
    {
        OMNI_LOG_WARN(kExtChannel, "texture info: omniclient unavailable for '%s'", url);
        return nullptr;
    }

    if (!readOmniClientFile(omniclient, url, buffer) || buffer.empty())
    {
        OMNI_LOG_WARN(kExtChannel, "texture info: failed to read '%s' via omniclient", url);
        return nullptr;
    }

    const std::string ext = carb::extras::Path(url).getExtension().getStringBuffer();
    carb::imaging::Image* image = imaging->createImage(buffer.data(), buffer.size(), ext.c_str(), 0);
    if (!image)
    {
        const char* error = imaging->getErrorMessage();
        OMNI_LOG_WARN(kExtChannel, "texture info failed for '%s': %s", url, error ? error : "unknown");
    }

    return image;
}
} // namespace

namespace omni
{
namespace kit
{
namespace materialGraph
{
// Query basic texture info using carb::imaging.
static void GetTextureInfo(const char* url, bool* valid, int32_t* channelCount)
{
    if (valid)
    {
        *valid = false;
    }

    if (channelCount)
    {
        *channelCount = 0;
    }

    auto framework = carb::getFramework();

    auto imaging = framework->acquireInterface<carb::imaging::IImaging>();
    if (!imaging)
    {
        return;
    }

    carb::imaging::Image* image = loadImage(imaging, url);
    if (!image)
    {
        return;
    }

    if (valid)
    {
        *valid = true;
    }

    if (channelCount)
    {
        *channelCount = 0;
        const carb::imaging::DataFormat format = imaging->getImageDataFormat(image);
        switch (format)
        {
            case carb::imaging::DataFormat::eR8_UNORM:
            case carb::imaging::DataFormat::eR8_UINT:
            case carb::imaging::DataFormat::eR16_UNORM:
            case carb::imaging::DataFormat::eR16_UINT:
            case carb::imaging::DataFormat::eR16_SFLOAT:
            case carb::imaging::DataFormat::eR32_UINT:
            case carb::imaging::DataFormat::eR32_SFLOAT:
            case carb::imaging::DataFormat::eD32_SFLOAT:
                *channelCount = 1;
                break;
            case carb::imaging::DataFormat::eRG8_UNORM:
            case carb::imaging::DataFormat::eRG8_UINT:
            case carb::imaging::DataFormat::eRG16_UNORM:
            case carb::imaging::DataFormat::eRG16_UINT:
            case carb::imaging::DataFormat::eRG16_SFLOAT:
            case carb::imaging::DataFormat::eRG32_UINT:
            case carb::imaging::DataFormat::eRG32_SFLOAT:
                *channelCount = 2;
                break;
            case carb::imaging::DataFormat::eRGB32_SFLOAT:
            case carb::imaging::DataFormat::eRGB32_UINT:
                *channelCount = 3;
                break;
            case carb::imaging::DataFormat::eRGBA8_UNORM:
            case carb::imaging::DataFormat::eRGBA8_UINT:
            case carb::imaging::DataFormat::eRGBA16_UNORM:
            case carb::imaging::DataFormat::eRGBA16_UINT:
            case carb::imaging::DataFormat::eRGBA16_SFLOAT:
            case carb::imaging::DataFormat::eRGBA32_UINT:
            case carb::imaging::DataFormat::eRGBA32_SFLOAT:
                *channelCount = 4;
                break;
            default:
                *channelCount = 0;
                break;
        }
    }

    imaging->destroyImage(image);
}

// Export a texture preview icon to disk.
static bool CreateTextureIcon(const char* url, const char* outputPath, int32_t size)
{
    if (!outputPath || !outputPath[0])
    {
        OMNI_LOG_WARN(kExtChannel, "texture icon: empty output path");
        return false;
    }
    if (size <= 0)
    {
        OMNI_LOG_WARN(kExtChannel, "texture icon: invalid size %d", size);
        return false;
    }

    auto framework = carb::getFramework();
    auto imaging = framework->acquireInterface<carb::imaging::IImaging>();
    if (!imaging)
    {
        return false;
    }

    carb::imaging::Image* image = loadImage(imaging, url);
    if (!image)
    {
        return false;
    }

    auto format = imaging->getImageDataFormat(image);
    if (format != carb::imaging::DataFormat::eRGBA8_UNORM)
    {
        if (!imaging->convertImageData(image, carb::imaging::DataFormat::eRGBA8_UNORM))
        {
            const char* error = imaging->getErrorMessage();
            OMNI_LOG_WARN(
                kExtChannel, "texture icon: convertImageData failed for '%s': %s", url, error ? error : "unknown");
            imaging->destroyImage(image);
            return false;
        }
        format = imaging->getImageDataFormat(image);
    }
    if (format != carb::imaging::DataFormat::eRGBA8_UNORM)
    {
        OMNI_LOG_WARN(kExtChannel, "texture icon: unsupported format for '%s'", url);
        imaging->destroyImage(image);
        return false;
    }
    const uint8_t* data = imaging->getImageData(image, 0);
    const uint32_t width = imaging->getImageWidth(image, 0);
    const uint32_t height = imaging->getImageHeight(image, 0);
    if (!data || width == 0 || height == 0)
    {
        const char* error = imaging->getErrorMessage();
        OMNI_LOG_WARN(kExtChannel, "texture icon: failed to read '%s': %s", url, error ? error : "unknown");
        imaging->destroyImage(image);
        return false;
    }

    std::vector<uint8_t> rgba;
    rgba.resize(static_cast<size_t>(width) * static_cast<size_t>(height) * 4);
    switch (format)
    {
        case carb::imaging::DataFormat::eRGBA8_UNORM:
        case carb::imaging::DataFormat::eRGBA8_UINT:
        {
            std::memcpy(rgba.data(), data, rgba.size());
            break;
        }
        default:
        {
            const char* error = imaging->getErrorMessage();
            OMNI_LOG_WARN(
                kExtChannel, "texture icon: unsupported format for '%s': %s", outputPath, error ? error : "unknown");
            imaging->destroyImage(image);
            return false;
        }
    }

    // Downscale to target size if needed.
    std::vector<uint8_t> scaled;
    uint32_t outWidth = static_cast<uint32_t>(size);
    uint32_t outHeight = static_cast<uint32_t>(size);
    if (width == outWidth && height == outHeight)
    {
        scaled.swap(rgba);
    }
    else
    {
        scaled.resize(static_cast<size_t>(outWidth) * static_cast<size_t>(outHeight) * 4);
        for (uint32_t y = 0; y < outHeight; ++y)
        {
            const uint32_t srcY = static_cast<uint32_t>((static_cast<uint64_t>(y) * height) / outHeight);
            for (uint32_t x = 0; x < outWidth; ++x)
            {
                const uint32_t srcX = static_cast<uint32_t>((static_cast<uint64_t>(x) * width) / outWidth);
                const size_t srcIdx = (static_cast<size_t>(srcY) * width + srcX) * 4;
                const size_t dstIdx = (static_cast<size_t>(y) * outWidth + x) * 4;
                scaled[dstIdx] = rgba[srcIdx];
                scaled[dstIdx + 1] = rgba[srcIdx + 1];
                scaled[dstIdx + 2] = rgba[srcIdx + 2];
                scaled[dstIdx + 3] = rgba[srcIdx + 3];
            }
        }
    }

    const uint32_t rowPitch = outWidth * 4;
    const bool saved = imaging->saveToFile(
        scaled.data(), outWidth, outHeight, rowPitch, carb::imaging::DataFormat::eRGBA8_UNORM, outputPath, 0);
    if (!saved)
    {
        const char* error = imaging->getErrorMessage();
        OMNI_LOG_WARN(kExtChannel, "texture icon: failed to save '%s': %s", outputPath, error ? error : "unknown");
    }

    imaging->destroyImage(image);
    return saved;
}
} // namespace materialGraph
} // namespace kit
} // namespace omni

void fillInterface(omni::kit::materialGraph::TextureUtilsPlugin& iface)
{
    // clang-format off
    // Bind public interface function pointers.
    iface =
    {
        omni::kit::materialGraph::GetTextureInfo,
        omni::kit::materialGraph::CreateTextureIcon
    };
    // clang-format on
}
// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <carb/Interface.h>

namespace omni
{
namespace kit
{
namespace materialGraph
{
// Interface for querying basic texture validity and channel count.
struct TextureUtilsPlugin
{
    CARB_PLUGIN_INTERFACE("omni::kit::materialGraph::TextureUtilsPlugin", 0, 1)

    // Attempts to load a url using carb::omniclient::IOmniClient and
    // carb::imaging::IImaging to determine if the image is readable by the
    // texturing system. Returns validity and, if valid, the channel count.
    void(CARB_ABI* get_texture_info)(const char* url, bool* valid, int32_t* channel_count);

    // Attempts to load a url and export a PNG icon to the output path.
    // Returns true if the icon was generated successfully.
    // size is the target square size (e.g. 64 for 64x64).
    bool(CARB_ABI* create_texture_icon)(const char* url, const char* output_path, int32_t size);
};
} // namespace materialGraph
} // namespace kit
} // namespace omni

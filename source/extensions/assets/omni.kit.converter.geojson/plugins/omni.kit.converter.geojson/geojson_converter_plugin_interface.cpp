// SPDX-FileCopyrightText: Copyright (c) 2019-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "UsdPCH.h"


#define CARB_EXPORTS

#include <carb/PluginUtils.h>
#include <carb/events/EventsUtils.h>
#include <carb/events/IEvents.h>
#include <carb/logging/Log.h>

#include <omni/kit/converter/geojson/geojson_converter_plugin_interface.h>

#include <geojson_converter_abi.hpp>
#include <memory>
#include <set>

#define EXTENSION_NAME "omni.kit.converter.geojson.plugin"

const struct carb::PluginImplDesc kPluginImpl = { EXTENSION_NAME,
                                                  "Example of a plugin extension which has API available in python.",
                                                  "NVIDIA", carb::PluginHotReload::eEnabled, "dev" };


CARB_PLUGIN_IMPL(kPluginImpl, omni::kit::converter::geojson::GeoJsonConverter)

namespace
{
carb::Framework* g_framework = nullptr;
uint32_t g_converter_ref_count = 0;
std::unique_ptr<omni::kit::converter::geojson::GeoJsonConverter> g_geoJsonConverter = nullptr;

int CARB_ABI Convert_GeoJSON_Interface(const char* stage_url, const char* folder_name, bool recursive)
{
    return geojson_converter_abi::Convert_GeoJSON_ABI(stage_url, folder_name, recursive);
}
} // namespace

CARB_EXPORT void carbOnPluginStartup()
{
    CARB_LOG_INFO("Startup GeoJSON Converter Extension");
    // Get app interface using Carbonite Framework
    g_framework = carb::getFramework();

    if (g_geoJsonConverter.get() == nullptr)
        g_geoJsonConverter = std::make_unique<omni::kit::converter::geojson::GeoJsonConverter>();

    g_converter_ref_count++;
}

CARB_EXPORT void carbOnPluginShutdown()
{
    CARB_LOG_INFO("Shutting Down GeoJSON Converter Interface");
    if (g_converter_ref_count == 1)
    {
        CARB_LOG_INFO("  Deleting interface");
        g_geoJsonConverter.reset(nullptr);
    }
    if (g_converter_ref_count > 0)
        g_converter_ref_count--;
    CARB_LOG_INFO("Done");
}

void fillInterface(omni::kit::converter::geojson::GeoJsonConverter& iface)
{
    using namespace omni::kit::converter::geojson;
    CARB_LOG_INFO("Filling GeoJSON Interface");
    memset(&iface, 0, sizeof(iface));

    iface.convert_geojson_python = Convert_GeoJSON_Interface;
}

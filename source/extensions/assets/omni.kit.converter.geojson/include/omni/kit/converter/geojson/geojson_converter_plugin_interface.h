// SPDX-FileCopyrightText: Copyright (c) 2019-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

//! @file
//!
//! @brief Example of Carbonite Interface exposed by C++ extension.
#pragma once


#include <carb/Interface.h>
#include <carb/events/IEvents.h>
// include header file that has actual function
// can
// #include

#include "geojson_converter/geojson_converter_abi.hpp"

namespace omni
{
namespace kit
{
namespace converter
{
namespace geojson
{
struct GeoJsonConverter
{
    CARB_PLUGIN_INTERFACE("omni::kit::converter::geojson::GeoJsonConverter", 0, 1)

    // exposed function here with return value
    // example: int(CARB_ABI* name_of_func)(const char* arg1, const char* arg2);

    // will require a class with exposed function
    // define function as an ABI
    // may need ABI decorators
    // need a namespace? only if it is in a wrapper class
    int(CARB_ABI* convert_geojson_python)(const char* stage_url, const char* folder_name, bool recursive);
};
} // namespace geojson
} // namespace converter
} // namespace kit
} // namespace omni

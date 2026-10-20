// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "geojson_converter_abi.hpp"

#include "UsdPCH.h"
#include "geojson_converter.h"

#define CARB_EXPORTS

namespace geojson_converter_abi
{
GeoJSON_Converter_ABI int Convert_GeoJSON_ABI(const char* stage_url, const char* folder_name, bool recursive)
{
    return Convert_GeoJSON_Source(stage_url, folder_name, recursive);
}
} // namespace geojson_converter_abi

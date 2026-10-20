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
#include "omni/kit/converter/geojson/geojson_converter_plugin_interface.h"

#include <carb/BindingsPythonUtils.h>

#include <geojson_converter/geojson_converter_abi.hpp>

// bring in header file for source code, see carb::defineInterfaceClass
CARB_BINDINGS("omni.kit.converter.geojson.python")

namespace omni
{
namespace kit
{
namespace converter
{
namespace geojson
{

}
} // namespace converter
} // namespace kit
} // namespace omni

namespace
{
// just 1 function that main will call in source code then expose for this file
// move logic into a function for main which will be also called here through binding
PYBIND11_MODULE(_geojson_converter, m)
{
    m.doc() = "pybind11 omni.kit.converter.geojson.GeoJsonConverter bindings";

    using namespace omni::kit::converter::geojson;

    carb::defineInterfaceClass<GeoJsonConverter>(m, "GeoJsonConverter", "acquire_interface", "release_interface")
        .def("convert_geojson_python", carb::wrapInterfaceFunction(&GeoJsonConverter::convert_geojson_python));
}
} // namespace

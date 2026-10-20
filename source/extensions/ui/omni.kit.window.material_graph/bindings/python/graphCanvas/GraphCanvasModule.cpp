// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include <carb/BindingsPythonUtils.h>

#include "BindingsForward.h"
#include "NativeBuildScene.h"

using namespace omni::kit::materialGraph;

CARB_BINDINGS("omni.kit.window.material_graph.graphCanvas.python")

namespace
{

PYBIND11_MODULE(_graphCanvas, m)
{
    m.doc() = "C++ GraphCanvasWidget, layout, and scene building for high-performance material graph.";

    m.def("set_perf_print", &setPerfPrint, py::arg("enabled"), "Enable/disable C++ perf timing prints.");
    m.def("get_perf_print", &getPerfPrint, "Return whether C++ perf timing prints are enabled.");
    m.def("set_color_noodles", &setColorNoodles, py::arg("enabled"), "Enable/disable port-colored connection noodles.");
    m.def("get_color_noodles", &getColorNoodles, "Return whether port-colored noodles are enabled.");

    registerNodeDataBindings(m);
    registerSceneDataBindings(m);
    registerGraphCanvasWidgetBindings(m);
    registerLayoutBindings(m);
}

} // namespace

// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include <carb/BindingsPythonUtils.h>

#include <omni/scenevisualization/ISceneVisualization.h>


CARB_BINDINGS("omni.scene.visualization.core.python")

namespace
{

PYBIND11_MODULE(_omni_scene_visualization_core, m)
{
    using namespace carb;
    using namespace omni::renderer;

    m.doc() = "pybind11 omni.scene.visualization.core bindings";

    defineInterfaceClass<ISceneDeclutter>(m, "Py_ISceneVisualizer", "acquire_interface", "release_interface")
        .def("toggle_points", [](ISceneDeclutter* self) { self->TogglePoints(); })
        .def("toggle_normals", [](ISceneDeclutter* self) { self->ToggleNormals(); })
        .def("toggle_wireframe", [](ISceneDeclutter* self) { self->ToggleWireframe(); })
        .def("toggle_tangents", [](ISceneDeclutter* self) { self->ToggleTangents(); })
        .def("toggle_vertex_color", [](ISceneDeclutter* self) { self->ToggleUseVertexColor(); });

    m.attr("pointWidthSettingName") = kSettingsPointWidth;
    m.attr("lineWidthSettingName") = kSettingsLineWidth;
    m.attr("applyToDescendantsSettingName") = kSettingsApplyToDescendants;
    m.attr("useSceneVisPrim") = kSettingsUseSceneVisPrim;
    m.attr("useWidthsPrimvar") = kSettingsUseWidthsPrimvar;
}
} // namespace

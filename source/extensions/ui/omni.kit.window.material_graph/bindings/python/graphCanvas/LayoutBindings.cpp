// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "BindingsForward.h"
#include "SugiyamaLayoutNative.h"
#include "NativeBuildScene.h"

#include <pybind11/stl.h>

using namespace omni::kit::materialGraph;

void registerLayoutBindings(py::module& m)
{
    py::class_<SugiyamaLayoutNative>(m, "SugiyamaLayoutNative")
        .def(py::init<const std::vector<std::pair<int, int>>&, float, float>(), py::arg("edges"),
             py::arg("vertical_distance") = 10.0f, py::arg("horizontal_distance") = 10.0f)
        .def("set_size", &SugiyamaLayoutNative::setSize, py::arg("vertex"), py::arg("width"), py::arg("height"))
        .def("update_positions", &SugiyamaLayoutNative::updatePositions)
        .def("pin_io_layers", &SugiyamaLayoutNative::pinIOLayers, py::arg("input_nodes"), py::arg("output_nodes"))
        .def(
            "get_position",
            [](SugiyamaLayoutNative& l, int v) -> py::object {
                auto pos = l.getPosition(v);
                if (!pos)
                    return py::none();
                return py::make_tuple(pos->first, pos->second);
            },
            py::arg("vertex"))
        .def(
            "get_layer",
            [](SugiyamaLayoutNative& l, int v) -> py::object {
                auto layer = l.getLayer(v);
                if (!layer)
                    return py::none();
                return py::int_(*layer);
            },
            py::arg("vertex"));

    py::class_<NativeBuildResult>(m, "NativeBuildResult")
        .def_readonly("scene", &NativeBuildResult::scene)
        .def_readonly("edges", &NativeBuildResult::edges)
        .def_readonly("visible_port_counts", &NativeBuildResult::visiblePortCounts)
        .def_readonly("model_nodes", &NativeBuildResult::modelNodes)
        .def_readonly("stable_ids", &NativeBuildResult::stableIds)
        .def_readonly("node_pos_x", &NativeBuildResult::nodePosX)
        .def_readonly("node_pos_y", &NativeBuildResult::nodePosY)
        .def_readonly("node_widths", &NativeBuildResult::nodeWidths)
        .def_readonly("node_heights", &NativeBuildResult::nodeHeights)
        .def_readonly("node_port_start_y", &NativeBuildResult::nodePortStartY);

    m.def("native_build_scene", &nativeBuildScene, py::arg("model"), py::arg("port_grouping"),
          "Build GraphScene + layout edges from a Python graph model in one native pass.");

    m.def("native_build_from_snapshot", &nativeBuildFromSnapshot, py::arg("snapshot"),
          "Build GraphScene from a pre-extracted Python snapshot (list of dicts).");
}

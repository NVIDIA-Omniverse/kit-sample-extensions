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
#include "SceneData.h"

using namespace omni::kit::materialGraph;

void registerSceneDataBindings(py::module& m)
{
    py::class_<SceneNodeEntry>(m, "SceneNodeEntry")
        .def(py::init<>())
        .def_readwrite("stable_id", &SceneNodeEntry::stableId)
        .def_readwrite("data", &SceneNodeEntry::data)
        .def_readwrite("pos_x", &SceneNodeEntry::posX)
        .def_readwrite("pos_y", &SceneNodeEntry::posY);

    py::class_<SceneConnectionEntry>(m, "SceneConnectionEntry")
        .def(py::init<>())
        .def_readwrite("source_node_id", &SceneConnectionEntry::sourceNodeId)
        .def_readwrite("source_port_index", &SceneConnectionEntry::sourcePortIndex)
        .def_readwrite("target_node_id", &SceneConnectionEntry::targetNodeId)
        .def_readwrite("target_port_index", &SceneConnectionEntry::targetPortIndex)
        .def_readwrite("color", &SceneConnectionEntry::color)
        .def_readwrite("thickness", &SceneConnectionEntry::thickness)
        .def_readwrite("reversed", &SceneConnectionEntry::reversed)
        .def_readwrite("valid", &SceneConnectionEntry::valid);

    py::class_<GraphScene>(m, "GraphScene")
        .def(py::init<>())
        .def_readwrite("nodes", &GraphScene::nodes)
        .def_readwrite("connections", &GraphScene::connections);

    py::enum_<HitType>(m, "HitType")
        .value("NONE", HitType::NONE)
        .value("NODE_BODY", HitType::NODE_BODY)
        .value("NODE_HEADER", HitType::NODE_HEADER)
        .value("PORT_INPUT", HitType::PORT_INPUT)
        .value("PORT_OUTPUT", HitType::PORT_OUTPUT)
        .value("CONNECTION", HitType::CONNECTION)
        .value("BACKDROP_RESIZE", HitType::BACKDROP_RESIZE)
        .value("BACKDROP_COLOR_SWATCH", HitType::BACKDROP_COLOR_SWATCH)
        .value("INPUT_NODE_MODE_TOGGLE", HitType::INPUT_NODE_MODE_TOGGLE);

    py::class_<HitResult>(m, "HitResult")
        .def(py::init<>())
        .def_readonly("type", &HitResult::type)
        .def_readonly("node_id", &HitResult::nodeId)
        .def_readonly("port_index", &HitResult::portIndex)
        .def_readonly("connection_index", &HitResult::connectionIndex);
}

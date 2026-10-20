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
#include "NodeData.h"

using namespace omni::kit::materialGraph;

void registerNodeDataBindings(py::module& m)
{
    py::class_<PortData>(m, "PortData")
        .def(py::init<>())
        .def_readwrite("name", &PortData::name)
        .def_readwrite("type_name", &PortData::typeName)
        .def_readwrite("is_input", &PortData::isInput)
        .def_readwrite("is_output", &PortData::isOutput)
        .def_readwrite("is_group", &PortData::isGroup)
        .def_readwrite("is_empty", &PortData::isEmpty)
        .def_readwrite("is_expanded", &PortData::isExpanded)
        .def_readwrite("connected_source", &PortData::connectedSource)
        .def_readwrite("connected_target", &PortData::connectedTarget)
        .def_readwrite("level", &PortData::level)
        .def_readwrite("child_count", &PortData::childCount)
        .def_readwrite("relative_position", &PortData::relativePosition)
        .def_readwrite("parent_child_count", &PortData::parentChildCount)
        .def_readwrite("color", &PortData::color)
        .def_readwrite("is_polymorphic", &PortData::isPolymorphic)
        .def_readwrite("is_resolved", &PortData::isResolved)
        .def_readwrite("is_uniform", &PortData::isUniform)
        .def_readwrite("is_interface_only", &PortData::isInterfaceOnly)
        .def_readwrite("io_state", &PortData::ioState)
        .def_readwrite("is_group_header", &PortData::isGroupHeader)
        .def_readwrite("group_port_count", &PortData::groupPortCount)
        .def_readwrite("group_collapsed", &PortData::groupCollapsed)
        .def_readwrite("is_hidden", &PortData::isHidden)
        .def_readwrite("has_error", &PortData::hasError);

    py::class_<NodeData>(m, "NodeData")
        .def(py::init<>())
        .def_readwrite("name", &NodeData::name)
        .def_readwrite("type_name", &NodeData::typeName)
        .def_readwrite("icon_url", &NodeData::iconUrl)
        .def_readwrite("description", &NodeData::description)
        .def_readwrite("background_color", &NodeData::backgroundColor)
        .def_readwrite("header_color", &NodeData::headerColor)
        .def_readwrite("border_color", &NodeData::borderColor)
        .def_readwrite("text_color", &NodeData::textColor)
        .def_readwrite("node_width", &NodeData::nodeWidth)
        .def_readwrite("node_height", &NodeData::nodeHeight)
        .def_readwrite("stacking_order", &NodeData::stackingOrder)
        .def_readwrite("expansion_state", &NodeData::expansionState)
        .def_readwrite("selected", &NodeData::selected)
        .def_readwrite("valid_state", &NodeData::validState)
        .def_readwrite("is_backdrop", &NodeData::isBackdrop)
        .def_readwrite("is_interface", &NodeData::isInterface)
        .def_readwrite("is_polymorphic", &NodeData::isPolymorphic)
        .def_readwrite("is_resolved", &NodeData::isResolved)
        .def_readwrite("has_menu", &NodeData::hasMenu)
        .def_readwrite("ports", &NodeData::ports)
        .def_readwrite("is_input_node", &NodeData::isInputNode)
        .def_readwrite("view_mode", &NodeData::viewMode)
        .def_readwrite("preview_url", &NodeData::previewUrl);
}

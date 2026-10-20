// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Data structures describing individual ports and nodes for the native graph
// canvas renderer.  These are populated from the Python snapshot (or live
// model) in NativeBuildScene and consumed by GraphCanvasNodeDraw for rendering.

#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Describes a single port (input, output, or group header) on a node.
// Populated during snapshot deserialization and used by the draw routines
// to render port circles, labels, connection dots, and error indicators.
struct PortData
{
    std::string name; // Display name of the port
    std::string typeName; // USD/SDR type name (e.g. "float", "color3f")
    bool isInput = false; // Port accepts incoming connections
    bool isOutput = false; // Port provides outgoing connections
    bool isGroup = false; // Collapsible group header (not a real port)
    bool isEmpty = false; // Placeholder "Add Port" entry
    bool isExpanded = true; // Group expansion state (open/closed)
    bool connectedSource = false; // Has at least one outgoing connection
    bool connectedTarget = false; // Has at least one incoming connection
    bool isPolymorphic = false; // Port belongs to a polymorphic node
    bool isResolved = true; // Polymorphic type is fully resolved
    bool isUniform = false; // USD uniform variability (rendered as square)
    bool isInterfaceOnly = false; // USD interfaceOnly connectability
    int level = 0; // Nesting depth in group hierarchy
    int childCount = 0; // Number of direct children (for groups)
    int relativePosition = 0; // Index among siblings at this level
    int parentChildCount = 0; // Sibling count of parent group
    uint32_t color = 0xFFAAAAAA; // Port circle fill color (ABGR)

    // InputNode-specific fields for readability grouping
    int ioState = 0; // 0=active in current context, 1=used in other contexts, 2=unused
    bool isGroupHeader = false; // Synthetic group header for InputNode port categories
    int groupPortCount = 0; // Port count displayed in group header label
    bool groupCollapsed = false; // Whether the InputNode group is collapsed
    bool isHidden = false; // Hidden port (zero height, still anchors connections)
    bool hasError = false; // Port is involved in an invalid connection
};

// Describes a single node in the graph canvas scene.
// Contains all visual properties, port list, and state flags needed
// for rendering by GraphCanvasNodeDraw.
struct NodeData
{
    std::string name; // Display name shown in node header
    std::string typeName; // Shader/node type identifier
    std::string iconUrl; // Path to node icon texture (SVG/PNG)
    std::string description; // Tooltip/description text (backdrops)
    uint32_t backgroundColor = 0xFF393939; // Node body fill (ABGR)
    uint32_t headerColor = 0xFF4F4F4F; // Header region fill (ABGR)
    uint32_t borderColor = 0xFF606060; // Node border stroke (ABGR)
    uint32_t textColor = 0xFFFFFFFF; // Header text color (ABGR)
    float nodeWidth = 200.0f; // Node width in canvas units
    float nodeHeight = 0.0f; // Node height (0 = auto-computed from ports)
    int stackingOrder = 0; // Z-order for backdrop layering
    int expansionState = 0; // 0=open, 1=minimized, 2=closed
    bool selected = false; // Node is part of the current selection
    int validState = 0; // 0=valid, 1=warning (yellow fringe), 2=error (red fringe)
    bool isBackdrop = false; // Node is a Backdrop (special rendering)
    bool isInterface = false; // Node is an interface/container type
    bool isPolymorphic = false; // Node has polymorphic type resolution
    bool isResolved = true; // Polymorphic type is fully resolved
    bool hasMenu = false; // Node has a right-click context menu
    std::vector<PortData> ports; // Ordered list of visible ports

    // InputNode-specific fields
    bool isInputNode = false; // Node is the material's InputNode
    int viewMode = 0; // 0=CURRENT_CONTEXT, 1=ALL_USED, 2=ALL_PORTS

    // Texture preview (displayed below node body for texture nodes)
    std::string previewUrl;
};

} // namespace materialGraph
} // namespace kit
} // namespace omni

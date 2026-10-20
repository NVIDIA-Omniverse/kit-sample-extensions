// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Scene-level data structures for the graph canvas renderer.
// A GraphScene holds all positioned nodes and connections that make up
// one frame of the graph.  Built by NativeBuildScene and consumed by
// GraphCanvasWidget for rendering and hit-testing.

#pragma once

#include "NodeData.h"

#include <cstdint>
#include <vector>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// A node placed in the scene at a specific canvas position.
// The stableId is a persistent identifier that survives graph rebuilds,
// used for selection, animation, and Python-side cross-referencing.
struct SceneNodeEntry
{
    uint32_t stableId = 0; // Persistent node identifier
    NodeData data; // Visual and structural node properties
    float posX = 0.0f; // Canvas X position (top-left)
    float posY = 0.0f; // Canvas Y position (top-left)
};

// A connection (noodle/edge) between two ports in the scene.
// Source is typically an output port; target is typically an input port.
struct SceneConnectionEntry
{
    uint32_t sourceNodeId = 0; // StableId of the source node
    int sourcePortIndex = -1; // Visible port index on the source node
    uint32_t targetNodeId = 0; // StableId of the target node
    int targetPortIndex = -1; // Visible port index on the target node
    uint32_t color = 0xFFAAAAAA; // Connection color (ABGR), may follow source port type
    float thickness = 2.0f; // Stroke thickness in canvas units
    bool reversed = false; // Draw direction is swapped (target -> source)
    bool valid = true; // False if this connection has a validation error
};

// Complete graph scene for one frame: all nodes and connections.
// Passed to GraphCanvasWidget::setScene() for rendering.
struct GraphScene
{
    std::vector<SceneNodeEntry> nodes;
    std::vector<SceneConnectionEntry> connections;
};

// Types of elements that can be hit-tested in the canvas.
// Returned by GraphCanvasWidget::hitTest().
enum class HitType : int
{
    NONE = 0, // No element hit
    NODE_BODY = 1, // Node body area
    NODE_HEADER = 2, // Node header bar
    PORT_INPUT = 3, // Input port circle
    PORT_OUTPUT = 4, // Output port circle
    CONNECTION = 5, // Connection spline
    BACKDROP_RESIZE = 6, // Backdrop resize handle
    BACKDROP_COLOR_SWATCH = 7, // Backdrop color swatch
    INPUT_NODE_MODE_TOGGLE = 8 // InputNode view mode toggle
};

// Result of a hit-test query at a screen position.
struct HitResult
{
    HitType type = HitType::NONE; // What was hit
    uint32_t nodeId = 0; // StableId of the hit node (0 if none)
    int portIndex = -1; // Port index if a port was hit (-1 if none)
    int connectionIndex = -1; // Connection index if a spline was hit (-1 if none)
};

} // namespace materialGraph
} // namespace kit
} // namespace omni

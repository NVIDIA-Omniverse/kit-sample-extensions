// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Layout constants and helper functions for computing node geometry.
// Used by both GraphCanvasNodeDraw (rendering) and NativeBuildScene
// (snapshot deserialization) to ensure consistent sizing.

#pragma once

#include "NodeData.h"

namespace omni
{
namespace kit
{
namespace materialGraph
{

// ---- Standard node layout constants ----
static constexpr float kBodyInset = 8.0f; // Top inset when node has output ports
static constexpr float kBodyInsetNoOut = 16.0f; // Top inset when node has no output ports
static constexpr float kBottomInsetNoOut = 10.0f; // Bottom inset when node has no output ports
static constexpr float kNoPortHeaderBoost = 4.0f; // Extra header height for portless nodes
static constexpr float kMinBodyHeight = 14.0f; // Minimum node body height
static constexpr int kNoPortBodyDarken = 8; // Darken amount for portless node bodies
static constexpr float kHeaderH = 24.0f; // Standard header height

// ---- InputNode compact layout constants ----
static constexpr float kInputNodePortHeight = 16.0f; // Row height for InputNode ports
static constexpr float kInputNodeGroupHeaderHeight = 18.0f; // Row height for InputNode group headers
static constexpr float kInputNodeBodyTopInset = 18.0f; // Top inset above first InputNode port
static constexpr float kInputNodeBodyBottomInset = 4.0f; // Bottom inset below last InputNode port

// Returns true if the node has at least one visible output port.
inline bool nodeHasOutputPort(const NodeData& data)
{
    for (const auto& p : data.ports)
        if (p.isOutput && !p.isGroup && !p.isEmpty)
            return true;
    return false;
}

// Compute the top inset (gap between header and first port) for a standard node.
inline float bodyTopInsetForNode(const NodeData& data)
{
    float base = nodeHasOutputPort(data) ? kBodyInset : kBodyInsetNoOut;
    int realPorts = 0;
    for (const auto& p : data.ports)
        if (!p.isGroup)
            ++realPorts;
    if (realPorts > 0 && realPorts <= 3)
        base += 1.5f;
    return base;
}

// Compute the bottom inset (gap below last port) for a standard node.
inline float bodyBottomInsetForNode(const NodeData& data)
{
    return nodeHasOutputPort(data) ? 4.0f : kBottomInsetNoOut;
}

// Return the header height for any node.
inline float headerHeightForNode(const NodeData& data)
{
    (void)data;
    return kHeaderH;
}

// Return the height of a single port row, accounting for InputNode compact layout.
// Hidden ports return 0; group headers and empty ports have distinct heights.
inline float portHeightForNode(const NodeData& data, int portIndex)
{
    if (!data.isInputNode)
        return 22.0f;
    if (portIndex >= 0 && portIndex < static_cast<int>(data.ports.size()))
    {
        const auto& p = data.ports[portIndex];
        if (p.isHidden)
            return 0.0f;
        if (p.isGroupHeader)
            return kInputNodeGroupHeaderHeight;
        if (p.isEmpty)
            return 22.0f;
        if (p.isGroup)
            return kInputNodeGroupHeaderHeight;
    }
    return kInputNodePortHeight;
}

// Sum the total port area height for an InputNode (variable row heights).
inline float inputNodePortAreaHeight(const NodeData& data)
{
    float total = 0.0f;
    for (int i = 0; i < static_cast<int>(data.ports.size()); ++i)
        total += portHeightForNode(data, i);
    return total;
}

// Return the top inset for InputNode port area.
inline float bodyTopInsetForInputNode()
{
    return kInputNodeBodyTopInset;
}

// Return the bottom inset for InputNode port area.
inline float bodyBottomInsetForInputNode()
{
    return kInputNodeBodyBottomInset;
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Native scene builder: converts Python graph model data (live model or
// pre-extracted snapshot dicts) into a GraphScene + layout edges in a
// single C++ pass for maximum performance.

#pragma once

#include "SceneData.h"

#include <pybind11/pybind11.h>

#include <utility>
#include <vector>

namespace py = pybind11;

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Result of a native scene build.  Contains the renderable scene,
// layout edges for Sugiyama, per-node metadata for Python-side
// hit-testing, and visible port counts.
struct NativeBuildResult
{
    GraphScene scene; // Positioned nodes + connections for rendering
    std::vector<std::pair<int, int>> edges; // Directed edges (target, source) for layout
    std::vector<int> visiblePortCounts; // Number of visible ports per node
    std::vector<py::object> modelNodes; // Python model node objects (for cross-referencing)

    // Per-node arrays for Python hit-testing (avoids repeated pybind11 attribute access)
    std::vector<uint32_t> stableIds;
    std::vector<float> nodePosX;
    std::vector<float> nodePosY;
    std::vector<float> nodeWidths;
    std::vector<float> nodeHeights;
    std::vector<float> nodePortStartY;
};

// Build a GraphScene from a live Python graph model, walking nodes/ports/connections.
NativeBuildResult nativeBuildScene(py::object model, bool portGrouping);

// Build a GraphScene from a pre-extracted Python snapshot (list of node dicts).
// This is the primary build path used by the material graph editor.
NativeBuildResult nativeBuildFromSnapshot(py::list snapshot);

// Enable/disable performance timing prints to stdout.
void setPerfPrint(bool enabled);
bool getPerfPrint();

// Enable/disable port-type-colored connection noodles.
void setColorNoodles(bool enabled);
bool getColorNoodles();

} // namespace materialGraph
} // namespace kit
} // namespace omni

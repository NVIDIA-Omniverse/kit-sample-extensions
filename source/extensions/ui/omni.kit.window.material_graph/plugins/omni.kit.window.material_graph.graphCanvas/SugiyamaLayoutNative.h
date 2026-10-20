// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <cstdint>
#include <optional>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Runs Sugiyama-style layout: layering, crossing reduction, and coordinate assignment for a graph given as edges.
class SugiyamaLayoutNative
{
public:
    // Builds the layout state from directed edges (from, to). Optional per-axis minimum spacing between layers and
    // nodes.
    SugiyamaLayoutNative(const std::vector<std::pair<int, int>>& edges,
                         float verticalDistance = 10.0f,
                         float horizontalDistance = 10.0f);

    // Records the drawn size of a vertex before positions are computed.
    void setSize(int vertex, float width, float height);
    // Recomputes node positions from the current graph, sizes, and pinning.
    void updatePositions();
    // Returns the laid-out (x, y) for a vertex, if it exists in the layout.
    std::optional<std::pair<float, float>> getPosition(int vertex) const;
    // Returns the assigned layer index for a vertex, if any.
    std::optional<int> getLayer(int vertex) const;
    // Pins input vertices to the top layer and output vertices to the bottom layer before layout.
    void pinIOLayers(const std::vector<int>& inputNodes, const std::vector<int>& outputNodes);

private:
    // Internal graph vertex: adjacency, layer assignment, dummy-node bookkeeping, and layout intermediates.
    struct Node
    {
        int id = 0;
        std::vector<int> upstream;
        std::vector<int> downstream;
        int layer = -1;
        bool isDummy = false;
        int indexInLayer = 0;
        float barycenter = 0.0f;
        float width = 0.0f;
        float height = 0.0f;
        std::pair<float, float> finalPosition = { 0.0f, 0.0f };
        bool hasFinalPosition = false;

        // Tarjan SCC fields
        bool isCurrentlyIterating = false;
        int highestIterationIndex = 0;
        int lowestIterationIndex = 0;

        // Brandes-Kopf alignment fields
        int root = 0;
        int horizontalAlignedTo = 0;
        int verticalAlignedTo = 0;
        std::optional<float> offset;
        std::optional<float> maxY;
        float bound[4] = { 0.0f, 0.0f, 0.0f, 0.0f };

        // Dummy edge tracking
        std::unordered_map<int, int> dummyNodes;
    };

    // Hash for undirected edge keys stored in unordered containers.
    struct PairHash
    {
        size_t operator()(const std::pair<int, int>& p) const
        {
            size_t h = std::hash<int>{}(p.first);
            h ^= std::hash<int>{}(p.second) + 0x9e3779b9 + (h << 6) + (h >> 2);
            return h;
        }
    };

    using EdgeSet = std::unordered_set<std::pair<int, int>, PairHash>;
    using DummyMap = std::unordered_map<std::pair<int, int>, std::unordered_map<int, int>, PairHash>;

    float m_verticalDistance;
    float m_horizontalDistance;
    int m_alignmentDirection = 0;
    int m_alignmentDirectionVertical = 1;
    int m_alignmentDirectionHorizontal = -1;
    int m_dummyCounter = -1;

    std::unordered_map<int, Node> m_nodes;
    std::unordered_map<int, std::vector<int>> m_layers;
    std::vector<EdgeSet> m_graphs;
    EdgeSet m_allEdges;
    DummyMap m_dummyMap;

    void setAlignmentDirection(int dir);
    void splitToGraphs();
    void layout();

    std::vector<Node*> getRoots(const EdgeSet& graph);
    std::vector<std::pair<int, int>> getReversedEdges(const EdgeSet& graph, const std::vector<Node*>& roots);
    void iterateNodeEdges(Node& node, int& counter, std::vector<Node*>& visited, std::vector<std::pair<int, int>>& reversed);
    void invertEdge(const std::pair<int, int>& edge);
    void setLayer(Node& node);
    void iterateLayer(const std::vector<Node*>& roots);
    void createDummies(const std::pair<int, int>& edge);
    Node& createDummy(int layer, std::unordered_map<int, int>& dummyNodes);

    std::vector<int> getNeighbors(Node& node);
    float getMeanValuePosition(Node& node);
    int getCrossCount(int layerId);
    int reduceCrossings(int layerId);
    void reorder(int layerId);
    void orderingPass(int direction);
    void horizontalAlignment();
    void alignSubnetwork(int vertex);
    void verticalAlignment();
};

} // namespace materialGraph
} // namespace kit
} // namespace omni

// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "SugiyamaLayoutNative.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Stores edge spacing, builds internal node/edge state from `edges`, splits into graphs, and runs layout.
SugiyamaLayoutNative::SugiyamaLayoutNative(const std::vector<std::pair<int, int>>& edges,
                                           float verticalDistance,
                                           float horizontalDistance)
    : m_verticalDistance(verticalDistance), m_horizontalDistance(horizontalDistance)
{
    setAlignmentDirection(0);
    for (const auto& e : edges)
        m_allEdges.insert(e);

    splitToGraphs();
    layout();
}

// Maps the abstract alignment quadrant `dir` to vertical/horizontal sign used by alignment passes.
void SugiyamaLayoutNative::setAlignmentDirection(int dir)
{
    m_alignmentDirection = dir;
    switch (dir)
    {
        case 0:
            m_alignmentDirectionVertical = 1;
            m_alignmentDirectionHorizontal = -1;
            break;
        case 1:
            m_alignmentDirectionVertical = -1;
            m_alignmentDirectionHorizontal = -1;
            break;
        case 2:
            m_alignmentDirectionVertical = 1;
            m_alignmentDirectionHorizontal = 1;
            break;
        case 3:
            m_alignmentDirectionVertical = -1;
            m_alignmentDirectionHorizontal = 1;
            break;
        default:
            m_alignmentDirectionVertical = 1;
            m_alignmentDirectionHorizontal = -1;
            break;
    }
}

// Partitions `m_allEdges` into connected components and fills `m_graphs` with per-component edge sets.
void SugiyamaLayoutNative::splitToGraphs()
{
    std::unordered_set<int> vertices;
    std::unordered_map<int, std::unordered_set<int>> deps;

    for (const auto& [v1, v2] : m_allEdges)
    {
        vertices.insert(v1);
        vertices.insert(v2);
        deps[v1].insert(v2);
        deps[v2].insert(v1);

        if (m_nodes.find(v1) == m_nodes.end())
        {
            Node n;
            n.id = v1;
            n.root = v1;
            n.horizontalAlignedTo = v1;
            n.verticalAlignedTo = v1;
            m_nodes[v1] = std::move(n);
        }
        if (m_nodes.find(v2) == m_nodes.end())
        {
            Node n;
            n.id = v2;
            n.root = v2;
            n.horizontalAlignedTo = v2;
            n.verticalAlignedTo = v2;
            m_nodes[v2] = std::move(n);
        }

        // A malformed self-connection still contributes a visible vertex, but
        // must not create cyclic adjacency that leaves the vertex unlayered.
        if (v1 == v2)
            continue;

        auto& n1 = m_nodes[v1];
        auto& n2 = m_nodes[v2];
        if (std::find(n1.upstream.begin(), n1.upstream.end(), v2) == n1.upstream.end())
            n1.upstream.push_back(v2);
        if (std::find(n2.downstream.begin(), n2.downstream.end(), v1) == n2.downstream.end())
            n2.downstream.push_back(v1);
    }

    while (!vertices.empty())
    {
        std::vector<int> component;
        component.push_back(*vertices.begin());
        vertices.erase(vertices.begin());

        for (size_t i = 0; i < component.size(); ++i)
        {
            int v = component[i];
            auto it = deps.find(v);
            if (it == deps.end())
                continue;
            for (int dep : it->second)
            {
                if (vertices.count(dep))
                {
                    vertices.erase(dep);
                    component.push_back(dep);
                }
            }
        }

        std::unordered_set<int> compSet(component.begin(), component.end());
        EdgeSet graphEdges;
        for (const auto& e : m_allEdges)
        {
            if (compSet.count(e.first) || compSet.count(e.second))
                graphEdges.insert(e);
        }
        m_graphs.push_back(std::move(graphEdges));
    }
}

// Returns nodes with no downstream neighbors in `graph` (sink-like roots for layering).
std::vector<SugiyamaLayoutNative::Node*> SugiyamaLayoutNative::getRoots(const EdgeSet& graph)
{
    std::vector<Node*> roots;
    for (const auto& e : graph)
    {
        auto& node = m_nodes[e.first];
        if (node.downstream.empty())
        {
            if (std::find_if(roots.begin(), roots.end(), [&](Node* n) { return n->id == node.id; }) == roots.end())
                roots.push_back(&node);
        }
    }
    return roots;
}

// DFS over upstream edges to assign iteration indices and record edges that must be reversed for acyclicity.
void SugiyamaLayoutNative::iterateNodeEdges(Node& node,
                                            int& counter,
                                            std::vector<Node*>& visited,
                                            std::vector<std::pair<int, int>>& reversed)
{
    counter++;
    node.highestIterationIndex = counter;
    node.lowestIterationIndex = counter;
    visited.push_back(&node);
    node.isCurrentlyIterating = true;

    for (int v : node.upstream)
    {
        auto& upstream = m_nodes[v];
        if (upstream.highestIterationIndex == 0)
        {
            iterateNodeEdges(upstream, counter, visited, reversed);
            node.lowestIterationIndex = std::min(node.lowestIterationIndex, upstream.lowestIterationIndex);
        }
        else if (upstream.isCurrentlyIterating)
        {
            reversed.emplace_back(node.id, upstream.id);
        }
        if (std::find_if(visited.begin(), visited.end(), [&](Node* n) { return n->id == upstream.id; }) != visited.end())
        {
            node.lowestIterationIndex = std::min(node.lowestIterationIndex, upstream.highestIterationIndex);
        }
    }

    if (node.lowestIterationIndex == node.highestIterationIndex)
    {
        while (!visited.empty() && visited.back()->id != node.id)
            visited.pop_back();
        if (!visited.empty())
            visited.pop_back();
    }
    node.isCurrentlyIterating = false;
}

// Finds a set of edges to flip so the graph can be layered; visits unvisited nodes after roots.
std::vector<std::pair<int, int>> SugiyamaLayoutNative::getReversedEdges(const EdgeSet& graph,
                                                                        const std::vector<Node*>& roots)
{
    int counter = 0;
    std::vector<Node*> visited;
    std::vector<std::pair<int, int>> reversed;

    for (auto& [v, node] : m_nodes)
        node.highestIterationIndex = 0;

    for (auto* root : roots)
        iterateNodeEdges(*root, counter, visited, reversed);

    for (const auto& e : graph)
    {
        for (int v : { e.first, e.second })
        {
            auto& node = m_nodes[v];
            if (node.highestIterationIndex == 0)
                iterateNodeEdges(node, counter, visited, reversed);
        }
    }
    return reversed;
}

// Swaps upstream/downstream roles for one edge in `m_nodes` adjacency lists.
void SugiyamaLayoutNative::invertEdge(const std::pair<int, int>& edge)
{
    auto& n1 = m_nodes[edge.first];
    auto& n2 = m_nodes[edge.second];
    n1.upstream.erase(std::remove(n1.upstream.begin(), n1.upstream.end(), edge.second), n1.upstream.end());
    n2.downstream.erase(std::remove(n2.downstream.begin(), n2.downstream.end(), edge.first), n2.downstream.end());

    if (std::find(n2.upstream.begin(), n2.upstream.end(), edge.first) == n2.upstream.end())
        n2.upstream.push_back(edge.first);
    if (std::find(n1.downstream.begin(), n1.downstream.end(), edge.second) == n1.downstream.end())
        n1.downstream.push_back(edge.second);
}

// Assigns `node` to a layer from downstream layers and updates `m_layers` membership.
void SugiyamaLayoutNative::setLayer(Node& node)
{
    int newLayer = 0;
    for (int d : node.downstream)
    {
        int dl = m_nodes[d].layer;
        if (dl >= 0)
            newLayer = std::max(newLayer, dl + 1);
        else
            newLayer = std::max(newLayer, 1);
    }
    if (newLayer == 0)
        newLayer = 1;

    if (node.layer == newLayer)
        return;

    if (node.layer >= 0)
    {
        auto& layer = m_layers[node.layer];
        layer.erase(std::remove(layer.begin(), layer.end(), node.id), layer.end());
    }

    node.layer = newLayer;
    m_layers[newLayer].push_back(node.id);
}

// BFS-style propagation from `roots`: layers nodes once all downstream scans toward upstream are done.
void SugiyamaLayoutNative::iterateLayer(const std::vector<Node*>& roots)
{
    std::unordered_set<std::pair<int, int>, PairHash> scannedEdges;
    std::vector<Node*> currentLayer(roots.begin(), roots.end());

    while (!currentLayer.empty())
    {
        std::vector<Node*> nextLayer;
        for (auto* node : currentLayer)
        {
            setLayer(*node);
            for (int v : node->upstream)
            {
                scannedEdges.insert({ node->id, v });
            }
            for (int x : node->upstream)
            {
                auto& upstream = m_nodes[x];
                bool allScanned = true;
                for (int d : upstream.downstream)
                {
                    if (scannedEdges.find({ d, upstream.id }) == scannedEdges.end())
                    {
                        allScanned = false;
                        break;
                    }
                }
                if (allScanned)
                {
                    if (std::find_if(nextLayer.begin(), nextLayer.end(), [&](Node* n) { return n->id == x; }) ==
                        nextLayer.end())
                        nextLayer.push_back(&upstream);
                }
            }
        }
        currentLayer = std::move(nextLayer);
    }
}

// Allocates a zero-size dummy node on `layer` and records the dummy chain in `dummyNodes`.
SugiyamaLayoutNative::Node& SugiyamaLayoutNative::createDummy(int layer, std::unordered_map<int, int>& dummyNodes)
{
    int id = m_dummyCounter--;
    Node dummy;
    dummy.id = id;
    dummy.isDummy = true;
    dummy.layer = layer;
    dummy.width = 0.0f;
    dummy.height = 0.0f;
    dummy.root = id;
    dummy.horizontalAlignedTo = id;
    dummy.verticalAlignedTo = id;
    dummy.dummyNodes = dummyNodes;
    m_nodes[id] = std::move(dummy);

    m_layers[layer].push_back(id);
    dummyNodes[layer] = id;
    auto& ref = m_nodes[id];
    ref.dummyNodes = dummyNodes;
    return ref;
}

// Inserts dummy nodes on each intermediate layer so this edge only spans adjacent layers.
void SugiyamaLayoutNative::createDummies(const std::pair<int, int>& edge)
{
    int v1 = edge.first, v2 = edge.second;
    int l1 = m_nodes[v1].layer, l2 = m_nodes[v2].layer;
    if (l1 > l2)
    {
        std::swap(v1, v2);
        std::swap(l1, l2);
    }
    if ((l2 - l1) <= 1)
        return;

    std::unordered_map<int, int> dummyNodes;
    dummyNodes[l1] = v1;
    dummyNodes[l2] = v2;

    auto& n1 = m_nodes[v1];
    auto& n2 = m_nodes[v2];
    n1.upstream.erase(std::remove(n1.upstream.begin(), n1.upstream.end(), v2), n1.upstream.end());
    n2.downstream.erase(std::remove(n2.downstream.begin(), n2.downstream.end(), v1), n2.downstream.end());

    int prevId = v1;
    for (int layerId = l1 + 1; layerId < l2; ++layerId)
    {
        auto& dummy = createDummy(layerId, dummyNodes);
        auto& prev = m_nodes[prevId];
        if (std::find(prev.upstream.begin(), prev.upstream.end(), dummy.id) == prev.upstream.end())
            prev.upstream.push_back(dummy.id);
        if (std::find(dummy.downstream.begin(), dummy.downstream.end(), prevId) == dummy.downstream.end())
            dummy.downstream.push_back(prevId);
        prevId = dummy.id;
    }

    auto& prev = m_nodes[prevId];
    if (std::find(prev.upstream.begin(), prev.upstream.end(), v2) == prev.upstream.end())
        prev.upstream.push_back(v2);
    if (std::find(n2.downstream.begin(), n2.downstream.end(), prevId) == n2.downstream.end())
        n2.downstream.push_back(prevId);

    m_dummyMap[edge] = std::move(dummyNodes);
}

// Neighbors on the adjacent layer for ordering; for dummies, follows the long-edge chain via `m_dummyMap`.
std::vector<int> SugiyamaLayoutNative::getNeighbors(Node& node)
{
    if (node.isDummy)
    {
        return (m_alignmentDirectionHorizontal == -1) ? node.downstream : node.upstream;
    }

    auto result = (m_alignmentDirectionHorizontal == -1) ? node.downstream : node.upstream;

    for (int direction : { -1, 1 })
    {
        int targetLayer = node.layer + direction;
        for (size_t i = 0; i < result.size(); ++i)
        {
            if (m_nodes.count(result[i]) && m_nodes[result[i]].layer == targetLayer)
                continue;

            auto edgeFwd = std::make_pair(node.id, result[i]);
            auto edgeRev = std::make_pair(result[i], node.id);
            auto dit = m_dummyMap.find(edgeFwd);
            if (dit == m_dummyMap.end())
                dit = m_dummyMap.find(edgeRev);
            if (dit != m_dummyMap.end())
            {
                auto dlit = dit->second.find(targetLayer);
                if (dlit != dit->second.end())
                    result[i] = dlit->second;
            }
        }
    }

    return result;
}

// Average barycenter of `node`'s neighbors, or the node's current barycenter if there are none.
float SugiyamaLayoutNative::getMeanValuePosition(Node& node)
{
    auto neighbors = getNeighbors(node);
    if (neighbors.empty())
        return node.barycenter;

    float sum = 0.0f;
    for (int v : neighbors)
    {
        if (m_nodes.count(v))
            sum += m_nodes[v].barycenter;
    }
    return sum / static_cast<float>(neighbors.size());
}

// Counts edge crossings implied by neighbor orderings for nodes in `layerId` (inversion count).
int SugiyamaLayoutNative::getCrossCount(int layerId)
{
    auto it = m_layers.find(layerId);
    if (it == m_layers.end())
        return 0;

    std::vector<int> neighborIndices;
    for (int v : it->second)
    {
        auto neighbors = getNeighbors(m_nodes[v]);
        std::vector<int> sorted;
        for (int n : neighbors)
        {
            if (m_nodes.count(n))
                sorted.push_back(m_nodes[n].indexInLayer);
        }
        std::sort(sorted.begin(), sorted.end());
        neighborIndices.insert(neighborIndices.end(), sorted.begin(), sorted.end());
    }

    std::vector<int> s;
    int count = 0;
    for (size_t i = 0; i < neighborIndices.size(); ++i)
    {
        auto pos = std::lower_bound(s.begin(), s.end(), neighborIndices[i]);
        int j = static_cast<int>(pos - s.begin());
        if (j < static_cast<int>(i))
            count += static_cast<int>(i) - j;
        s.insert(pos, neighborIndices[i]);
    }
    return count;
}

// Greedy adjacent swaps on `layerId` that lower crossing cost between neighbor barycenter sets.
int SugiyamaLayoutNative::reduceCrossings(int layerId)
{
    auto& layer = m_layers[layerId];
    int numNodes = static_cast<int>(layer.size());
    int totalCrossings = 0;

    for (int i = 0; i < numNodes - 1; ++i)
    {
        int vi = layer[i], vj = layer[i + 1];
        auto ni = getNeighbors(m_nodes[vi]);
        auto nj = getNeighbors(m_nodes[vj]);

        std::vector<float> bi, bj;
        for (int n : ni)
        {
            if (m_nodes.count(n))
                bi.push_back(m_nodes[n].barycenter);
        }
        for (int n : nj)
        {
            if (m_nodes.count(n))
                bj.push_back(m_nodes[n].barycenter);
        }

        int cij = 0, cji = 0;
        for (float b : bj)
        {
            int crossings = 0;
            for (float a : bi)
            {
                if (a > b)
                    crossings++;
            }
            cij += crossings;
            cji += static_cast<int>(bi.size()) - crossings;
        }

        if (cji < cij)
        {
            std::swap(layer[i], layer[i + 1]);
            totalCrossings += cji;
        }
        else
        {
            totalCrossings += cij;
        }
    }
    return totalCrossings;
}

// Sorts one layer by barycenter means, optionally reduces crossings, then refreshes indices and barycenters.
void SugiyamaLayoutNative::reorder(int layerId)
{
    auto& layer = m_layers[layerId];
    if (layer.empty())
        return;

    float baryHeight = (layer.size() > 1) ? 1.0f / (static_cast<float>(layer.size()) - 1.0f) : 1.0f;
    int c = getCrossCount(layerId);

    if (c > 0)
    {
        for (int v : layer)
            m_nodes[v].barycenter = getMeanValuePosition(m_nodes[v]);

        std::sort(
            layer.begin(), layer.end(), [this](int a, int b) { return m_nodes[a].barycenter < m_nodes[b].barycenter; });

        reduceCrossings(layerId);

        for (int i = 0; i < static_cast<int>(layer.size()); ++i)
        {
            m_nodes[layer[i]].indexInLayer = i;
            m_nodes[layer[i]].barycenter = static_cast<float>(i) * baryHeight;
        }
    }
}

// One sweep over layers (top-down or bottom-up per `direction`) updating alignment and order.
void SugiyamaLayoutNative::orderingPass(int direction)
{
    m_alignmentDirectionHorizontal = direction;
    // Mirror alignment direction calculation from Python
    int adv = m_alignmentDirectionVertical;
    m_alignmentDirection = (m_alignmentDirectionHorizontal + 1) + (1 - adv) / 2;
    setAlignmentDirection(m_alignmentDirection);

    std::vector<int> layerIds;
    for (auto& [lid, _] : m_layers)
        layerIds.push_back(lid);
    std::sort(layerIds.begin(), layerIds.end());

    if (direction == 1)
        std::reverse(layerIds.begin(), layerIds.end());

    for (int lid : layerIds)
        reorder(lid);
}

// Core pipeline: per connected graph, break cycles, assign layers, add dummies, then reorder.
void SugiyamaLayoutNative::layout()
{
    for (auto& graph : m_graphs)
    {
        auto roots = getRoots(graph);
        auto reversed = getReversedEdges(graph, roots);

        for (const auto& e : reversed)
            invertEdge(e);

        auto newRoots = getRoots(graph);
        for (auto* r : newRoots)
        {
            if (std::find_if(roots.begin(), roots.end(), [&](Node* n) { return n->id == r->id; }) == roots.end())
                roots.push_back(r);
        }

        iterateLayer(roots);

        for (const auto& e : graph)
            createDummies(e);
    }

    for (auto& [lid, layer] : m_layers)
    {
        float baryHeight = (layer.size() > 1) ? 1.0f / (static_cast<float>(layer.size()) - 1.0f) : 1.0f;
        for (int i = 0; i < static_cast<int>(layer.size()); ++i)
        {
            m_nodes[layer[i]].indexInLayer = i;
            m_nodes[layer[i]].barycenter = static_cast<float>(i) * baryHeight;
        }
    }

    for (int i = 0; i < 2; ++i)
    {
        orderingPass(-1);
        orderingPass(1);
    }
    orderingPass(-1);
}

// Aligns nodes horizontally to median positions of neighbors on the adjacent layer per current direction flags.
void SugiyamaLayoutNative::horizontalAlignment()
{
    std::vector<int> layerIds;
    for (auto& [lid, _] : m_layers)
        layerIds.push_back(lid);
    std::sort(layerIds.begin(), layerIds.end());

    if (m_alignmentDirectionHorizontal == 1)
        std::reverse(layerIds.begin(), layerIds.end());

    for (int layerId : layerIds)
    {
        int prevLayerId = layerId + ((m_alignmentDirectionHorizontal == 1) ? 1 : -1);
        if (m_layers.find(prevLayerId) == m_layers.end())
            continue;

        auto& layer = m_layers[layerId];
        auto& prevLayer = m_layers[prevLayerId];
        std::optional<int> currentVertexIndex;

        auto layerOrder = layer;
        if (m_alignmentDirectionVertical == -1)
            std::reverse(layerOrder.begin(), layerOrder.end());

        for (int vertex : layerOrder)
        {
            if (m_nodes[vertex].horizontalAlignedTo != vertex)
                continue;

            auto neighbors = getNeighbors(m_nodes[vertex]);
            std::vector<int> medianIndices;
            std::vector<int> indexInLayer;
            for (int n : neighbors)
            {
                if (m_nodes.count(n))
                    indexInLayer.push_back(m_nodes[n].indexInLayer);
            }
            if (indexInLayer.empty())
                continue;

            std::sort(indexInLayer.begin(), indexInLayer.end());
            if (m_alignmentDirectionVertical == -1)
                std::reverse(indexInLayer.begin(), indexInLayer.end());

            int sz = static_cast<int>(indexInLayer.size());
            int i = (sz - 1) / 2;
            int j = (sz - 1) % 2;
            medianIndices.push_back(indexInLayer[i]);
            if (j != 0 && i + 1 < sz)
                medianIndices.push_back(indexInLayer[i + 1]);

            for (int medianIdx : medianIndices)
            {
                if (medianIdx < 0 || medianIdx >= static_cast<int>(prevLayer.size()))
                    continue;

                if (m_nodes[vertex].horizontalAlignedTo != vertex)
                    break;

                int medianVertex = prevLayer[medianIdx];

                if (!currentVertexIndex.has_value() || (m_alignmentDirectionVertical * currentVertexIndex.value() <
                                                        m_alignmentDirectionVertical * medianIdx))
                {
                    m_nodes[medianVertex].horizontalAlignedTo = vertex;
                    int medianRoot = m_nodes[medianVertex].root;
                    m_nodes[vertex].horizontalAlignedTo = medianRoot;
                    m_nodes[vertex].root = medianRoot;
                    currentVertexIndex = medianIdx;
                }
            }
        }
    }
}

// Propagates vertical spacing along the horizontal alignment chain for `vertex`, merging offsets into roots.
void SugiyamaLayoutNative::alignSubnetwork(int vertex)
{
    if (m_nodes[vertex].maxY.has_value())
        return;

    m_nodes[vertex].maxY = 0.0f;
    int vtAlign = vertex;

    // Safety limit: the alignment chain should visit each node at most once.
    // If horizontalAlignedTo forms a cycle that excludes `vertex`, the
    // original while(true) loops forever.
    int maxIter = static_cast<int>(m_nodes.size()) + 1;

    for (int iter = 0; iter < maxIter; ++iter)
    {
        int prevIdx = m_nodes[vtAlign].indexInLayer - m_alignmentDirectionVertical;
        int layerId = m_nodes[vtAlign].layer;

        auto lit = m_layers.find(layerId);
        if (lit != m_layers.end() && prevIdx >= 0 && prevIdx < static_cast<int>(lit->second.size()))
        {
            int prevVertexId = lit->second[prevIdx];
            float vDist = m_verticalDistance + m_nodes[prevVertexId].height * 0.5f + m_nodes[vtAlign].height * 0.5f;

            int rootVertex = m_nodes[prevVertexId].root;
            alignSubnetwork(rootVertex);

            if (m_nodes[vertex].verticalAlignedTo == vertex)
                m_nodes[vertex].verticalAlignedTo = m_nodes[rootVertex].verticalAlignedTo;

            if (m_nodes[vertex].verticalAlignedTo == m_nodes[rootVertex].verticalAlignedTo)
            {
                m_nodes[vertex].maxY =
                    std::max(m_nodes[vertex].maxY.value(), m_nodes[rootVertex].maxY.value_or(0.0f) + vDist);
            }
            else
            {
                int alignedVertex = m_nodes[rootVertex].verticalAlignedTo;
                float off = m_nodes[vertex].maxY.value() - m_nodes[rootVertex].maxY.value_or(0.0f) + vDist;
                if (!m_nodes[alignedVertex].offset.has_value())
                    m_nodes[alignedVertex].offset = off;
                else
                    m_nodes[alignedVertex].offset = std::min(m_nodes[alignedVertex].offset.value(), off);
            }
        }

        vtAlign = m_nodes[vtAlign].horizontalAlignedTo;
        if (vtAlign == vertex)
            break;
    }
}

// Computes vertical bounds from alignment chains for the current `m_alignmentDirection`, then resets node link fields.
void SugiyamaLayoutNative::verticalAlignment()
{
    std::vector<int> layerIds;
    for (auto& [lid, _] : m_layers)
        layerIds.push_back(lid);
    std::sort(layerIds.begin(), layerIds.end());

    if (m_alignmentDirectionHorizontal == 1)
        std::reverse(layerIds.begin(), layerIds.end());

    for (int layerId : layerIds)
    {
        auto layerOrder = m_layers[layerId];
        if (m_alignmentDirectionVertical == -1)
            std::reverse(layerOrder.begin(), layerOrder.end());

        for (int vertex : layerOrder)
        {
            if (m_nodes[vertex].root == vertex)
                alignSubnetwork(vertex);
        }
    }

    if (m_alignmentDirectionVertical == -1)
    {
        for (int layerId : layerIds)
        {
            for (int vertex : m_layers[layerId])
            {
                if (m_nodes[vertex].maxY.has_value())
                    m_nodes[vertex].maxY = -m_nodes[vertex].maxY.value();
            }
        }
    }

    for (int layerId : layerIds)
    {
        auto layerOrder = m_layers[layerId];
        if (m_alignmentDirectionVertical == -1)
            std::reverse(layerOrder.begin(), layerOrder.end());

        for (int vertex : layerOrder)
        {
            m_nodes[vertex].bound[m_alignmentDirection] = m_nodes[m_nodes[vertex].root].maxY.value_or(0.0f);
            int alignedVertex = m_nodes[m_nodes[vertex].root].verticalAlignedTo;
            if (m_nodes[alignedVertex].offset.has_value())
            {
                m_nodes[vertex].bound[m_alignmentDirection] +=
                    m_alignmentDirectionVertical * m_nodes[alignedVertex].offset.value();
            }
        }
    }

    for (auto& [lid, layer] : m_layers)
    {
        for (int vertex : layer)
        {
            m_nodes[vertex].root = vertex;
            m_nodes[vertex].horizontalAlignedTo = vertex;
            m_nodes[vertex].verticalAlignedTo = vertex;
            m_nodes[vertex].offset.reset();
            m_nodes[vertex].maxY.reset();
        }
    }
}

// Sets or creates a node's width and height (creating a layer-0 node if missing).
void SugiyamaLayoutNative::setSize(int vertex, float width, float height)
{
    auto it = m_nodes.find(vertex);
    if (it == m_nodes.end())
    {
        Node node;
        node.id = vertex;
        node.layer = 0;
        node.root = vertex;
        node.horizontalAlignedTo = vertex;
        node.verticalAlignedTo = vertex;
        node.indexInLayer = static_cast<int>(m_layers[0].size());
        m_nodes[vertex] = std::move(node);
        m_layers[0].push_back(vertex);
        it = m_nodes.find(vertex);
    }
    it->second.width = width;
    it->second.height = height;
}

// Runs four alignment-direction passes, then assigns each node a final x/y from layer order and bounds median.
void SugiyamaLayoutNative::updatePositions()
{
    for (auto& [_, layer] : m_layers)
    {
        for (int vertex : layer)
        {
            auto& node = m_nodes[vertex];
            node.root = vertex;
            node.horizontalAlignedTo = vertex;
            node.verticalAlignedTo = vertex;
            node.offset.reset();
            node.maxY.reset();
            node.bound[0] = node.bound[1] = node.bound[2] = node.bound[3] = 0.0f;
        }
    }

    for (int ad = 0; ad < 4; ++ad)
    {
        setAlignmentDirection(ad);
        horizontalAlignment();
        verticalAlignment();
    }

    float xCounter = 0.0f;
    std::vector<int> layerIds;
    for (auto& [lid, _] : m_layers)
        layerIds.push_back(lid);
    std::sort(layerIds.begin(), layerIds.end());

    for (int lid : layerIds)
    {
        auto& layer = m_layers[lid];
        if (layer.empty())
            continue;

        float maxWidth = 0.0f;
        for (int v : layer)
            maxWidth = std::max(maxWidth, m_nodes[v].width * 0.5f);

        std::optional<float> yCounter;
        for (int vertex : layer)
        {
            auto& node = m_nodes[vertex];
            float b[4];
            std::copy(node.bound, node.bound + 4, b);
            std::sort(b, b + 4);
            float avgY = (b[1] + b[2]) * 0.5f;

            if (!yCounter.has_value())
                yCounter = avgY;
            yCounter = std::max(yCounter.value(), avgY);

            node.finalPosition = { -(xCounter + maxWidth), yCounter.value() };
            node.hasFinalPosition = true;

            yCounter = yCounter.value() + node.height + m_verticalDistance;
        }
        xCounter += 2.0f * maxWidth + m_horizontalDistance;
    }
}

// Returns the cached final position for `vertex` if layout has computed one.
std::optional<std::pair<float, float>> SugiyamaLayoutNative::getPosition(int vertex) const
{
    auto it = m_nodes.find(vertex);
    if (it != m_nodes.end() && it->second.hasFinalPosition)
        return it->second.finalPosition;
    return std::nullopt;
}

// Returns the assigned layer index for `vertex`, if any.
std::optional<int> SugiyamaLayoutNative::getLayer(int vertex) const
{
    auto it = m_nodes.find(vertex);
    if (it != m_nodes.end() && it->second.layer >= 0)
        return it->second.layer;
    return std::nullopt;
}

// Moves listed inputs to a layer above the stack and outputs below, for fixed IO placement.
void SugiyamaLayoutNative::pinIOLayers(const std::vector<int>& inputNodes, const std::vector<int>& outputNodes)
{
    if (inputNodes.empty() && outputNodes.empty())
        return;

    int minLayer = std::numeric_limits<int>::max();
    int maxLayer = std::numeric_limits<int>::min();
    for (const auto& [layerId, nodes] : m_layers)
    {
        if (!nodes.empty())
        {
            minLayer = std::min(minLayer, layerId);
            maxLayer = std::max(maxLayer, layerId);
        }
    }
    if (minLayer > maxLayer)
        return;

    auto moveNode = [&](int nodeId, int targetLayer) {
        auto it = m_nodes.find(nodeId);
        if (it == m_nodes.end())
            return;
        auto& node = it->second;
        if (node.layer >= 0)
        {
            auto& oldLayer = m_layers[node.layer];
            oldLayer.erase(std::remove(oldLayer.begin(), oldLayer.end(), nodeId), oldLayer.end());
        }
        node.layer = targetLayer;
        m_layers[targetLayer].push_back(nodeId);
    };

    int inputLayer = maxLayer + 1;
    int outputLayer = minLayer - 1;

    for (int id : inputNodes)
        moveNode(id, inputLayer);
    for (int id : outputNodes)
        moveNode(id, outputLayer);
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

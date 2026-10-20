// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "NodeData.h"
#include "PortColorSystem.h"
#include "GraphCanvasResourceUtils.h"
#include "SceneData.h"
#include "SugiyamaLayoutNative.h"

#include <carb/BindingsUtils.h>
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

using namespace omni::kit::materialGraph;

CARB_BINDINGS("omni.kit.window.material_graph.graphCanvas.tests")

namespace
{

void require(bool condition, const std::string& message)
{
    if (condition)
        CHECK(condition);
    else
        FAIL(message);
}

template <typename Actual, typename Expected>
void requireEqual(const Actual& actual, const Expected& expected, const std::string& message)
{
    if (actual == expected)
        CHECK(actual == expected);
    else
        FAIL(message);
}

void requireFinitePosition(const SugiyamaLayoutNative& layout, int vertex)
{
    const auto position = layout.getPosition(vertex);
    require(position.has_value(), "vertex " + std::to_string(vertex) + " has no position");
    require(std::isfinite(position->first), "vertex " + std::to_string(vertex) + " has a non-finite x position");
    require(std::isfinite(position->second), "vertex " + std::to_string(vertex) + " has a non-finite y position");
}

void sizeAndUpdate(SugiyamaLayoutNative& layout, const std::vector<int>& vertices)
{
    for (int vertex : vertices)
        layout.setSize(vertex, 120.0f + static_cast<float>(vertex % 3) * 10.0f, 40.0f);
    layout.updatePositions();
    for (int vertex : vertices)
        requireFinitePosition(layout, vertex);
}

void testTypeCategories()
{
    require(parseTypeCategory("color3f") == TypeCategory::COLOR, "color type category");
    require(parseTypeCategory("normal3f") == TypeCategory::VECTOR_SPATIAL, "normal type category");
    require(parseTypeCategory("vector4d") == TypeCategory::VECTOR_SPATIAL, "vector type category");
    require(parseTypeCategory("point3h") == TypeCategory::VECTOR_SPATIAL, "point type category");
    require(parseTypeCategory("texcoord2f") == TypeCategory::TEXTURE_COORD, "texcoord type category");
    require(parseTypeCategory("quatf") == TypeCategory::QUATERNION, "quaternion type category");
    require(parseTypeCategory("matrix4d") == TypeCategory::MATRIX, "matrix type category");
    require(parseTypeCategory("frame") == TypeCategory::FRAME, "frame type category");
    require(parseTypeCategory("bool") == TypeCategory::BOOLEAN, "boolean type category");
    require(parseTypeCategory("asset") == TypeCategory::ASSET, "asset type category");
    require(parseTypeCategory("token") == TypeCategory::STRING, "token type category");
    require(parseTypeCategory("uint") == TypeCategory::INTEGER, "integer type category");
    require(parseTypeCategory("double3") == TypeCategory::FLOAT_VECTOR, "floating vector type category");
    require(parseTypeCategory("half") == TypeCategory::FLOAT_SCALAR, "floating scalar type category");
    require(parseTypeCategory("edf") == TypeCategory::OTHER, "unknown type category");
}

void testTypeShapeParsing()
{
    requireEqual(extractDimension("float"), 1, "scalar dimension");
    requireEqual(extractDimension("float2"), 2, "suffix dimension");
    requireEqual(extractDimension("color3f"), 3, "USD precision-suffixed dimension");
    requireEqual(extractDimension("matrix4d"), 4, "matrix dimension");
    requireEqual(extractDimension("float3[]"), 3, "array element dimension");
    requireEqual(extractDimension("color3farray"), 3, "word-array element dimension");
    requireEqual(extractDimension("int64"), 1, "integer bit width is not a vector dimension");
    require(detectArray("float3[]"), "bracket array detection");
    require(detectArray("color3farray"), "word array detection");
    require(!detectArray("color3f"), "scalar must not be treated as array");
}

void testPrecisionParsing()
{
    require(detectPrecision("half3") == Precision::HALF, "half precision");
    require(detectPrecision("color3h_half") == Precision::HALF, "embedded half precision");
    require(detectPrecision("double4") == Precision::DOUBLE, "double precision");
    require(detectPrecision("matrix4d_double") == Precision::DOUBLE, "embedded double precision");
    require(detectPrecision("float3") == Precision::FLOAT, "float precision default");
}

void testHsvPacking()
{
    requireEqual(hsvToAbgr(0.0f, 1.0f, 1.0f), uint32_t{ 0xFF0000FF }, "red ABGR packing");
    requireEqual(hsvToAbgr(120.0f, 1.0f, 1.0f), uint32_t{ 0xFF00FF00 }, "green ABGR packing");
    requireEqual(hsvToAbgr(240.0f, 1.0f, 1.0f), uint32_t{ 0xFFFF0000 }, "blue ABGR packing");
    requireEqual(hsvToAbgr(-120.0f, 1.0f, 1.0f), hsvToAbgr(240.0f, 1.0f, 1.0f), "negative hue wrap");
    requireEqual(hsvToAbgr(360.0f, 1.0f, 1.0f, 0x7F), uint32_t{ 0x7F0000FF }, "alpha packing");
}

void testPortColorContracts()
{
    const uint32_t color = GetPortColorABGR("Color3F");
    requireEqual(color, GetPortColorABGR("color3f"), "port colors must be case-insensitive");
    requireEqual(color, GetPortColorABGR("color3f"), "port colors must be deterministic");
    require(color != GetPortColorABGR("color3f[]"), "arrays must be visually distinct from scalars");

    const uint32_t unknown = GetPortColorABGR("customSemanticType");
    const uint8_t red = static_cast<uint8_t>(unknown & 0xFF);
    const uint8_t green = static_cast<uint8_t>((unknown >> 8) & 0xFF);
    const uint8_t blue = static_cast<uint8_t>((unknown >> 16) & 0xFF);
    require(red == green && green == blue, "unknown semantic types must use neutral gray");
    requireEqual(static_cast<uint8_t>(unknown >> 24), uint8_t{ 0xFF }, "port colors must be opaque");
}

void testPortDataDefaults()
{
    const PortData port;
    require(port.name.empty() && port.typeName.empty(), "port strings must default empty");
    require(!port.isInput && !port.isOutput && !port.isGroup && !port.isEmpty, "port roles must default false");
    require(port.isExpanded && port.isResolved, "port resolution defaults");
    require(!port.connectedSource && !port.connectedTarget && !port.hasError, "port state defaults");
    requireEqual(port.level, 0, "port level default");
    requireEqual(port.color, uint32_t{ 0xFFAAAAAA }, "port color default");
}

void testNodeDataDefaults()
{
    const NodeData node;
    require(node.name.empty() && node.typeName.empty() && node.iconUrl.empty(), "node strings must default empty");
    requireEqual(node.nodeWidth, 200.0f, "node width default");
    requireEqual(node.nodeHeight, 0.0f, "node auto-height default");
    require(!node.selected && !node.isBackdrop && !node.isInterface, "node flags must default false");
    require(node.isResolved, "node must default resolved");
    requireEqual(node.validState, 0, "node validity default");
    require(node.ports.empty() && node.previewUrl.empty(), "node collections must default empty");
}

void testSceneDataDefaults()
{
    const GraphScene scene;
    require(scene.nodes.empty() && scene.connections.empty(), "scene must default empty");

    const SceneNodeEntry node;
    requireEqual(node.stableId, uint32_t{ 0 }, "scene node id default");
    requireEqual(node.posX, 0.0f, "scene node x default");
    requireEqual(node.posY, 0.0f, "scene node y default");

    const SceneConnectionEntry connection;
    requireEqual(connection.sourcePortIndex, -1, "source port index default");
    requireEqual(connection.targetPortIndex, -1, "target port index default");
    require(connection.valid && !connection.reversed, "connection validity defaults");

    const HitResult hit;
    require(hit.type == HitType::NONE, "hit type default");
    requireEqual(hit.portIndex, -1, "hit port default");
    requireEqual(hit.connectionIndex, -1, "hit connection default");
}

void testCheckedRgbaByteCount()
{
    size_t byteCount = 99;
    require(!checkedRgbaByteCount(0, 1, byteCount) && byteCount == 0, "zero width rejection");
    require(!checkedRgbaByteCount(1, -1, byteCount) && byteCount == 0, "negative height rejection");
    require(checkedRgbaByteCount(2, 3, byteCount), "valid icon dimensions");
    requireEqual(byteCount, size_t{ 24 }, "valid icon byte count");

    const bool largeAccepted = checkedRgbaByteCount(50000, 50000, byteCount);
    if (sizeof(size_t) >= 8)
    {
        require(largeAccepted, "64-bit byte count should not inherit signed-int overflow");
        requireEqual(byteCount, size_t{ 10000000000ULL }, "large icon byte count");
    }
    else
    {
        require(!largeAccepted && byteCount == 0, "32-bit byte count overflow rejection");
    }
}

void testEmptyLayout()
{
    SugiyamaLayoutNative layout({});
    layout.pinIOLayers({}, {});
    layout.updatePositions();
    require(!layout.getLayer(1).has_value(), "empty layout must not invent a layer");
    require(!layout.getPosition(1).has_value(), "empty layout must not invent a position");
}

void testIsolatedVertices()
{
    SugiyamaLayoutNative layout({}, 12.0f, 20.0f);
    layout.setSize(10, 100.0f, 30.0f);
    layout.setSize(20, 80.0f, 50.0f);
    layout.updatePositions();

    requireEqual(layout.getLayer(10).value_or(-1), 0, "isolated vertex layer");
    requireEqual(layout.getLayer(20).value_or(-1), 0, "second isolated vertex layer");
    requireFinitePosition(layout, 10);
    requireFinitePosition(layout, 20);
    const float separation = std::abs(layout.getPosition(10)->second - layout.getPosition(20)->second);
    require(separation >= 42.0f, "isolated vertices must respect height and vertical spacing");
}

void testSimpleEdge()
{
    SugiyamaLayoutNative layout({ { 1, 2 } });
    sizeAndUpdate(layout, { 1, 2 });
    require(layout.getLayer(1).has_value() && layout.getLayer(2).has_value(), "edge layers must exist");
    require(layout.getLayer(1) != layout.getLayer(2), "edge endpoints must occupy different layers");
    require(layout.getPosition(1)->first != layout.getPosition(2)->first, "edge endpoints must occupy different columns");
}

void testChainLayers()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 2, 3 }, { 3, 4 } });
    sizeAndUpdate(layout, { 1, 2, 3, 4 });
    std::vector<int> layers;
    for (int id : { 1, 2, 3, 4 })
        layers.push_back(layout.getLayer(id).value_or(-1));
    std::sort(layers.begin(), layers.end());
    require(std::adjacent_find(layers.begin(), layers.end()) == layers.end(), "chain vertices need distinct layers");
}

void testDiamondGraph()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 1, 3 }, { 2, 4 }, { 3, 4 } });
    sizeAndUpdate(layout, { 1, 2, 3, 4 });
    requireEqual(layout.getLayer(2).value_or(-1), layout.getLayer(3).value_or(-2), "diamond peers share a layer");
    require(layout.getPosition(2)->second != layout.getPosition(3)->second, "diamond peers must not overlap");
}

void testCycleLayout()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 2, 3 }, { 3, 1 } });
    sizeAndUpdate(layout, { 1, 2, 3 });
    for (int id : { 1, 2, 3 })
        require(layout.getLayer(id).has_value(), "cycle vertex must have a layer");
}

void testSelfLoopRemainsVisible()
{
    SugiyamaLayoutNative layout({ { 1, 1 } });
    sizeAndUpdate(layout, { 1 });
    require(layout.getLayer(1).has_value(), "self-connected vertex must remain in the layout");
}

void testDisconnectedGraphs()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 10, 11 }, { 11, 12 } });
    sizeAndUpdate(layout, { 1, 2, 10, 11, 12 });
    require(layout.getLayer(1) != layout.getLayer(2), "first component must be layered");
    require(layout.getLayer(10) != layout.getLayer(11), "second component must be layered");
}

void testDuplicateEdges()
{
    SugiyamaLayoutNative single({ { 1, 2 }, { 2, 3 } });
    SugiyamaLayoutNative duplicate({ { 1, 2 }, { 1, 2 }, { 2, 3 }, { 2, 3 } });
    sizeAndUpdate(single, { 1, 2, 3 });
    sizeAndUpdate(duplicate, { 1, 2, 3 });
    for (int id : { 1, 2, 3 })
    {
        requireEqual(single.getLayer(id).value_or(-1), duplicate.getLayer(id).value_or(-2), "duplicate edge layer");
        requireEqual(single.getPosition(id)->first, duplicate.getPosition(id)->first, "duplicate edge x position");
        requireEqual(single.getPosition(id)->second, duplicate.getPosition(id)->second, "duplicate edge y position");
    }
}

void testLongEdgeDummyLayout()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 2, 3 }, { 3, 4 }, { 1, 4 } });
    sizeAndUpdate(layout, { 1, 2, 3, 4 });
    require(!layout.getPosition(999).has_value(), "long-edge dummies must not invent public vertices");
}

void testPinnedIoLayers()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 2, 3 }, { 3, 4 } });
    std::vector<int> initialLayers;
    for (int id : { 1, 2, 3, 4 })
        initialLayers.push_back(layout.getLayer(id).value_or(0));
    const int minimum = *std::min_element(initialLayers.begin(), initialLayers.end());
    const int maximum = *std::max_element(initialLayers.begin(), initialLayers.end());

    layout.pinIOLayers({ 2 }, { 3 });
    requireEqual(layout.getLayer(2).value_or(0), maximum + 1, "input pin layer");
    requireEqual(layout.getLayer(3).value_or(0), minimum - 1, "output pin layer");
    sizeAndUpdate(layout, { 1, 2, 3, 4 });
}

void testUnknownPinsAreIgnored()
{
    SugiyamaLayoutNative layout({ { 1, 2 } });
    const auto layer1 = layout.getLayer(1);
    const auto layer2 = layout.getLayer(2);
    layout.pinIOLayers({ 999 }, { 998 });
    require(layout.getLayer(1) == layer1 && layout.getLayer(2) == layer2, "unknown pins must not move graph vertices");
    require(!layout.getLayer(999).has_value() && !layout.getLayer(998).has_value(), "unknown pins must not add vertices");
}

void testRepeatedPositionUpdateIsStable()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 1, 3 }, { 2, 4 }, { 3, 4 } });
    sizeAndUpdate(layout, { 1, 2, 3, 4 });
    std::vector<std::pair<float, float>> first;
    for (int id : { 1, 2, 3, 4 })
        first.push_back(*layout.getPosition(id));

    layout.updatePositions();
    for (size_t index = 0; index < first.size(); ++index)
        requireEqual(*layout.getPosition(static_cast<int>(index + 1)), first[index], "repeated layout position");
}

void testZeroSizedVerticesRemainFinite()
{
    SugiyamaLayoutNative layout({ { 1, 2 }, { 2, 3 } }, 0.0f, 0.0f);
    for (int id : { 1, 2, 3 })
        layout.setSize(id, 0.0f, 0.0f);
    layout.updatePositions();
    for (int id : { 1, 2, 3 })
        requireFinitePosition(layout, id);
}

void testLargeDag()
{
    constexpr int nodeCount = 120;
    std::vector<std::pair<int, int>> edges;
    for (int id = 1; id < nodeCount; ++id)
    {
        edges.emplace_back(id, id + 1);
        if (id + 3 <= nodeCount)
            edges.emplace_back(id, id + 3);
    }

    SugiyamaLayoutNative layout(edges, 8.0f, 12.0f);
    std::vector<int> vertices;
    for (int id = 1; id <= nodeCount; ++id)
        vertices.push_back(id);
    sizeAndUpdate(layout, vertices);
}

} // namespace

TEST_SUITE("omni.kit.window.material_graph.graphCanvas")
{
    TEST_CASE("port type categories")
    {
        testTypeCategories();
    }
    TEST_CASE("port type shape parsing")
    {
        testTypeShapeParsing();
    }
    TEST_CASE("port type precision")
    {
        testPrecisionParsing();
    }
    TEST_CASE("HSV ABGR packing")
    {
        testHsvPacking();
    }
    TEST_CASE("port color contracts")
    {
        testPortColorContracts();
    }
    TEST_CASE("port data defaults")
    {
        testPortDataDefaults();
    }
    TEST_CASE("node data defaults")
    {
        testNodeDataDefaults();
    }
    TEST_CASE("scene data defaults")
    {
        testSceneDataDefaults();
    }
    TEST_CASE("RGBA byte count")
    {
        testCheckedRgbaByteCount();
    }
    TEST_CASE("empty layout")
    {
        testEmptyLayout();
    }
    TEST_CASE("isolated vertices")
    {
        testIsolatedVertices();
    }
    TEST_CASE("simple edge")
    {
        testSimpleEdge();
    }
    TEST_CASE("chain layers")
    {
        testChainLayers();
    }
    TEST_CASE("diamond graph")
    {
        testDiamondGraph();
    }
    TEST_CASE("cycle layout")
    {
        testCycleLayout();
    }
    TEST_CASE("self loop remains visible")
    {
        testSelfLoopRemainsVisible();
    }
    TEST_CASE("disconnected graphs")
    {
        testDisconnectedGraphs();
    }
    TEST_CASE("duplicate edges")
    {
        testDuplicateEdges();
    }
    TEST_CASE("long edge dummy layout")
    {
        testLongEdgeDummyLayout();
    }
    TEST_CASE("pinned IO layers")
    {
        testPinnedIoLayers();
    }
    TEST_CASE("unknown pins are ignored")
    {
        testUnknownPinsAreIgnored();
    }
    TEST_CASE("repeated position update is stable")
    {
        testRepeatedPositionUpdateIsStable();
    }
    TEST_CASE("zero-sized vertices remain finite")
    {
        testZeroSizedVerticesRemainFinite();
    }
    TEST_CASE("large DAG")
    {
        testLargeDag();
    }
}

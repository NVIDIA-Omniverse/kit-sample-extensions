// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Native scene builder: deserializes Python graph data (live model or
// pre-extracted snapshot dicts) into NodeData/PortData/SceneConnectionEntry
// structures, builds the connection map from port input/output lists,
// computes node heights and port layout, and produces a NativeBuildResult
// containing the renderable GraphScene plus layout edges.

#include "NativeBuildScene.h"
#include "GraphCanvasLayout.h"
#include "PortColorSystem.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <exception>
#include <functional>
#include <omni/log/ILog.h>
#include <set>
#include <string>
#include <unordered_map>

OMNI_LOG_ADD_CHANNEL(kGraphCanvasChannel,
                     "omni.kit.window.material_graph",
                     "Messages related to the Material Graph native GraphCanvas scene builder.")

namespace omni
{
namespace kit
{
namespace materialGraph
{

static bool s_perfPrint = false;
static bool s_colorNoodles = false;

namespace
{
void reportUnexpectedNativeException(const char* action) noexcept
{
    try
    {
        throw;
    }
    catch (const py::error_already_set&)
    {
        // Missing/invalid optional Python snapshot fields are expected fallbacks.
    }
    catch (const py::cast_error&)
    {
        // Snapshot values from older Kit hosts may not support the preferred cast.
    }
    catch (const std::exception& exc)
    {
        OMNI_LOG_WARN(kGraphCanvasChannel, "native GraphCanvas %s failed: %s", action, exc.what());
    }
    catch (...)
    {
        OMNI_LOG_WARN(kGraphCanvasChannel, "native GraphCanvas %s failed with an unknown exception", action);
    }
}
} // namespace

void setPerfPrint(bool enabled)
{
    s_perfPrint = enabled;
}
bool getPerfPrint()
{
    return s_perfPrint;
}

void setColorNoodles(bool enabled)
{
    s_colorNoodles = enabled;
}
bool getColorNoodles()
{
    return s_colorNoodles;
}

// ---- Procedural port color system ----

static uint32_t colorForType(const std::string& typeName)
{
    return GetPortColorABGR(typeName);
}

static uint32_t tupleToAbgr(py::object color)
{
    if (color.is_none())
        return 0;

    try
    {
        double r = color[py::int_(0)].cast<double>();
        double g = color[py::int_(1)].cast<double>();
        double b = color[py::int_(2)].cast<double>();
        r = std::max(0.0, r);
        g = std::max(0.0, g);
        b = std::max(0.0, b);

        double mx = std::max({ r, g, b });
        if (mx > 1.0)
        {
            r /= mx;
            g /= mx;
            b /= mx;
        }

        int ri = static_cast<int>(std::round(r * 255.0));
        int gi = static_cast<int>(std::round(g * 255.0));
        int bi = static_cast<int>(std::round(b * 255.0));
        return (0xFFu << 24) | (static_cast<uint32_t>(bi) << 16) | (static_cast<uint32_t>(gi) << 8) |
               static_cast<uint32_t>(ri);
    }
    catch (...)
    {
        reportUnexpectedNativeException("color conversion");
        return 0;
    }
}

// ---- Helpers to safely read Python attributes ----

static std::string strAttr(py::object obj, const char* name)
{
    try
    {
        py::object val = obj.attr(name);
        if (val.is_none())
            return {};
        // Use py::str() to convert any Python object to string,
        // equivalent to str(val) in Python.
        return py::str(val).cast<std::string>();
    }
    catch (...)
    {
        reportUnexpectedNativeException("string attribute conversion");
        return {};
    }
}

static bool boolAttr(py::object obj, const char* name, bool def)
{
    try
    {
        return obj.attr(name).cast<bool>();
    }
    catch (...)
    {
        reportUnexpectedNativeException("boolean attribute conversion");
        return def;
    }
}

static int intAttr(py::object obj, const char* name, int def)
{
    try
    {
        py::object val = obj.attr(name);
        if (val.is_none())
            return def;
        // Try direct int cast first, then .value for Python enums
        try
        {
            return val.cast<int>();
        }
        catch (...)
        {
            reportUnexpectedNativeException("integer attribute conversion");
            try
            {
                return val.attr("value").cast<int>();
            }
            catch (...)
            {
                reportUnexpectedNativeException("enum value conversion");
                return def;
            }
        }
    }
    catch (...)
    {
        reportUnexpectedNativeException("integer attribute lookup");
        return def;
    }
}


// Per-port data captured during the node loop for the connection pass.
struct PortRecord
{
    py::object port; // original model port object
    int visiblePortIdx = -1; // visible port index within the node (for SceneConnectionEntry)
    std::vector<py::object> inputs;
    std::vector<py::object> outputs;
};

// Hashing for py::object keys (uses Python id())
struct PyObjHash
{
    size_t operator()(const py::object& o) const
    {
        return std::hash<void*>{}(o.ptr());
    }
};
struct PyObjEqual
{
    bool operator()(const py::object& a, const py::object& b) const
    {
        return a.ptr() == b.ptr();
    }
};

using PortMap = std::unordered_map<py::object, size_t, PyObjHash, PyObjEqual>;
using SourceTargetMap = std::unordered_map<py::object, std::vector<py::object>, PyObjHash, PyObjEqual>;

// Shared connection pass: builds sourceToTarget map from port records, then
// creates layout edges and SceneConnectionEntry objects in `result`.
static void buildConnections(const std::vector<PortRecord>& allPorts,
                             const PortMap& portToIdx,
                             const PortMap& portToNodeIdx,
                             NativeBuildResult& result)
{
    SourceTargetMap sourceToTarget;
    for (const auto& pr : allPorts)
    {
        for (const auto& src : pr.inputs)
            sourceToTarget[src].push_back(pr.port);
        for (const auto& src : pr.outputs)
            sourceToTarget[src].push_back(pr.port);
    }

    std::set<std::pair<int, int>> edgesSeenSorted;
    for (auto& [source, targets] : sourceToTarget)
    {
        auto srcIt = portToNodeIdx.find(source);
        if (srcIt == portToNodeIdx.end())
            continue;
        int srcNodeIdx = static_cast<int>(srcIt->second);

        auto srcPortIt = portToIdx.find(source);
        int srcVisPortIdx = (srcPortIt != portToIdx.end()) ? allPorts[srcPortIt->second].visiblePortIdx : 0;
        uint32_t srcStableId =
            (srcNodeIdx < static_cast<int>(result.scene.nodes.size())) ? result.scene.nodes[srcNodeIdx].stableId : 0;

        for (auto& target : targets)
        {
            auto tgtIt = portToNodeIdx.find(target);
            if (tgtIt == portToNodeIdx.end())
                continue;
            int tgtNodeIdx = static_cast<int>(tgtIt->second);

            int v1 = srcNodeIdx, v2 = tgtNodeIdx;
            if (v1 != v2)
            {
                auto es = (v1 < v2) ? std::make_pair(v1, v2) : std::make_pair(v2, v1);
                if (edgesSeenSorted.insert(es).second)
                    result.edges.emplace_back(v2, v1);
            }

            auto tgtPortIt = portToIdx.find(target);
            int tgtVisPortIdx = (tgtPortIt != portToIdx.end()) ? allPorts[tgtPortIt->second].visiblePortIdx : 0;
            uint32_t tgtStableId =
                (tgtNodeIdx < static_cast<int>(result.scene.nodes.size())) ? result.scene.nodes[tgtNodeIdx].stableId : 0;

            if (srcStableId != 0 && tgtStableId != 0)
            {
                SceneConnectionEntry ce;
                ce.sourceNodeId = srcStableId;
                ce.sourcePortIndex = srcVisPortIdx;
                ce.targetNodeId = tgtStableId;
                ce.targetPortIndex = tgtVisPortIdx;
                ce.color = 0xFFAAAAAA;
                if (s_colorNoodles && srcNodeIdx < static_cast<int>(result.scene.nodes.size()))
                {
                    const auto& ports = result.scene.nodes[srcNodeIdx].data.ports;
                    if (srcVisPortIdx >= 0 && srcVisPortIdx < static_cast<int>(ports.size()))
                        ce.color = ports[srcVisPortIdx].color;
                }
                ce.thickness = 2.0f;
                ce.reversed = false;

                bool srcErr = false, tgtErr = false;
                {
                    const auto& srcPorts = result.scene.nodes[srcNodeIdx].data.ports;
                    if (srcVisPortIdx >= 0 && srcVisPortIdx < static_cast<int>(srcPorts.size()))
                        srcErr = srcPorts[srcVisPortIdx].hasError;
                    const auto& tgtPorts = result.scene.nodes[tgtNodeIdx].data.ports;
                    if (tgtVisPortIdx >= 0 && tgtVisPortIdx < static_cast<int>(tgtPorts.size()))
                        tgtErr = tgtPorts[tgtVisPortIdx].hasError;
                }
                ce.valid = !(srcErr || tgtErr);

                result.scene.connections.push_back(std::move(ce));
            }
        }
    }
}

NativeBuildResult nativeBuildScene(py::object model, bool portGrouping)
{
    auto tStart = std::chrono::steady_clock::now();

    NativeBuildResult result;

    py::object nodesObj = model.attr("nodes");
    if (nodesObj.is_none())
        return result;

    py::list nodes(nodesObj);
    int numNodes = static_cast<int>(py::len(nodes));

    // Maps for the connection pass
    std::vector<PortRecord> allPorts;
    PortMap portToIdx; // port object → index in allPorts
    PortMap portToNodeIdx; // port object → node index
    uint32_t stableId = 1;

    // ==================== NODE LOOP ====================
    for (int ni = 0; ni < numNodes; ++ni)
    {
        py::object node = nodes[ni];
        py::object np = model[node];

        result.modelNodes.push_back(node);

        std::string nodeName = strAttr(np, "name");
        std::string nodeType = strAttr(np, "type");

        // ---- NodeData ----
        NodeData nd;
        nd.name = nodeName;
        nd.typeName = nodeType;

        py::object nodeSize = np.attr("size");
        try
        {
            if (!nodeSize.is_none())
            {
                float w = nodeSize[py::int_(0)].cast<float>();
                nd.nodeWidth = (w > 0.0f) ? w : 200.0f;
            }
        }
        catch (...)
        {
            reportUnexpectedNativeException("node size conversion");
        }

        py::object displayColor = np.attr("display_color");
        if (!displayColor.is_none())
        {
            uint32_t abgr = tupleToAbgr(displayColor);
            if (abgr != 0)
                nd.backgroundColor = abgr;
        }

        nd.selected = boolAttr(np, "selected", false);
        nd.validState = intAttr(np, "valid_state", boolAttr(np, "valid", true) ? 0 : 2);

        bool polyUnresolved = boolAttr(np, "polymorphic_unresolved", false);
        if (polyUnresolved)
        {
            nd.isPolymorphic = true;
            nd.isResolved = false;
        }

        // ---- Ports (recursive) ----
        py::object rootPorts = np.attr("ports");
        if (rootPorts.is_none())
            rootPorts = py::list();

        int visiblePortIdx = 0;
        // Recursive lambda via std::function
        std::function<void(py::list, int)> recurse = [&](py::list portList, int level) {
            int cnt = static_cast<int>(py::len(portList));
            for (int pid = 0; pid < cnt; ++pid)
            {
                py::object port = portList[pid];
                py::object pp = model[port];

                std::string portName = strAttr(pp, "name");
                std::string portType = strAttr(pp, "type");
                // Try alternative type attributes if primary is empty or a class name
                if (portType.empty() || portType.find("Model") != std::string::npos)
                {
                    std::string alt = strAttr(pp, "type_name");
                    if (!alt.empty())
                        portType = alt;
                }
                if (portType.empty() || portType.find("Model") != std::string::npos)
                {
                    std::string alt = strAttr(pp, "sdf_type");
                    if (!alt.empty())
                        portType = alt;
                }
                py::object portInputsObj = pp.attr("inputs");
                py::object portOutputsObj = pp.attr("outputs");
                py::object subPortsObj = pp.attr("ports");
                int portExp = intAttr(pp, "expansion_state", 0);

                bool hasInputs = !portInputsObj.is_none();
                bool hasOutputs = !portOutputsObj.is_none();

                std::vector<py::object> inputs, outputs;
                if (hasInputs)
                {
                    py::list inList(portInputsObj);
                    for (auto& item : inList)
                        inputs.push_back(py::reinterpret_borrow<py::object>(item));
                }
                if (hasOutputs)
                {
                    py::list outList(portOutputsObj);
                    for (auto& item : outList)
                        outputs.push_back(py::reinterpret_borrow<py::object>(item));
                }

                bool isGroup = portGrouping && !subPortsObj.is_none();
                int subCount = isGroup ? static_cast<int>(py::len(subPortsObj)) : 0;

                PortRecord rec;
                rec.port = port;
                rec.inputs = std::move(inputs);
                rec.outputs = std::move(outputs);
                rec.visiblePortIdx = visiblePortIdx++;

                size_t portIdx = allPorts.size();
                allPorts.push_back(std::move(rec));
                portToIdx[port] = portIdx;
                portToNodeIdx[port] = ni;

                // PortData for scene
                PortData pd;
                pd.name = portName;
                pd.typeName = portType;
                pd.isInput = hasInputs;
                pd.isOutput = hasOutputs;
                pd.level = level;
                pd.color = colorForType(portType);
                if (pd.color == 0xFFAAAAAA)
                    pd.color = 0xFF888888;

                pd.connectedTarget = hasInputs && !allPorts.back().inputs.empty();

                try
                {
                    if (py::hasattr(pp, "proxy_attribute"))
                    {
                        py::object proxy = pp.attr("proxy_attribute");
                        if (!proxy.is_none())
                        {
                            if (py::hasattr(proxy, "variability"))
                            {
                                std::string vs = py::str(proxy.attr("variability"));
                                pd.isUniform = (vs.find("Uniform") != std::string::npos);
                            }
                            if (py::hasattr(proxy, "connectability"))
                            {
                                std::string cs = py::str(proxy.attr("connectability"));
                                pd.isInterfaceOnly = (cs.find("interfaceOnly") != std::string::npos);
                            }
                        }
                    }
                }
                catch (...)
                {
                    reportUnexpectedNativeException("port metadata conversion");
                }

                pd.isGroup = isGroup && subCount > 0;
                if (pd.isGroup)
                    pd.color = 0xFFAAAA66;
                if (pd.isGroup)
                {
                    pd.isExpanded = (portExp == 0);
                    pd.childCount = subCount;
                }
                nd.ports.push_back(std::move(pd));

                if (isGroup && subCount > 0)
                {
                    if (portExp == 0)
                        recurse(py::list(subPortsObj), level + 1);
                }
            }
        };

        recurse(py::list(rootPorts), 0);

        // Propagate node-level polymorphic state to ports
        if (nd.isPolymorphic && !nd.isResolved)
        {
            for (auto& p : nd.ports)
            {
                if (!p.isGroup && !p.isEmpty)
                {
                    p.isPolymorphic = true;
                    p.isResolved = false;
                }
            }
        }

        result.visiblePortCounts.push_back(visiblePortIdx);

        {
            constexpr float kCharW = 7.5f;
            constexpr float kHeaderPad = 26.0f;
            constexpr float kPortPadL = 24.0f;
            constexpr float kPortPadR = 24.0f;
            float minW = static_cast<float>(nd.name.size()) * kCharW + kHeaderPad;
            for (const auto& p : nd.ports)
            {
                float pw = static_cast<float>(p.name.size()) * kCharW + kPortPadL + kPortPadR;
                if (pw > minW)
                    minW = pw;
            }
            if (minW > nd.nodeWidth)
                nd.nodeWidth = minW;
        }

        // ---- SceneNodeEntry ----
        SceneNodeEntry entry;
        entry.stableId = stableId++;
        entry.data = std::move(nd);

        py::object posObj = np.attr("position");
        if (!posObj.is_none())
        {
            try
            {
                entry.posX = posObj[py::int_(0)].cast<float>();
                entry.posY = posObj[py::int_(1)].cast<float>();
            }
            catch (...)
            {
                reportUnexpectedNativeException("model node position conversion");
            }
        }

        result.stableIds.push_back(entry.stableId);
        result.nodePosX.push_back(entry.posX);
        result.nodePosY.push_back(entry.posY);
        result.nodeWidths.push_back(entry.data.nodeWidth);
        bool hasOut = false;
        int realPorts = 0;
        bool hasEmpty = false;
        for (const auto& p : entry.data.ports)
        {
            if (p.isOutput && !p.isGroup && !p.isEmpty)
                hasOut = true;
            if (!p.isGroup)
                ++realPorts;
            if (p.isEmpty)
                hasEmpty = true;
        }
        entry.data.isInterface = hasEmpty;
        float hdrH = 24.0f;
        float topInset = hasOut ? 8.0f : 16.0f;
        if (realPorts > 0 && realPorts <= 3)
            topInset += 1.5f;
        float botInset = hasOut ? 4.0f : 10.0f;
        float portArea = static_cast<float>(entry.data.ports.size()) * 22.0f;
        float bodyH = topInset + portArea + botInset;
        if (bodyH < 14.0f)
            bodyH = 14.0f;
        float nh = hdrH + bodyH;
        result.nodeHeights.push_back(nh);
        result.nodePortStartY.push_back(hdrH + topInset);

        result.scene.nodes.push_back(std::move(entry));
    }

    auto tNodesDone = std::chrono::steady_clock::now();

    // ==================== CONNECTION PASS ====================
    buildConnections(allPorts, portToIdx, portToNodeIdx, result);

    auto tEnd = std::chrono::steady_clock::now();
    double msNodes = std::chrono::duration<double, std::milli>(tNodesDone - tStart).count();
    double msConns = std::chrono::duration<double, std::milli>(tEnd - tNodesDone).count();
    double msTotal = std::chrono::duration<double, std::milli>(tEnd - tStart).count();
    if (s_perfPrint)
    {
        printf(
            "[perf] NativeBuildScene  TOTAL: %.0fms  (nodes=%.0fms conns=%.0fms)  "
            "n=%d  ports=%d  conns=%d  edges=%d\n",
            msTotal, msNodes, msConns, static_cast<int>(result.scene.nodes.size()), static_cast<int>(allPorts.size()),
            static_cast<int>(result.scene.connections.size()), static_cast<int>(result.edges.size()));
        fflush(stdout);
    }

    return result;
}

// ---------- Snapshot-based build (dict reads instead of proxy attr calls) ----------

NativeBuildResult nativeBuildFromSnapshot(py::list snapshot)
{
    auto tStart = std::chrono::steady_clock::now();

    NativeBuildResult result;
    int numNodes = static_cast<int>(py::len(snapshot));

    std::vector<PortRecord> allPorts;
    PortMap portToIdx;
    PortMap portToNodeIdx;
    uint32_t stableId = 1;

    for (int ni = 0; ni < numNodes; ++ni)
    {
        py::dict ns = snapshot[ni].cast<py::dict>();

        py::object node = ns["node"];
        result.modelNodes.push_back(node);

        std::string nodeName = ns["name"].cast<std::string>();
        std::string nodeType = ns["type"].cast<std::string>();

        NodeData nd;
        nd.name = nodeName;
        nd.typeName = nodeType;
        nd.nodeWidth = ns["size_w"].cast<float>();

        if (ns.contains("icon_url"))
        {
            py::object iconObj = ns["icon_url"];
            if (!iconObj.is_none())
                nd.iconUrl = iconObj.cast<std::string>();
        }
        if (ns.contains("preview_url"))
        {
            py::object prevObj = ns["preview_url"];
            if (!prevObj.is_none())
                nd.previewUrl = prevObj.cast<std::string>();
        }

        if (ns.contains("is_backdrop"))
            nd.isBackdrop = ns["is_backdrop"].cast<bool>();
        if (ns.contains("description"))
        {
            py::object descObj = ns["description"];
            if (!descObj.is_none())
                nd.description = descObj.cast<std::string>();
        }
        if (ns.contains("stacking_order"))
            nd.stackingOrder = ns["stacking_order"].cast<int>();
        if (ns.contains("expansion_state"))
            nd.expansionState = ns["expansion_state"].cast<int>();
        if (ns.contains("has_menu"))
            nd.hasMenu = ns["has_menu"].cast<bool>();
        if (ns.contains("size_h"))
        {
            float sh = ns["size_h"].cast<float>();
            if (sh > 0.0f)
                nd.nodeHeight = sh;
        }

        py::object colorObj = ns["color"];
        if (!colorObj.is_none())
        {
            uint32_t abgr = tupleToAbgr(colorObj);
            if (abgr != 0)
                nd.backgroundColor = abgr;
        }

        nd.selected = ns["selected"].cast<bool>();
        if (ns.contains("valid_state"))
            nd.validState = ns["valid_state"].cast<int>();
        else
            nd.validState = ns["valid"].cast<bool>() ? 0 : 2;
        if (ns.contains("polymorphic_unresolved") && ns["polymorphic_unresolved"].cast<bool>())
        {
            nd.isPolymorphic = true;
            nd.isResolved = false;
        }

        // InputNode-specific fields
        if (ns.contains("is_input_node"))
            nd.isInputNode = ns["is_input_node"].cast<bool>();
        if (ns.contains("view_mode"))
            nd.viewMode = ns["view_mode"].cast<int>();

        py::list portsList = ns["ports"].cast<py::list>();
        int numPorts = static_cast<int>(py::len(portsList));
        int visiblePortIdx = 0;
        for (int pi = 0; pi < numPorts; ++pi)
        {
            py::dict ps = portsList[pi].cast<py::dict>();

            py::object port = ps["port"];
            std::string portName = ps["name"].cast<std::string>();
            std::string portType = ps["type"].cast<std::string>();
            int level = ps["level"].cast<int>();
            int exp = ps["exp"].cast<int>();
            bool isGroup = ps["is_group"].cast<bool>();
            int subCount = ps["sub_count"].cast<int>();

            py::object inputsObj = ps["inputs"];
            py::object outputsObj = ps["outputs"];
            bool hasInputs = !inputsObj.is_none();
            bool hasOutputs = !outputsObj.is_none();

            std::vector<py::object> inputs, outputs;
            if (hasInputs)
            {
                py::list inList(inputsObj);
                for (auto& item : inList)
                    inputs.push_back(py::reinterpret_borrow<py::object>(item));
            }
            if (hasOutputs)
            {
                py::list outList(outputsObj);
                for (auto& item : outList)
                    outputs.push_back(py::reinterpret_borrow<py::object>(item));
            }

            PortRecord rec;
            rec.port = port;
            rec.inputs = std::move(inputs);
            rec.outputs = std::move(outputs);
            rec.visiblePortIdx = visiblePortIdx++;

            size_t portIdx = allPorts.size();
            allPorts.push_back(std::move(rec));
            portToIdx[port] = portIdx;
            portToNodeIdx[port] = ni;

            PortData pd;
            pd.name = portName;
            pd.typeName = portType;
            pd.isInput = hasInputs;
            pd.isOutput = hasOutputs;
            pd.level = level;
            pd.color = colorForType(portType);
            if (pd.color == 0xFFAAAAAA)
                pd.color = 0xFF888888;
            pd.connectedTarget = hasInputs && !allPorts.back().inputs.empty();
            pd.isGroup = isGroup && subCount > 0;
            if (pd.isGroup)
                pd.color = 0xFFAAAA66;
            if (pd.isGroup)
            {
                pd.isExpanded = (exp == 0);
                pd.childCount = subCount;
            }

            if (ps.contains("is_empty"))
                pd.isEmpty = ps["is_empty"].cast<bool>();
            if (ps.contains("rel_pos"))
                pd.relativePosition = ps["rel_pos"].cast<int>();
            if (ps.contains("parent_count"))
                pd.parentChildCount = ps["parent_count"].cast<int>();
            if (ps.contains("poly_unresolved") && ps["poly_unresolved"].cast<bool>())
            {
                pd.isPolymorphic = true;
                pd.isResolved = false;
            }
            if (ps.contains("is_uniform"))
                pd.isUniform = ps["is_uniform"].cast<bool>();
            if (ps.contains("is_interface_only"))
                pd.isInterfaceOnly = ps["is_interface_only"].cast<bool>();

            // InputNode readability fields (io_state, group headers, collapse state)
            if (ps.contains("io_state"))
                pd.ioState = ps["io_state"].cast<int>();
            if (ps.contains("is_group_header"))
                pd.isGroupHeader = ps["is_group_header"].cast<bool>();
            if (ps.contains("group_port_count"))
                pd.groupPortCount = ps["group_port_count"].cast<int>();
            if (ps.contains("group_collapsed"))
                pd.groupCollapsed = ps["group_collapsed"].cast<bool>();
            if (ps.contains("is_hidden"))
                pd.isHidden = ps["is_hidden"].cast<bool>();
            if (ps.contains("has_error"))
                pd.hasError = ps["has_error"].cast<bool>();

            nd.ports.push_back(std::move(pd));
        }
        result.visiblePortCounts.push_back(visiblePortIdx);

        // Auto-size: ensure node is wide enough for its text content
        // (skip for backdrops — their size comes from USD property)
        if (!nd.isBackdrop)
        {
            constexpr float kCharW = 7.5f;
            constexpr float kHeaderPad = 26.0f;
            constexpr float kPortPadL = 24.0f;
            constexpr float kPortPadR = 24.0f;
            float minW = static_cast<float>(nd.name.size()) * kCharW + kHeaderPad;
            for (const auto& p : nd.ports)
            {
                float pw = static_cast<float>(p.name.size()) * kCharW + kPortPadL + kPortPadR;
                if (pw > minW)
                    minW = pw;
            }
            if (minW > nd.nodeWidth)
                nd.nodeWidth = minW;
        }

        SceneNodeEntry entry;
        entry.stableId = stableId++;
        entry.data = std::move(nd);

        py::object posObj = ns["pos"];
        if (!posObj.is_none())
        {
            try
            {
                entry.posX = posObj[py::int_(0)].cast<float>();
                entry.posY = posObj[py::int_(1)].cast<float>();
            }
            catch (...)
            {
                reportUnexpectedNativeException("snapshot node position conversion");
            }
        }

        result.stableIds.push_back(entry.stableId);
        result.nodePosX.push_back(entry.posX);
        result.nodePosY.push_back(entry.posY);
        result.nodeWidths.push_back(entry.data.nodeWidth);
        bool hasOut2 = false;
        int realPorts2 = 0;
        bool hasEmpty2 = false;
        for (const auto& p : entry.data.ports)
        {
            if (p.isOutput && !p.isGroup && !p.isEmpty)
                hasOut2 = true;
            if (!p.isGroup)
                ++realPorts2;
            if (p.isEmpty)
                hasEmpty2 = true;
        }
        entry.data.isInterface = hasEmpty2;
        float hdrH2 = 24.0f;
        float topI2, botI2, portA2;
        if (entry.data.isInputNode)
        {
            topI2 = kInputNodeBodyTopInset;
            botI2 = kInputNodeBodyBottomInset;
            portA2 = inputNodePortAreaHeight(entry.data);
        }
        else
        {
            topI2 = hasOut2 ? 8.0f : 16.0f;
            if (realPorts2 > 0 && realPorts2 <= 3)
                topI2 += 1.5f;
            botI2 = hasOut2 ? 4.0f : 10.0f;
            portA2 = static_cast<float>(entry.data.ports.size()) * 22.0f;
        }
        float bodyH2 = topI2 + portA2 + botI2;
        if (bodyH2 < 14.0f)
            bodyH2 = 14.0f;
        float previewH2 = 0.0f;
        if (!entry.data.previewUrl.empty() && entry.data.expansionState != 2)
            previewH2 = entry.data.nodeWidth + 12.0f;
        float nh;
        if (entry.data.isBackdrop && entry.data.nodeHeight > 0.0f)
            nh = entry.data.nodeHeight;
        else
            nh = hdrH2 + bodyH2 + previewH2;
        result.nodeHeights.push_back(nh);
        result.nodePortStartY.push_back(hdrH2 + topI2);

        result.scene.nodes.push_back(std::move(entry));
    }

    auto tNodesDone = std::chrono::steady_clock::now();

    // ---- Connection pass ----
    buildConnections(allPorts, portToIdx, portToNodeIdx, result);

    auto tEnd = std::chrono::steady_clock::now();
    double msNodes = std::chrono::duration<double, std::milli>(tNodesDone - tStart).count();
    double msConns = std::chrono::duration<double, std::milli>(tEnd - tNodesDone).count();
    double msTotal = std::chrono::duration<double, std::milli>(tEnd - tStart).count();
    if (s_perfPrint)
    {
        printf(
            "[perf] NativeBuildFromSnapshot  TOTAL: %.0fms  (nodes=%.0fms conns=%.0fms)  "
            "n=%d  ports=%d  conns=%d  edges=%d\n",
            msTotal, msNodes, msConns, static_cast<int>(result.scene.nodes.size()), static_cast<int>(allPorts.size()),
            static_cast<int>(result.scene.connections.size()), static_cast<int>(result.edges.size()));
        fflush(stdout);
    }

    return result;
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

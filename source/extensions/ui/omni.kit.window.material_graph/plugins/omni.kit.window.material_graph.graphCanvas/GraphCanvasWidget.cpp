// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// GraphCanvasWidget implementation: the main draw loop that renders
// backdrops, connections, nodes, marquee selection, drag noodle,
// breadcrumb, and tooltip in a single ImGui-style rendering pass.
// Also handles scene management, view transforms, hit-testing,
// node position/size updates, and selection state.

#include "GraphCanvasWidget.h"
#include "GraphCanvasLayout.h"

#include <carb/Framework.h>
#include <carb/imgui/ImGui.h>

#include <algorithm>
#include <cmath>
#include <numeric>

namespace omni
{
namespace kit
{
namespace materialGraph
{

static carb::imgui::ImGui* acquireImGui()
{
    static carb::imgui::ImGui* s_imgui = nullptr;
    if (!s_imgui)
    {
        auto* fw = carb::getFramework();
        if (fw)
            s_imgui = fw->tryAcquireInterface<carb::imgui::ImGui>();
    }
    return s_imgui;
}

// Minimum distance from screen point (px,py) to a cubic Bezier curve defined
// by four control points.  Uses uniform subdivision (kSamples segments) which
// is fast and accurate enough for the hit-test threshold we use (~6 px).
static float distanceToCubicBezier(
    float px, float py, float x0, float y0, float cp1x, float cp1y, float cp2x, float cp2y, float x1, float y1)
{
    constexpr int kSamples = 32;
    float best = 1e30f;
    for (int i = 0; i <= kSamples; ++i)
    {
        float t = static_cast<float>(i) / static_cast<float>(kSamples);
        float u = 1.0f - t;
        float bx = u * u * u * x0 + 3.0f * u * u * t * cp1x + 3.0f * u * t * t * cp2x + t * t * t * x1;
        float by = u * u * u * y0 + 3.0f * u * u * t * cp1y + 3.0f * u * t * t * cp2y + t * t * t * y1;
        float dx = px - bx;
        float dy = py - by;
        float d2 = dx * dx + dy * dy;
        if (d2 < best)
            best = d2;
    }
    return std::sqrt(best);
}

// ---------- Construction / factory ----------

GraphCanvasWidget::GraphCanvasWidget() = default;
GraphCanvasWidget::~GraphCanvasWidget() = default;

std::shared_ptr<GraphCanvasWidget> GraphCanvasWidget::create()
{
    auto w = std::shared_ptr<GraphCanvasWidget>(new GraphCanvasWidget());
    omni::ui::ContainerStack::instance().addChildToTop(w);
    return w;
}

// ---------- Scene management ----------

void GraphCanvasWidget::setScene(const GraphScene& scene)
{
    m_scene = scene;
    m_nodeIdToIndex.clear();
    for (size_t i = 0; i < m_scene.nodes.size(); ++i)
        m_nodeIdToIndex[m_scene.nodes[i].stableId] = i;
}

void GraphCanvasWidget::clearScene()
{
    m_scene.nodes.clear();
    m_scene.connections.clear();
    m_nodeIdToIndex.clear();
}

// ---------- State setters ----------

void GraphCanvasWidget::setNodeSelected(uint32_t stableId, bool selected)
{
    auto it = m_nodeIdToIndex.find(stableId);
    if (it != m_nodeIdToIndex.end())
        m_scene.nodes[it->second].data.selected = selected;
}

void GraphCanvasWidget::setMarqueeRect(float x0, float y0, float x1, float y1)
{
    m_marqueeActive = true;
    m_marqueeX0 = x0;
    m_marqueeY0 = y0;
    m_marqueeX1 = x1;
    m_marqueeY1 = y1;
}

void GraphCanvasWidget::clearMarquee()
{
    m_marqueeActive = false;
}

void GraphCanvasWidget::setDragNoodle(float x0, float y0, float x1, float y1, uint32_t color)
{
    m_noodleActive = true;
    m_noodleX0 = x0;
    m_noodleY0 = y0;
    m_noodleX1 = x1;
    m_noodleY1 = y1;
    m_noodleColor = color;
}

void GraphCanvasWidget::clearDragNoodle()
{
    m_noodleActive = false;
}

void GraphCanvasWidget::setNodePosition(uint32_t stableId, float posX, float posY)
{
    auto it = m_nodeIdToIndex.find(stableId);
    if (it != m_nodeIdToIndex.end())
    {
        m_scene.nodes[it->second].posX = posX;
        m_scene.nodes[it->second].posY = posY;
    }
}

void GraphCanvasWidget::setNodeSize(uint32_t stableId, float width, float height)
{
    auto it = m_nodeIdToIndex.find(stableId);
    if (it != m_nodeIdToIndex.end())
    {
        m_scene.nodes[it->second].data.nodeWidth = width;
        m_scene.nodes[it->second].data.nodeHeight = height;
    }
}

// ---------- View transform ----------

void GraphCanvasWidget::setViewTransform(
    float zoom, float panX, float panY, float frameScreenX, float frameScreenY, float dpiScale)
{
    m_zoom = zoom;
    m_panX = panX;
    m_panY = panY;
    m_frameScreenX = frameScreenX;
    m_frameScreenY = frameScreenY;
    m_dpiScale = (dpiScale > 0.0f) ? dpiScale : 1.0f;
}

// ---------- Coordinate transforms ----------

float GraphCanvasWidget::canvasToScreenX(float cx) const
{
    return m_frameScreenX + (cx * m_zoom + m_panX);
}

float GraphCanvasWidget::canvasToScreenY(float cy) const
{
    return m_frameScreenY + (cy * m_zoom + m_panY);
}

float GraphCanvasWidget::screenToCanvasX(float sx) const
{
    if (m_zoom == 0.0f)
        return 0.0f;
    return (sx - m_frameScreenX - m_panX) / m_zoom;
}

float GraphCanvasWidget::screenToCanvasY(float sy) const
{
    if (m_zoom == 0.0f)
        return 0.0f;
    return (sy - m_frameScreenY - m_panY) / m_zoom;
}

// ---------- Utility ----------

bool GraphCanvasWidget::isRectInViewport(float x, float y, float w, float h, float vpX, float vpY, float vpW, float vpH) const
{
    return !(x + w < vpX || x > vpX + vpW || y + h < vpY || y > vpY + vpH);
}

// ---------- Port anchor positions ----------

std::pair<float, float> GraphCanvasWidget::portScreenPosition(const SceneNodeEntry& node,
                                                              int portIndex,
                                                              bool isInput,
                                                              float effScale) const
{
    float sx = canvasToScreenX(node.posX);
    float sy = canvasToScreenY(node.posY);
    float nodeW = node.data.nodeWidth * m_zoom;
    float hdrH = headerHeightForNode(node.data);

    if (node.data.expansionState == 2)
    {
        float closedH = nodeHeight(node.data);
        float portY = sy + closedH * 0.5f * effScale;
        return isInput ? std::make_pair(sx, portY) : std::make_pair(sx + nodeW, portY);
    }

    float inset, portY;
    if (node.data.isInputNode)
    {
        inset = bodyTopInsetForInputNode();
        float runY = 0.0f;
        for (int i = 0; i < portIndex && i < static_cast<int>(node.data.ports.size()); ++i)
            runY += portHeightForNode(node.data, i);
        float pH = portHeightForNode(node.data, portIndex);
        portY = sy + (hdrH + inset + runY + pH * 0.5f) * effScale;
    }
    else
    {
        inset = bodyTopInsetForNode(node.data);
        portY = sy + (hdrH + inset + portIndex * kPortHeight + kPortHeight * 0.5f) * effScale;
    }

    if (isInput)
        return { sx, portY };
    return { sx + nodeW, portY };
}

std::pair<float, float> GraphCanvasWidget::portScreenPos(
    const SceneNodeEntry& node, int portIndex, bool isInput, float originX, float originY, float effScale) const
{
    float sx = originX + node.posX * effScale;
    float sy = originY + node.posY * effScale;
    float nodeW = node.data.nodeWidth * effScale;

    if (node.data.expansionState == 2)
    {
        float closedH = nodeHeight(node.data);
        float portY = sy + closedH * 0.5f * effScale;
        return isInput ? std::make_pair(sx, portY) : std::make_pair(sx + nodeW, portY);
    }

    float hdrH = headerHeightForNode(node.data);
    float inset, portY;
    if (node.data.isInputNode)
    {
        inset = bodyTopInsetForInputNode();
        float runY = 0.0f;
        for (int i = 0; i < portIndex && i < static_cast<int>(node.data.ports.size()); ++i)
            runY += portHeightForNode(node.data, i);
        float pH = portHeightForNode(node.data, portIndex);
        portY = sy + (hdrH + inset + runY + pH * 0.5f) * effScale;
    }
    else
    {
        inset = bodyTopInsetForNode(node.data);
        portY = sy + (hdrH + inset + portIndex * kPortHeight + kPortHeight * 0.5f) * effScale;
    }

    if (isInput)
        return { sx, portY };
    return { sx + nodeW, portY };
}

GraphCanvasWidget::AnchorPoint GraphCanvasWidget::getPortAnchor(uint32_t nodeId, int portIndex, bool isInput) const
{
    auto it = m_nodeIdToIndex.find(nodeId);
    if (it == m_nodeIdToIndex.end())
        return { 0.0f, 0.0f };

    const auto& node = m_scene.nodes[it->second];
    float effScale = m_zoom;
    auto pos = portScreenPosition(node, portIndex, isInput, effScale);
    return { pos.first, pos.second };
}

// ---------- Hit testing ----------

HitResult GraphCanvasWidget::hitTest(float screenX, float screenY) const
{
    HitResult result;
    float effScale = m_zoom;

    for (int i = static_cast<int>(m_scene.nodes.size()) - 1; i >= 0; --i)
    {
        const auto& node = m_scene.nodes[i];
        float sx = canvasToScreenX(node.posX);
        float sy = canvasToScreenY(node.posY);
        float sw = node.data.nodeWidth * effScale;
        float sh = nodeHeight(node.data) * effScale;

        if (screenX < sx || screenX > sx + sw || screenY < sy || screenY > sy + sh)
            continue;

        result.nodeId = node.stableId;

        if (screenY < sy + kHeaderHeight * effScale)
        {
            // InputNode mode toggle: check if click is in the mode indicator area
            if (node.data.isInputNode && effScale >= m_style.lodThreshold0)
            {
                float expCenter = node.data.hasMenu ? (sx + sw - 28.0f * effScale) : (sx + sw - 14.0f * effScale);
                float modeX = expCenter - 20.0f * effScale;
                float modeW = 40.0f * effScale;
                if (screenX >= modeX - modeW && screenX <= modeX + 10.0f * effScale)
                {
                    result.type = HitType::INPUT_NODE_MODE_TOGGLE;
                    return result;
                }
            }
            result.type = HitType::NODE_HEADER;
            return result;
        }

        if (node.data.isInputNode)
        {
            float topI = kInputNodeBodyTopInset;
            float runY = kHeaderHeight + topI;
            for (int p = 0; p < static_cast<int>(node.data.ports.size()); ++p)
            {
                float pH = portHeightForNode(node.data, p);
                float portScreenY = sy + runY * effScale;
                if (screenY >= portScreenY && screenY < portScreenY + pH * effScale)
                {
                    result.portIndex = p;
                    const auto& port = node.data.ports[p];
                    if (port.isGroupHeader || port.isGroup)
                    {
                        result.type = HitType::NODE_BODY;
                        return result;
                    }
                    float midX = sx + sw * 0.5f;
                    if (port.isInput && screenX < midX)
                        result.type = HitType::PORT_INPUT;
                    else if (port.isOutput && screenX >= midX)
                        result.type = HitType::PORT_OUTPUT;
                    else
                        result.type = HitType::NODE_BODY;
                    return result;
                }
                runY += pH;
            }
        }
        else
        {
            for (int p = 0; p < static_cast<int>(node.data.ports.size()); ++p)
            {
                float portY = sy + (kHeaderHeight + p * kPortHeight) * effScale;
                if (screenY >= portY && screenY < portY + kPortHeight * effScale)
                {
                    result.portIndex = p;
                    const auto& port = node.data.ports[p];
                    float midX = sx + sw * 0.5f;
                    if (port.isInput && screenX < midX)
                        result.type = HitType::PORT_INPUT;
                    else if (port.isOutput && screenX >= midX)
                        result.type = HitType::PORT_OUTPUT;
                    else
                        result.type = HitType::NODE_BODY;
                    return result;
                }
            }
        }

        result.type = HitType::NODE_BODY;
        return result;
    }

    return result;
}

// ---------- Drawing: main entry ----------

void GraphCanvasWidget::_drawContent(float elapsedTime)
{
    auto* imgui = acquireImGui();
    if (!imgui)
        return;

    auto* dl = imgui->getWindowDrawList();
    if (!dl)
        return;

    float originX = getScreenPositionX();
    float originY = getScreenPositionY();
    float zoom = _getCanvasZoom();
    if (zoom <= 0.0f)
        zoom = 1.0f;
    float dpiScale = getDpiScale();
    if (dpiScale <= 0.0f)
        dpiScale = 1.0f;
    float effScale = zoom * dpiScale;

    m_zoom = effScale;

    ensureFonts();
    ensureBgTexture();
    float kBaseFontSize = m_style.baseFontSize;
    float desiredFontSize = kBaseFontSize * effScale;
    auto [bestFont, fontCorrection] = pickFont(desiredFontSize);
    if (bestFont)
        imgui->pushFont(bestFont);
    imgui->setWindowFontScale(fontCorrection);
    updateIconProviders();

    drawGrid(imgui, dl, originX, originY, effScale);

    int visNodes = 0;
    int visConns = 0;

    size_t nodeCount = m_scene.nodes.size();
    std::vector<size_t> drawOrder(nodeCount);
    std::iota(drawOrder.begin(), drawOrder.end(), 0);
    std::sort(drawOrder.begin(), drawOrder.end(), [&](size_t a, size_t b) {
        return m_scene.nodes[a].data.stackingOrder < m_scene.nodes[b].data.stackingOrder;
    });

    // Layer 1: Backdrop nodes (unselected then selected)
    for (size_t idx : drawOrder)
    {
        const auto& node = m_scene.nodes[idx];
        if (!node.data.isBackdrop || node.data.selected)
            continue;
        float sx = originX + node.posX * effScale;
        float sy = originY + node.posY * effScale;
        float sw = node.data.nodeWidth * effScale;
        float sh = nodeHeight(node.data) * effScale;
        drawBackdrop(imgui, dl, node, sx, sy, sw, sh, effScale);
        ++visNodes;
    }
    for (size_t idx : drawOrder)
    {
        const auto& node = m_scene.nodes[idx];
        if (!node.data.isBackdrop || !node.data.selected)
            continue;
        float sx = originX + node.posX * effScale;
        float sy = originY + node.posY * effScale;
        float sw = node.data.nodeWidth * effScale;
        float sh = nodeHeight(node.data) * effScale;
        drawBackdrop(imgui, dl, node, sx, sy, sw, sh, effScale);
        ++visNodes;
    }

    // Layer 2: Connections (with hover detection)
    auto mpos = imgui->getMousePos();
    bool mouseDown = imgui->isMouseDown(0);
    int bestHoverConn = -1;
    float bestHoverDist = m_style.connHoverThreshold;

    for (int ci = 0; ci < static_cast<int>(m_scene.connections.size()); ++ci)
    {
        const auto& conn = m_scene.connections[ci];
        auto srcIt = m_nodeIdToIndex.find(conn.sourceNodeId);
        auto tgtIt = m_nodeIdToIndex.find(conn.targetNodeId);
        if (srcIt == m_nodeIdToIndex.end() || tgtIt == m_nodeIdToIndex.end())
            continue;

        const auto& srcNode = m_scene.nodes[srcIt->second];
        const auto& tgtNode = m_scene.nodes[tgtIt->second];

        auto srcAnchor = portScreenPos(srcNode, conn.sourcePortIndex, false, originX, originY, effScale);
        auto tgtAnchor = portScreenPos(tgtNode, conn.targetPortIndex, true, originX, originY, effScale);

        if (conn.reversed)
            std::swap(srcAnchor, tgtAnchor);

        float curveAmt = kConnectionCurve * effScale;
        float connMin = (effScale < m_style.lodThreshold3) ? m_style.connMinThicknessLod3 : m_style.connMinThickness;
        float connThick = std::max(conn.thickness * effScale, connMin);

        // Hover detection: distance from mouse to this Bezier
        if (!mouseDown && !m_noodleActive && !m_marqueeActive)
        {
            float cp1x = srcAnchor.first + curveAmt;
            float cp2x = tgtAnchor.first - curveAmt;
            float dist = distanceToCubicBezier(mpos.x, mpos.y, srcAnchor.first, srcAnchor.second, cp1x, srcAnchor.second,
                                               cp2x, tgtAnchor.second, tgtAnchor.first, tgtAnchor.second);
            if (dist < bestHoverDist)
            {
                bestHoverDist = dist;
                bestHoverConn = ci;
            }
        }

        if (!conn.valid)
        {
            uint32_t errRGB = m_style.errorColor & 0x00FFFFFF;
            float outerThick = connThick + m_style.errorConnOuterGlow * effScale;
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second,
                           (m_style.errorConnOuterAlpha << 24) | errRGB, outerThick, curveAmt);
            float innerThick = connThick + m_style.errorConnGlowExtra * effScale;
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second,
                           (m_style.errorConnGlowAlpha << 24) | errRGB, innerThick, curveAmt);
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second,
                           m_style.errorColor, connThick, curveAmt);
        }
        else
        {
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second, conn.color,
                           connThick, curveAmt);
        }
        ++visConns;
    }

    m_hoverConnectionIndex = bestHoverConn;

    // Draw hover highlight for the hovered connection (selection-blue fringe)
    if (bestHoverConn >= 0 && bestHoverConn < static_cast<int>(m_scene.connections.size()))
    {
        const auto& conn = m_scene.connections[bestHoverConn];
        auto srcIt = m_nodeIdToIndex.find(conn.sourceNodeId);
        auto tgtIt = m_nodeIdToIndex.find(conn.targetNodeId);
        if (srcIt != m_nodeIdToIndex.end() && tgtIt != m_nodeIdToIndex.end())
        {
            auto srcAnchor =
                portScreenPos(m_scene.nodes[srcIt->second], conn.sourcePortIndex, false, originX, originY, effScale);
            auto tgtAnchor =
                portScreenPos(m_scene.nodes[tgtIt->second], conn.targetPortIndex, true, originX, originY, effScale);
            if (conn.reversed)
                std::swap(srcAnchor, tgtAnchor);

            float curveAmt = kConnectionCurve * effScale;
            float connMin = (effScale < m_style.lodThreshold3) ? m_style.connMinThicknessLod3 : m_style.connMinThickness;
            float connThick = std::max(conn.thickness * effScale, connMin);
            uint32_t selRGB = m_style.selectionColor & 0x00FFFFFF;

            float outerThick = connThick + m_style.connHoverOuterGlow * effScale;
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second,
                           (m_style.connHoverOuterAlpha << 24) | selRGB, outerThick, curveAmt);
            float innerThick = connThick + m_style.connHoverGlowExtra * effScale;
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second,
                           (m_style.connHoverGlowAlpha << 24) | selRGB, innerThick, curveAmt);
            uint32_t coreColor = (m_style.selectionOutlineAlpha << 24) | selRGB;
            drawConnection(imgui, dl, srcAnchor.first, srcAnchor.second, tgtAnchor.first, tgtAnchor.second, coreColor,
                           connThick, curveAmt);
        }
    }

    // Minimum on-screen node size at LOD 2/3
    float kMinNodeScreenW = m_style.minNodeScreenW;
    float kMinNodeScreenH = m_style.minNodeScreenH;
    bool enforceMins = (effScale < m_style.lodThreshold2);

    auto clampedNodeRect = [&](const SceneNodeEntry& node, float& sx, float& sy, float& sw, float& sh) {
        sx = originX + node.posX * effScale;
        sy = originY + node.posY * effScale;
        sw = node.data.nodeWidth * effScale;
        sh = nodeHeight(node.data) * effScale;
        if (enforceMins)
        {
            if (sw < kMinNodeScreenW)
            {
                sx -= (kMinNodeScreenW - sw) * 0.5f;
                sw = kMinNodeScreenW;
            }
            if (sh < kMinNodeScreenH)
            {
                sy -= (kMinNodeScreenH - sh) * 0.5f;
                sh = kMinNodeScreenH;
            }
        }
    };

    // Layer 3: Regular nodes (unselected then selected)
    for (size_t idx : drawOrder)
    {
        const auto& node = m_scene.nodes[idx];
        if (node.data.isBackdrop || node.data.selected)
            continue;
        float sx, sy, sw, sh;
        clampedNodeRect(node, sx, sy, sw, sh);
        drawNode(imgui, dl, node, sx, sy, sw, sh, effScale);
        ++visNodes;
    }
    for (size_t idx : drawOrder)
    {
        const auto& node = m_scene.nodes[idx];
        if (node.data.isBackdrop || !node.data.selected)
            continue;
        float sx, sy, sw, sh;
        clampedNodeRect(node, sx, sy, sw, sh);
        drawNode(imgui, dl, node, sx, sy, sw, sh, effScale);
        ++visNodes;
    }

    m_visibleNodeCount = visNodes;
    m_visibleConnectionCount = visConns;

    // ---- Marquee selection rectangle ----
    if (m_marqueeActive)
    {
        float sx0 = originX + m_marqueeX0 * effScale;
        float sy0 = originY + m_marqueeY0 * effScale;
        float sx1 = originX + m_marqueeX1 * effScale;
        float sy1 = originY + m_marqueeY1 * effScale;
        float mx0 = std::min(sx0, sx1);
        float my0 = std::min(sy0, sy1);
        float mx1 = std::max(sx0, sx1);
        float my1 = std::max(sy0, sy1);

        imgui->addRect(
            dl, { mx0, my0 }, { mx1, my1 }, m_style.marqueeOutline, 0.0f, carb::imgui::kDrawCornerFlagAll, 1.5f);
        imgui->addRectFilled(dl, { mx0, my0 }, { mx1, my1 }, m_style.marqueeFill, 0.0f, carb::imgui::kDrawCornerFlagAll);
    }

    // ---- Drag noodle ----
    if (m_noodleActive)
    {
        float sx0 = originX + m_noodleX0 * effScale;
        float sy0 = originY + m_noodleY0 * effScale;
        float sx1 = originX + m_noodleX1 * effScale;
        float sy1 = originY + m_noodleY1 * effScale;
        drawConnection(
            imgui, dl, sx0, sy0, sx1, sy1, m_noodleColor, kConnectionThickness * effScale, kConnectionCurve * effScale);
    }

    imgui->setWindowFontScale(1.0f);
    if (bestFont)
        imgui->popFont();

    // ---- Breadcrumb bar ----
    if (m_breadcrumbs.size() > 1)
    {
        float bcDpi = 1.0f;
        float bcDesiredSize = 14.0f * bcDpi;
        auto [bcFont, bcCorr] = pickFont(bcDesiredSize);
        if (bcFont)
            imgui->pushFont(bcFont);
        imgui->setWindowFontScale(bcCorr);

        drawBreadcrumb(imgui, dl, bcDpi);

        imgui->setWindowFontScale(1.0f);
        if (bcFont)
            imgui->popFont();
    }

    // ---- Hover tooltip ----
    updateAndDrawTooltip(imgui, dl, originX, originY, effScale, elapsedTime);
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

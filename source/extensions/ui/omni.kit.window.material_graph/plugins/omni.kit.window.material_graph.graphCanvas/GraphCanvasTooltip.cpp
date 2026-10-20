// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "GraphCanvasWidget.h"
#include "GraphCanvasLayout.h"

#include <carb/Framework.h>
#include <carb/imgui/ImGui.h>

#include <algorithm>
#include <cmath>
#include <string>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Updates hover state from the mouse position, resets dwell when the target changes, and
// after the configured delay draws the tooltip (rounded box, wrapped lines, separators).
void GraphCanvasWidget::updateAndDrawTooltip(
    carb::imgui::ImGui* imgui, carb::imgui::DrawList* dl, float originX, float originY, float effScale, float elapsedTime)
{
    if (m_noodleActive || m_marqueeActive || m_scene.nodes.empty() || effScale < m_style.lodThreshold0)
        return;

    auto mpos = imgui->getMousePos();
    bool mouseDown = imgui->isMouseDown(0);

    int curHoverNode = -1;
    int curHoverPort = -1;

    if (!mouseDown)
    {
        for (int i = static_cast<int>(m_scene.nodes.size()) - 1; i >= 0; --i)
        {
            const auto& node = m_scene.nodes[i];
            float sx = originX + node.posX * effScale;
            float sy = originY + node.posY * effScale;
            float sw = node.data.nodeWidth * effScale;
            float sh = nodeHeight(node.data) * effScale;

            float portOverhang = (kPortRadius + 6.0f) * effScale;
            if (mpos.x < sx - portOverhang || mpos.x > sx + sw + portOverhang || mpos.y < sy || mpos.y > sy + sh)
                continue;

            float hdrH = headerHeightForNode(node.data) * effScale;

            if (mpos.y > sy + hdrH && node.data.expansionState != 2)
            {
                float nodeHdr = headerHeightForNode(node.data);
                float topI = bodyTopInsetForNode(node.data);
                for (int pi = 0; pi < static_cast<int>(node.data.ports.size()); ++pi)
                {
                    const auto& pd = node.data.ports[pi];
                    if (pd.isGroup || pd.isEmpty)
                        continue;

                    float portCY =
                        sy + (nodeHdr + topI + static_cast<float>(pi) * kPortHeight + kPortHeight * 0.5f) * effScale;
                    float portR = kPortRadius * effScale;
                    float hitR = portR + 6.0f * effScale;

                    float dy = mpos.y - portCY;
                    if (dy < -hitR || dy > hitR)
                        continue;

                    bool rightSide = pd.isOutput && !pd.isInput;
                    float portCX = rightSide ? (sx + sw) : sx;
                    float dx = mpos.x - portCX;

                    if (dx * dx + dy * dy <= hitR * hitR)
                    {
                        curHoverNode = static_cast<int>(node.stableId);
                        curHoverPort = pi;
                        break;
                    }
                }
            }

            if (curHoverPort < 0 && mpos.y <= sy + hdrH)
            {
                float iconPadS = std::max((hdrH - kIconSize * effScale) * 0.5f, 1.0f * effScale);
                float iconRightX = sx + iconPadS + 1.0f * effScale + kIconSize * effScale;
                if (mpos.x >= sx && mpos.x <= iconRightX)
                {
                    curHoverNode = static_cast<int>(node.stableId);
                    curHoverPort = -1;
                }
            }
            break;
        }
    }

    if (curHoverNode != m_hoverNodeId || curHoverPort != m_hoverPortIndex)
    {
        m_hoverNodeId = curHoverNode;
        m_hoverPortIndex = curHoverPort;
        m_hoverTime = 0.0f;
        m_tooltipText.clear();

        m_tipAnchorX = 0.0f;
        m_tipAnchorY = 0.0f;
        m_tipAnchorRight = true;
        if (curHoverNode >= 0)
        {
            for (const auto& node : m_scene.nodes)
            {
                if (static_cast<int>(node.stableId) != curHoverNode)
                    continue;
                float sx = originX + node.posX * effScale;
                float sy = originY + node.posY * effScale;
                float sw = node.data.nodeWidth * effScale;

                if (curHoverPort >= 0 && curHoverPort < static_cast<int>(node.data.ports.size()))
                {
                    const auto& pd = node.data.ports[curHoverPort];
                    bool rightSide = pd.isOutput && !pd.isInput;
                    float topI = bodyTopInsetForNode(node.data);
                    float nodeHdr = headerHeightForNode(node.data);
                    float portCY =
                        sy + (nodeHdr + topI + static_cast<float>(curHoverPort) * kPortHeight + kPortHeight * 0.5f) *
                                 effScale;
                    if (rightSide)
                    {
                        m_tipAnchorX = sx + sw;
                        m_tipAnchorRight = true;
                    }
                    else
                    {
                        m_tipAnchorX = sx;
                        m_tipAnchorRight = false;
                    }
                    m_tipAnchorY = portCY;
                }
                else
                {
                    m_tipAnchorX = sx;
                    m_tipAnchorY = sy;
                    m_tipAnchorRight = false;
                }
                break;
            }
        }
    }
    else if (m_hoverNodeId >= 0)
    {
        m_hoverTime += elapsedTime;
    }

    if (m_hoverNodeId < 0 || m_hoverTime < m_style.tooltipDelay || m_tooltipText.empty())
        return;

    // Draw tooltip background, border, and leveled text lines.
    float tipFontSz = m_style.tooltipFontSize;
    auto [tipFont, tipCorr] = pickFont(tipFontSz);
    if (tipFont)
        imgui->pushFont(tipFont);
    imgui->setWindowFontScale(tipCorr);

    const std::string& text = m_tooltipText;
    float pad = m_style.tooltipPad;
    float maxW = m_style.tooltipMaxW;
    float radius = m_style.tooltipRadius;
    float baseLineH = imgui->calcTextSize("Mg", nullptr, false, -1.0f).y;
    float lineMul = m_style.tooltipLineSpacing;

    auto levelScale = [&](int lvl) -> float {
        if (lvl == 0)
            return m_style.tooltipTitleScale;
        if (lvl == 1)
            return m_style.tooltipMetaScale;
        return m_style.tooltipDescScale;
    };
    auto levelLineH = [&](int lvl) -> float { return baseLineH * levelScale(lvl) * lineMul; };

    struct TipLine
    {
        std::string str;
        int level;
    };
    std::vector<TipLine> lines;
    {
        size_t lp = 0;
        bool firstLine = true;
        while (lp <= text.size())
        {
            size_t le = text.find('\n', lp);
            if (le == std::string::npos)
                le = text.size();
            std::string raw = text.substr(lp, le - lp);
            lp = le + 1;
            if (raw == "---")
            {
                lines.push_back({ "", 3 });
                continue;
            }
            int lvl;
            std::string display;
            if (raw.size() > 1 && raw[0] == '@')
            {
                display = raw.substr(1);
                lvl = 1;
            }
            else if (firstLine)
            {
                display = raw;
                lvl = 0;
                firstLine = false;
            }
            else
            {
                display = raw;
                lvl = 2;
            }
            if (!display.empty())
            {
                float sc = levelScale(lvl);
                imgui->setWindowFontScale(tipCorr * sc);
                auto sz = imgui->calcTextSize(display.c_str(), nullptr, false, -1.0f);
                if (sz.x > maxW)
                {
                    std::string buf;
                    std::string word;
                    for (size_t ci = 0; ci <= display.size(); ++ci)
                    {
                        char ch = (ci < display.size()) ? display[ci] : ' ';
                        if (ch == ' ' || ci == display.size())
                        {
                            std::string test = buf.empty() ? word : (buf + " " + word);
                            auto tw = imgui->calcTextSize(test.c_str(), nullptr, false, -1.0f);
                            if (tw.x > maxW && !buf.empty())
                            {
                                lines.push_back({ buf, lvl });
                                buf = word;
                            }
                            else
                            {
                                buf = test;
                            }
                            word.clear();
                        }
                        else
                        {
                            word += ch;
                        }
                    }
                    if (!buf.empty())
                        lines.push_back({ buf, lvl });
                }
                else
                {
                    lines.push_back({ display, lvl });
                }
                imgui->setWindowFontScale(tipCorr);
            }
            else
            {
                lines.push_back({ display, lvl });
            }
        }
    }

    float contentW = 0.0f;
    float contentH = 0.0f;
    float secGap = m_style.tooltipSectionGap;
    for (const auto& ln : lines)
    {
        if (ln.level == 3)
        {
            contentH += secGap;
            continue;
        }
        float sc = levelScale(ln.level);
        float lh = levelLineH(ln.level);
        if (!ln.str.empty())
        {
            imgui->setWindowFontScale(tipCorr * sc);
            auto sz = imgui->calcTextSize(ln.str.c_str(), nullptr, false, -1.0f);
            contentW = std::max(contentW, sz.x);
            imgui->setWindowFontScale(tipCorr);
        }
        contentH += lh;
    }
    contentW = std::min(contentW, maxW);

    float bw = contentW + 2.0f * pad;
    float bh = contentH + 2.0f * pad;

    float tx, ty;
    if (m_tipAnchorRight)
    {
        tx = m_tipAnchorX + m_style.tooltipOffsetX;
        ty = m_tipAnchorY + m_style.tooltipOffsetY;
    }
    else
    {
        tx = m_tipAnchorX - bw - m_style.tooltipOffsetX;
        ty = m_tipAnchorY + m_style.tooltipOffsetY;
    }

    auto clipMin = imgui->getWindowContentRegionMin();
    auto clipMax = imgui->getWindowContentRegionMax();
    auto winPos = imgui->getWindowPos();
    float screenRight = winPos.x + clipMax.x;
    float screenLeft = winPos.x + clipMin.x;
    float screenBottom = winPos.y + clipMax.y;
    if (m_tipAnchorRight && tx + bw > screenRight)
        tx = m_tipAnchorX - bw - m_style.tooltipOffsetX;
    else if (!m_tipAnchorRight && tx < screenLeft)
        tx = m_tipAnchorX + m_style.tooltipOffsetX;
    if (ty + bh > screenBottom)
        ty = screenBottom - bh - 2.0f;

    imgui->addRectFilled(
        dl, { tx, ty }, { tx + bw, ty + bh }, m_style.tooltipBg, radius, carb::imgui::kDrawCornerFlagAll);
    imgui->addRect(
        dl, { tx, ty }, { tx + bw, ty + bh }, m_style.tooltipBorder, radius, carb::imgui::kDrawCornerFlagAll, 1.0f);

    float curY = ty + pad;
    for (const auto& ln : lines)
    {
        if (ln.level == 3)
        {
            float sepMid = curY + secGap * 0.5f;
            imgui->addLine(dl, { tx + pad, sepMid }, { tx + bw - pad, sepMid }, 0x18FFFFFF, 1.0f);
            curY += secGap;
            continue;
        }
        float sc = levelScale(ln.level);
        float lh = levelLineH(ln.level);
        if (!ln.str.empty())
        {
            uint32_t col = (ln.level == 0) ? m_style.tooltipTitle :
                           (ln.level == 1) ? m_style.tooltipMeta :
                                             m_style.tooltipDesc;
            imgui->setWindowFontScale(tipCorr * sc);
            imgui->addText(dl, { tx + pad, curY }, col, ln.str.c_str(), nullptr);
            imgui->setWindowFontScale(tipCorr);
        }
        curY += lh;
    }

    imgui->setWindowFontScale(1.0f);
    if (tipFont)
        imgui->popFont();
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

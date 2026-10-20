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

// Replaces the breadcrumb path, clears click/ellipsis state, and resets the list of
// segments hidden behind the ellipsis when the path is rebuilt.
void GraphCanvasWidget::setBreadcrumb(const std::vector<std::string>& path)
{
    m_breadcrumbs = path;
    m_bcClickedIndex = -1;
    m_bcEllipsisOpen = false;
    m_bcHiddenSegments.clear();
}

// Lays out and draws the breadcrumb bar (rounded background, chevron separators, text
// colors for root / ancestors / current). Handles width limits by truncating labels,
// collapsing to first / ellipsis / last (and optionally penultimate), popup for hidden
// segments, and records hover and clicked segment indices for the widget host.
void GraphCanvasWidget::drawBreadcrumb(carb::imgui::ImGui* imgui, carb::imgui::DrawList* dl, float dpiScale)
{
    if (m_breadcrumbs.empty())
        return;

    using namespace carb::imgui;

    auto clipMin = imgui->getWindowContentRegionMin();
    auto clipMax = imgui->getWindowContentRegionMax();
    auto winPos = imgui->getWindowPos();
    float vpLeft = winPos.x + clipMin.x;
    float vpTop = winPos.y + clipMin.y;
    float vpW = clipMax.x - clipMin.x;
    if (vpW <= 0.0f)
        return;

    const float ds = dpiScale;
    const float kOffsetX = 12.0f * ds;
    const float kOffsetY = 10.0f * ds;
    const float kBarH = 32.0f * ds;
    const float kHPad = 10.0f * ds;
    const float kCornerR = 6.0f * ds;
    const float kSegHPad = 6.0f * ds;
    const float kGapTS = 6.0f * ds;
    const float kSepBlockW = 13.0f * ds;
    const float kMaxSegW = 160.0f * ds;
    const float kMaxBarW = vpW * 0.4f;

    constexpr uint32_t cBg = 0xB4181818;
    constexpr uint32_t cBorder = 0x40606060;
    constexpr uint32_t cSep = 0x73AAAAAA;
    constexpr uint32_t cRoot = 0xB3DDDDDD;
    constexpr uint32_t cAncestor = 0xB3CCCCCC;
    constexpr uint32_t cCurrent = 0xFFEEEEEE;
    constexpr uint32_t cHoverTxt = 0xE0DDDDDD;
    constexpr uint32_t cHoverBg = 0x1E606060;
    constexpr uint32_t cHoverBd = 0x0C888888;

    const int segCount = static_cast<int>(m_breadcrumbs.size());

    struct Seg
    {
        std::string text;
        float textW, boxW;
        bool truncated, isEllipsis;
        int origIdx;
    };

    std::vector<Seg> segs;
    segs.reserve(segCount);
    for (int i = 0; i < segCount; ++i)
    {
        const auto& name = m_breadcrumbs[i];
        auto ts = imgui->calcTextSize(name.c_str(), nullptr, false, -1.0f);
        float tw = ts.x;
        bool trunc = false;
        std::string display = name;
        if (tw > kMaxSegW)
        {
            trunc = true;
            std::string probe = name;
            while (probe.size() > 1)
            {
                probe.pop_back();
                std::string candidate = probe + "...";
                auto sz = imgui->calcTextSize(candidate.c_str(), nullptr, false, -1.0f);
                if (sz.x <= kMaxSegW)
                {
                    display = std::move(candidate);
                    tw = sz.x;
                    break;
                }
            }
        }
        segs.push_back({ std::move(display), tw, tw + 2.0f * kSegHPad, trunc, false, i });
    }

    auto computeTotalW = [&]() {
        float w = kHPad * 2.0f;
        for (int i = 0; i < (int)segs.size(); ++i)
        {
            w += segs[i].boxW;
            if (i < (int)segs.size() - 1)
                w += kGapTS + kSepBlockW + kGapTS;
        }
        return w;
    };

    float barW = computeTotalW();
    m_bcHiddenSegments.clear();
    if (barW > kMaxBarW && segCount > 2)
    {
        auto ets = imgui->calcTextSize("...", nullptr, false, -1.0f);
        Seg ellipsis{ "...", ets.x, ets.x + 2.0f * kSegHPad, false, true, -1 };
        float sepCost = kGapTS + kSepBlockW + kGapTS;
        float base = kHPad * 2.0f + segs[0].boxW + sepCost + ellipsis.boxW + sepCost + segs.back().boxW;
        std::vector<Seg> collapsed;
        collapsed.push_back(segs[0]);
        collapsed.push_back(ellipsis);
        if (segCount > 3 && base + segs[segCount - 2].boxW + sepCost <= kMaxBarW)
        {
            collapsed.push_back(segs[segCount - 2]);
            for (int i = 1; i < segCount - 2; ++i)
                m_bcHiddenSegments.push_back({ i, m_breadcrumbs[i] });
        }
        else
        {
            for (int i = 1; i < segCount - 1; ++i)
                m_bcHiddenSegments.push_back({ i, m_breadcrumbs[i] });
        }
        collapsed.push_back(segs.back());
        segs = std::move(collapsed);
        barW = computeTotalW();
    }
    barW = std::min(barW, kMaxBarW);

    float barX = vpLeft + kOffsetX;
    float barY = vpTop + kOffsetY;

    imgui->addRectFilled(dl, { barX, barY }, { barX + barW, barY + kBarH }, cBg, kCornerR, kDrawCornerFlagAll);
    imgui->addRect(dl, { barX, barY }, { barX + barW, barY + kBarH }, cBorder, kCornerR, kDrawCornerFlagAll, 1.0f);

    auto mpos = imgui->getMousePos();
    bool mouseInBar = (mpos.x >= barX && mpos.x <= barX + barW && mpos.y >= barY && mpos.y <= barY + kBarH);
    m_bcHovered = mouseInBar;

    bool mDown = imgui->isMouseDown(0);
    bool mClicked = mDown && !m_bcPrevMouseDown;
    m_bcPrevMouseDown = mDown;

    // Close the ellipsis popup on click outside the bar and popup area.
    if (m_bcEllipsisOpen && mClicked)
    {
        float popW = 180.0f * ds;
        float popItemH = 24.0f * ds;
        float popPad = 4.0f * ds;
        float popH = (float)m_bcHiddenSegments.size() * popItemH + 2.0f * popPad;
        bool inPop =
            (mpos.x >= m_bcPopupX && mpos.x <= m_bcPopupX + popW && mpos.y >= m_bcPopupY && mpos.y <= m_bcPopupY + popH);
        if (!inPop && !mouseInBar)
            m_bcEllipsisOpen = false;
    }

    auto measuredH = imgui->calcTextSize("Mg", nullptr, false, -1.0f);
    float textH = measuredH.y;
    float cx = barX + kHPad;

    for (int i = 0; i < (int)segs.size(); ++i)
    {
        const auto& s = segs[i];
        float x0 = cx, x1 = cx + s.boxW;
        float y0 = barY + 4.0f * ds, y1 = barY + kBarH - 4.0f * ds;
        bool isLast = (s.origIdx == segCount - 1);
        bool clickable = !isLast && !s.isEllipsis;
        bool hovered = mouseInBar && mpos.x >= x0 && mpos.x <= x1 && mpos.y >= y0 && mpos.y <= y1;

        uint32_t tc = isLast ? cCurrent : (s.origIdx == 0 ? cRoot : cAncestor);

        if (hovered && (clickable || s.isEllipsis))
        {
            if (clickable)
                tc = cHoverTxt;
            imgui->addRectFilled(dl, { x0, y0 }, { x1, y1 }, cHoverBg, 4.0f * ds, kDrawCornerFlagAll);
            imgui->addRect(dl, { x0, y0 }, { x1, y1 }, cHoverBd, 4.0f * ds, kDrawCornerFlagAll, 1.0f);
            if (mClicked)
            {
                if (s.isEllipsis)
                {
                    m_bcEllipsisOpen = !m_bcEllipsisOpen;
                    m_bcPopupX = x0;
                    m_bcPopupY = barY + kBarH + 2.0f * ds;
                }
                else
                {
                    m_bcClickedIndex = s.origIdx;
                }
            }
        }

        float textX = cx + kSegHPad;
        float textY = barY + (kBarH - textH) * 0.5f;
        imgui->addText(dl, { textX, textY }, tc, s.text.c_str(), nullptr);

        // Full path segment as a tooltip when the label was shortened with "...".
        if (hovered && s.truncated && s.origIdx >= 0)
        {
            const auto& fn = m_breadcrumbs[s.origIdx];
            auto tipSz = imgui->calcTextSize(fn.c_str(), nullptr, false, -1.0f);
            float tp = 4.0f * ds, tx = mpos.x + 12.0f * ds, ty = mpos.y + 16.0f * ds;
            imgui->addRectFilled(dl, { tx, ty }, { tx + tipSz.x + 2 * tp, ty + tipSz.y + 2 * tp }, 0xE8222222,
                                 4.0f * ds, kDrawCornerFlagAll);
            imgui->addRect(dl, { tx, ty }, { tx + tipSz.x + 2 * tp, ty + tipSz.y + 2 * tp }, 0x60808080, 4.0f * ds,
                           kDrawCornerFlagAll, 1.0f);
            imgui->addText(dl, { tx + tp, ty + tp }, 0xFFDDDDDD, fn.c_str(), nullptr);
        }

        cx = x1;
        if (i < (int)segs.size() - 1)
        {
            float sepMidX = cx + kGapTS + kSepBlockW * 0.5f;
            float sepMidY = barY + kBarH * 0.5f;
            float chH = 4.0f * ds, chW = 2.5f * ds;
            imgui->addLine(dl, { sepMidX - chW, sepMidY - chH }, { sepMidX + chW, sepMidY }, cSep, 1.2f);
            imgui->addLine(dl, { sepMidX + chW, sepMidY }, { sepMidX - chW, sepMidY + chH }, cSep, 1.2f);
            cx += kGapTS + kSepBlockW + kGapTS;
        }
    }

    if (m_bcEllipsisOpen && !m_bcHiddenSegments.empty())
    {
        float popW = 180.0f * ds, popItemH = 24.0f * ds, popPad = 4.0f * ds;
        float popH = (float)m_bcHiddenSegments.size() * popItemH + 2.0f * popPad;
        float popX = m_bcPopupX, popY = m_bcPopupY;
        imgui->addRectFilled(dl, { popX, popY }, { popX + popW, popY + popH }, cBg, kCornerR, kDrawCornerFlagAll);
        imgui->addRect(dl, { popX, popY }, { popX + popW, popY + popH }, cBorder, kCornerR, kDrawCornerFlagAll, 1.0f);
        float iy = popY + popPad;
        for (const auto& entry : m_bcHiddenSegments)
        {
            float ix0 = popX + popPad, ix1 = popX + popW - popPad, iy1 = iy + popItemH;
            bool ih = (mpos.x >= ix0 && mpos.x <= ix1 && mpos.y >= iy && mpos.y <= iy1);
            if (ih)
            {
                imgui->addRectFilled(dl, { ix0, iy }, { ix1, iy1 }, cHoverBg, 4.0f * ds, kDrawCornerFlagAll);
                if (mClicked)
                {
                    m_bcClickedIndex = entry.first;
                    m_bcEllipsisOpen = false;
                }
            }
            imgui->addText(
                dl, { ix0 + kSegHPad, iy + (popItemH - textH) * 0.5f }, cAncestor, entry.second.c_str(), nullptr);
            iy = iy1;
        }
        m_bcHovered = m_bcHovered || (mpos.x >= popX && mpos.x <= popX + popW && mpos.y >= popY && mpos.y <= popY + popH);
    }
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

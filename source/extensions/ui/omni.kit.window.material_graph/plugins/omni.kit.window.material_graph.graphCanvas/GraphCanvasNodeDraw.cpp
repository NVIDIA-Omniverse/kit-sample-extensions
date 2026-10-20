// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Node and port drawing routines for the graph canvas.
// Handles all visual states: normal, selected, error, warning,
// closed/minimized/expanded, InputNode compact layout, backdrops,
// texture previews, and LOD-based detail reduction.

#include "GraphCanvasWidget.h"
#include "GraphCanvasLayout.h"

#include <carb/imgui/ImGui.h>

#include <algorithm>
#include <cmath>
#include <cstring>

namespace omni
{
namespace kit
{
namespace materialGraph
{

float GraphCanvasWidget::nodeHeight(const NodeData& data) const
{
    if (data.isBackdrop && data.nodeHeight > 0.0f)
        return data.nodeHeight;
    float hdrH = headerHeightForNode(data);
    if (data.expansionState == 2)
    {
        float iconBottom = 1.0f + kIconSize;
        float botI = bodyBottomInsetForNode(data);
        return std::max(hdrH, iconBottom + botI);
    }
    float portArea, topI, botI;
    if (data.isInputNode)
    {
        portArea = inputNodePortAreaHeight(data);
        topI = bodyTopInsetForInputNode();
        botI = bodyBottomInsetForInputNode();
    }
    else
    {
        portArea = static_cast<float>(data.ports.size()) * kPortHeight;
        topI = bodyTopInsetForNode(data);
        botI = bodyBottomInsetForNode(data);
    }
    float bodyH = topI + portArea + botI;
    if (bodyH < kMinBodyHeight)
        bodyH = kMinBodyHeight;
    float previewH = 0.0f;
    if (!data.previewUrl.empty() && data.expansionState != 2)
    {
        float pad = m_style.texturePreviewPadding;
        previewH = data.nodeWidth + pad * 2.0f;
    }
    return hdrH + bodyH + previewH;
}

// ---------- Drawing: single node ----------

void GraphCanvasWidget::drawNode(carb::imgui::ImGui* imgui,
                                 carb::imgui::DrawList* dl,
                                 const SceneNodeEntry& node,
                                 float x,
                                 float y,
                                 float w,
                                 float h,
                                 float effScale)
{
    using namespace carb::imgui;
    const auto& data = node.data;
    float cornerPx = static_cast<float>(kBgTexCorner) * effScale;
    float hdrH = headerHeightForNode(data) * effScale;

    // Visual class must reflect intrinsic node type, NOT expansion state.
    // Ports may be stripped when minimized/closed, so only treat as
    // CONTAINER when the node is fully open AND has no ports.
    bool intrinsicNoPorts = data.ports.empty() && data.expansionState == 0;

    enum class VisClass
    {
        NORMAL,
        CONTAINER,
        INTERFACE
    };
    VisClass vc;
    if (data.isInterface)
        vc = VisClass::INTERFACE;
    else if (intrinsicNoPorts)
        vc = VisClass::CONTAINER;
    else if (!nodeHasOutputPort(data) && data.expansionState == 0)
        vc = VisClass::INTERFACE;
    else
        vc = VisClass::NORMAL;

    auto darken = [](uint32_t col, int amount) -> uint32_t {
        int r = std::max(0, (int)(col & 0xFF) - amount);
        int g = std::max(0, (int)((col >> 8) & 0xFF) - amount);
        int b = std::max(0, (int)((col >> 16) & 0xFF) - amount);
        return (col & 0xFF000000) | (b << 16) | (g << 8) | r;
    };
    auto brighten = [](uint32_t col, int amount) -> uint32_t {
        int r = std::min(255, (int)(col & 0xFF) + amount);
        int g = std::min(255, (int)((col >> 8) & 0xFF) + amount);
        int b = std::min(255, (int)((col >> 16) & 0xFF) + amount);
        return (col & 0xFF000000) | (b << 16) | (g << 8) | r;
    };
    auto tintTeal = [](uint32_t col, int shift) -> uint32_t {
        int r = (col & 0xFF);
        int g = ((col >> 8) & 0xFF);
        int b = ((col >> 16) & 0xFF);
        g = std::min(255, g + shift);
        b = std::min(255, b + shift / 2);
        return (col & 0xFF000000) | (b << 16) | (g << 8) | r;
    };

    uint32_t bodyCol =
        (vc == VisClass::CONTAINER) ? darken(data.backgroundColor, kNoPortBodyDarken) : data.backgroundColor;
    uint32_t headerCol = brighten(bodyCol, 13);
    if (vc == VisClass::INTERFACE)
        headerCol = tintTeal(headerCol, 12);
    bool isClosed = (data.expansionState == 2);

    auto drawClosedBody = [&](uint32_t bCol, uint32_t hCol, float bodyY, float bodyH) {
        if (bodyH > 0.0f)
        {
            draw9Slice(imgui, dl, m_bgTexId, x, bodyY, w, bodyH, cornerPx, bCol);
            if (cornerPx > 0.0f)
            {
                float patchH = std::min(cornerPx, bodyH);
                imgui->addRectFilled(dl, { x, bodyY }, { x + w, bodyY + patchH }, bCol, 0.0f, kDrawCornerFlagAll);
            }
        }
        draw9Slice(imgui, dl, m_bgTexId, x, y, w, hdrH, cornerPx, hCol);
        if (cornerPx > 0.0f && hdrH > cornerPx)
        {
            imgui->addRectFilled(dl, { x, y + hdrH - cornerPx }, { x + w, y + hdrH }, hCol, 0.0f, kDrawCornerFlagAll);
        }
    };

    if (isClosed)
    {
        uint32_t closedBodyCol = data.backgroundColor;
        uint32_t closedHdrCol = brighten(closedBodyCol, 13);

        float bodyY = y + hdrH;
        float bodyH = h - hdrH;

        bool selHalf = data.selected;

        if (data.validState > 0)
        {
            uint32_t stateColor = (data.validState == 2) ? m_style.errorColor : m_style.warningColor;
            uint32_t stateRGB = stateColor & 0x00FFFFFF;
            float bandPad = m_style.errorBandWidth * effScale;
            float auraPad = bandPad + m_style.errorAuraWidth * effScale;

            uint32_t auraA = selHalf ? (m_style.errorAuraAlpha >> 1) : m_style.errorAuraAlpha;
            draw9Slice(imgui, dl, m_bgTexId, x - auraPad, y - auraPad, w + 2.0f * auraPad, h + 2.0f * auraPad,
                       cornerPx + auraPad, (auraA << 24) | stateRGB);

            uint32_t bandA = selHalf ? (m_style.errorBandAlpha >> 1) : m_style.errorBandAlpha;
            float bandCorner = cornerPx + bandPad * m_style.errorBandCornerScale;
            draw9Slice(imgui, dl, m_bgTexId, x - bandPad, y - bandPad, w + 2.0f * bandPad, h + 2.0f * bandPad,
                       bandCorner, (bandA << 24) | stateRGB);
        }

        drawClosedBody(closedBodyCol, closedHdrCol, bodyY, bodyH);

        if (data.selected)
        {
            float selW = 3.0f * effScale;
            float selOuter = selW * 0.5f;
            float selInner = selW * 0.5f;
            float selGlowOut = selOuter + 2.0f * effScale;

            draw9Slice(imgui, dl, m_bgTexId, x - selGlowOut, y - selGlowOut, w + 2.0f * selGlowOut,
                       h + 2.0f * selGlowOut, cornerPx + selGlowOut,
                       (m_style.selectionGlowAlpha << 24) | (m_style.selectionColor & 0x00FFFFFF));
            draw9Slice(imgui, dl, m_bgTexId, x - selOuter, y - selOuter, w + 2.0f * selOuter, h + 2.0f * selOuter,
                       cornerPx + selOuter,
                       (m_style.selectionOutlineAlpha << 24) | (m_style.selectionColor & 0x00FFFFFF));

            float ix = x + selInner, iy = y + selInner;
            float iw = w - 2.0f * selInner, ih = h - 2.0f * selInner;
            float ihdrH = hdrH - selInner;
            float ibodyY = iy + ihdrH;
            float ibodyH = ih - ihdrH;
            float icorner = std::max(cornerPx - selInner, 0.0f);
            if (ibodyH > 0.0f)
            {
                draw9Slice(imgui, dl, m_bgTexId, ix, ibodyY, iw, ibodyH, icorner, closedBodyCol);
                if (icorner > 0.0f)
                {
                    float patchH = std::min(icorner, ibodyH);
                    imgui->addRectFilled(
                        dl, { ix, ibodyY }, { ix + iw, ibodyY + patchH }, closedBodyCol, 0.0f, kDrawCornerFlagAll);
                }
            }
            draw9Slice(imgui, dl, m_bgTexId, ix, iy, iw, ihdrH, icorner, closedHdrCol);
            if (icorner > 0.0f && ihdrH > icorner)
            {
                imgui->addRectFilled(
                    dl, { ix, iy + ihdrH - icorner }, { ix + iw, iy + ihdrH }, closedHdrCol, 0.0f, kDrawCornerFlagAll);
            }
        }

        if (effScale < m_style.lodThreshold3)
            return;

        drawNodeHeader(imgui, dl, x, y, w, h, effScale, data, node.stableId);

        // Ports centered vertically on the full closed height
        float portCY = y + h * 0.5f;
        float portR = kPortRadius * effScale * m_style.closedPortScale;
        uint32_t kClosedPortCol = m_style.closedPortColor;
        for (const auto& port : data.ports)
        {
            if (port.isGroup)
                continue;
            bool rightSide = port.isOutput && !port.isInput;
            float cx = rightSide ? (x + w) : x;
            imgui->addCircleFilled(dl, { cx, portCY }, portR, kClosedPortCol, 16);
        }

        return;
    }

    float bodyY = y + hdrH;
    float bodyH = h - hdrH;

    auto drawExpandedBody = [&]() {
        if (bodyH > 0.0f)
        {
            draw9Slice(imgui, dl, m_bgTexId, x, bodyY, w, bodyH, cornerPx, bodyCol);
            if (cornerPx > 0.0f)
            {
                float patchH = std::min(cornerPx, bodyH);
                imgui->addRectFilled(dl, { x, bodyY }, { x + w, bodyY + patchH }, bodyCol, 0.0f, kDrawCornerFlagAll);
            }
        }
        draw9Slice(imgui, dl, m_bgTexId, x, y, w, hdrH, cornerPx, headerCol);
        if (cornerPx > 0.0f && hdrH > cornerPx)
        {
            imgui->addRectFilled(
                dl, { x, y + hdrH - cornerPx }, { x + w, y + hdrH }, headerCol, 0.0f, kDrawCornerFlagAll);
        }
    };

    bool selHalf = data.selected;

    if (data.validState > 0)
    {
        uint32_t stateColor = (data.validState == 2) ? m_style.errorColor : m_style.warningColor;
        uint32_t stateRGB = stateColor & 0x00FFFFFF;
        float bandPad = m_style.errorBandWidth * effScale;
        float auraPad = bandPad + m_style.errorAuraWidth * effScale;

        uint32_t auraA = selHalf ? (m_style.errorAuraAlpha >> 1) : m_style.errorAuraAlpha;
        draw9Slice(imgui, dl, m_bgTexId, x - auraPad, y - auraPad, w + 2.0f * auraPad, h + 2.0f * auraPad,
                   cornerPx + auraPad, (auraA << 24) | stateRGB);

        uint32_t bandA = selHalf ? (m_style.errorBandAlpha >> 1) : m_style.errorBandAlpha;
        float bandCorner = cornerPx + bandPad * m_style.errorBandCornerScale;
        draw9Slice(imgui, dl, m_bgTexId, x - bandPad, y - bandPad, w + 2.0f * bandPad, h + 2.0f * bandPad, bandCorner,
                   (bandA << 24) | stateRGB);
    }

    drawExpandedBody();

    // Selection (centered stroke on node edge — visible ring straddles boundary)
    if (data.selected)
    {
        float selW = 3.0f * effScale;
        float selOuter = selW * 0.5f;
        float selInner = selW * 0.5f;
        float selGlowOut = selOuter + 2.0f * effScale;

        draw9Slice(imgui, dl, m_bgTexId, x - selGlowOut, y - selGlowOut, w + 2.0f * selGlowOut, h + 2.0f * selGlowOut,
                   cornerPx + selGlowOut, (m_style.selectionGlowAlpha << 24) | (m_style.selectionColor & 0x00FFFFFF));
        draw9Slice(imgui, dl, m_bgTexId, x - selOuter, y - selOuter, w + 2.0f * selOuter, h + 2.0f * selOuter,
                   cornerPx + selOuter, (m_style.selectionOutlineAlpha << 24) | (m_style.selectionColor & 0x00FFFFFF));

        float ix = x + selInner, iy = y + selInner;
        float iw = w - 2.0f * selInner, ih = h - 2.0f * selInner;
        float ihdrH = hdrH - selInner;
        float ibodyY = iy + ihdrH;
        float ibodyH = ih - ihdrH;
        float icorner = std::max(cornerPx - selInner, 0.0f);
        if (ibodyH > 0.0f)
        {
            draw9Slice(imgui, dl, m_bgTexId, ix, ibodyY, iw, ibodyH, icorner, bodyCol);
            if (icorner > 0.0f)
            {
                float patchH = std::min(icorner, ibodyH);
                imgui->addRectFilled(dl, { ix, ibodyY }, { ix + iw, ibodyY + patchH }, bodyCol, 0.0f, kDrawCornerFlagAll);
            }
        }
        draw9Slice(imgui, dl, m_bgTexId, ix, iy, iw, ihdrH, icorner, headerCol);
        if (icorner > 0.0f && ihdrH > icorner)
        {
            imgui->addRectFilled(
                dl, { ix, iy + ihdrH - icorner }, { ix + iw, iy + ihdrH }, headerCol, 0.0f, kDrawCornerFlagAll);
        }
    }

    // ---- Structured LOD ----
    if (effScale < m_style.lodThreshold3)
        return;

    bool fullDetail = (effScale >= m_style.lodThreshold0);

    drawNodeHeader(imgui, dl, x, y, w, h, effScale, data, node.stableId);

    float nodeHdrH = headerHeightForNode(data);

    if (data.isInputNode)
    {
        float topInset = bodyTopInsetForInputNode();
        float runningY = nodeHdrH + topInset;
        for (int i = 0; i < static_cast<int>(data.ports.size()); ++i)
        {
            float pH = portHeightForNode(data, i);
            float portY = y + runningY * effScale;
            drawInputNodePort(imgui, dl, data.ports[i], x, portY, w, pH, effScale, fullDetail);
            runningY += pH;
        }
    }
    else
    {
        float topInset = bodyTopInsetForNode(data);
        for (int i = 0; i < static_cast<int>(data.ports.size()); ++i)
        {
            float portY = y + (nodeHdrH + topInset + static_cast<float>(i) * kPortHeight) * effScale;
            drawNodePort(imgui, dl, data.ports[i], x, portY, w, effScale, fullDetail);
        }
    }

    // ---- Texture preview below port area ----
    if (!data.previewUrl.empty() && data.expansionState != 2 && effScale >= m_style.lodThreshold2)
    {
        float pad = m_style.texturePreviewPadding * effScale;
        float cornerR = m_style.texturePreviewCornerR * effScale;
        float previewSize = w - pad * 2.0f;
        float bodyBottomY = y + (h - (data.nodeWidth + m_style.texturePreviewPadding * 2.0f) * effScale);
        float imgX = x + pad;
        float imgY = bodyBottomY + pad;

        void* texPtr = data.previewUrl.empty() ? nullptr : getIconTexture(data.previewUrl);
        if (texPtr)
        {
            carb::imgui::TextureId texId{};
            texId.ptr = texPtr;
            imgui->addImageRounded(dl, texId, { imgX, imgY }, { imgX + previewSize, imgY + previewSize },
                                   { 0.0f, 0.0f }, { 1.0f, 1.0f }, 0xFFFFFFFF, cornerR, kDrawCornerFlagAll);
        }
        else
        {
            imgui->addRectFilled(dl, { imgX, imgY }, { imgX + previewSize, imgY + previewSize }, 0xFF333333, cornerR,
                                 kDrawCornerFlagAll);
        }
    }
}

// ---------- Drawing: node header ----------

void GraphCanvasWidget::drawNodeHeader(carb::imgui::ImGui* imgui,
                                       carb::imgui::DrawList* dl,
                                       float x,
                                       float y,
                                       float w,
                                       float h,
                                       float effScale,
                                       const NodeData& data,
                                       uint32_t stableId)
{
    using namespace carb::imgui;
    float headerH = headerHeightForNode(data) * effScale;
    uint32_t typeColor = m_style.headerAccentColor;
    if (data.validState == 2)
        typeColor = m_style.errorColor;
    else if (data.validState == 1)
        typeColor = m_style.warningColor;

    auto lighten = [](uint32_t col, int amount) -> uint32_t {
        int r = std::min(255, (int)(col & 0xFF) + amount);
        int g = std::min(255, (int)((col >> 8) & 0xFF) + amount);
        int b = std::min(255, (int)((col >> 16) & 0xFF) + amount);
        return (col & 0xFF000000) | (b << 16) | (g << 8) | r;
    };

    // Icon badge — same placement for all node types: centered in header
    float iconSz = kIconSize * effScale;
    float iconPad = std::max((headerH - iconSz) * 0.5f, 1.0f * effScale);
    float iy = y + iconPad;
    float ix = x + iconPad + 1.0f * effScale;
    float iconR = 5.0f * effScale;
    float iconRight = ix + iconSz;

    // Accent line + separator
    float barH = 2.0f * effScale;
    float divStartX = iconRight + 5.0f * effScale;
    float divY = std::floor(y + headerH - barH * 0.5f) + 0.5f;
    bool nodeUnresolved = data.isPolymorphic && !data.isResolved;
    if (nodeUnresolved)
    {
        uint32_t dashCol = (typeColor & 0x00FFFFFF) | (static_cast<uint32_t>(((typeColor >> 24) & 0xFF) * 0.92f) << 24);
        float dashLen = 10.0f * effScale;
        float gapLen = 5.0f * effScale;
        float lineEnd = x + w;
        float pos = 0.0f;
        float totalLen = lineEnd - divStartX;
        while (pos < totalLen)
        {
            float segEnd = pos + dashLen;
            if (segEnd > totalLen)
                segEnd = totalLen;
            imgui->addLine(dl, { divStartX + pos, divY }, { divStartX + segEnd, divY }, dashCol, barH);
            pos += dashLen + gapLen;
        }
    }
    else
    {
        imgui->addRectFilled(dl, { divStartX, std::floor(y + headerH - barH) + 0.5f },
                             { x + w, std::floor(y + headerH - barH) + 0.5f + barH }, typeColor, 0.0f,
                             kDrawCornerFlagAll);
    }
    float sepY = std::floor(y + headerH) + 0.5f;
    imgui->addLine(dl, { divStartX, sepY }, { x + w, sepY }, data.borderColor, 1.0f);

    // Badge background
    imgui->addRectFilled(dl, { ix, iy }, { ix + iconSz, iy + iconSz }, m_style.iconBadgeBg, iconR, kDrawCornerFlagAll);
    imgui->addLine(dl, { ix + iconR, iy + 0.5f }, { ix + iconSz - iconR, iy + 0.5f }, 0x14FFFFFF, 1.0f);

    void* iconTexPtr = data.iconUrl.empty() ? nullptr : getIconTexture(data.iconUrl);
    if (iconTexPtr)
    {
        carb::imgui::TextureId texId{};
        texId.ptr = iconTexPtr;
        imgui->addImageRounded(dl, texId, { ix, iy }, { ix + iconSz, iy + iconSz }, { 0.0f, 0.0f }, { 1.0f, 1.0f },
                               0xFFFFFFFF, iconR, kDrawCornerFlagAll);
    }
    else
    {
        imgui->addRectFilled(dl, { ix + 2.0f * effScale, iy + 2.0f * effScale },
                             { ix + iconSz - 2.0f * effScale, iy + iconSz - 2.0f * effScale }, lighten(typeColor, 30),
                             iconR * 0.6f, kDrawCornerFlagAll);
    }

    // LOD 2 (0.18–0.35): icon + accent line only, no text — show large icon in body
    if (effScale < m_style.lodThreshold2)
    {
        float bigSz = std::min(w * 0.6f, h * 0.4f);
        float bx = x + (w - bigSz) * 0.5f;
        float by = y + headerH + ((h - headerH) - bigSz) * 0.5f;
        float bigR = 6.0f * effScale;
        if (iconTexPtr)
        {
            carb::imgui::TextureId texId{};
            texId.ptr = iconTexPtr;
            imgui->addImageRounded(dl, texId, { bx, by }, { bx + bigSz, by + bigSz }, { 0.0f, 0.0f }, { 1.0f, 1.0f },
                                   0xFFFFFFFF, bigR, kDrawCornerFlagAll);
        }
        else
        {
            imgui->addRectFilled(
                dl, { bx, by }, { bx + bigSz, by + bigSz }, lighten(typeColor, 30), bigR, kDrawCornerFlagAll);
            float insetPx = bigSz * 0.15f;
            imgui->addRectFilled(dl, { bx + insetPx, by + insetPx }, { bx + bigSz - insetPx, by + bigSz - insetPx },
                                 0xA0000000, bigR * 0.5f, kDrawCornerFlagAll);
        }
        return;
    }

    // LOD 1+ (≥ 0.35): header name text or inline rename InputText
    {
        float textX = iconRight + 6.0f * effScale;
        float textY = y + (headerH - 14.0f * effScale) * 0.5f;
        float dotsReserve = data.hasMenu ? 40.0f * effScale : 24.0f * effScale;
        float maxW = (x + w - dotsReserve) - textX;

        bool isRenamingThis = m_renameActive && stableId == m_renameNodeId && effScale >= 0.60f;

        if (isRenamingThis && maxW > 20.0f)
        {
            imgui->setCursorScreenPos({ textX, textY - 2.0f * effScale });
            imgui->pushItemWidth(maxW);

            using namespace carb::imgui;
            InputTextFlags flags = kInputTextFlagEnterReturnsTrue | kInputTextFlagAutoSelectAll;
            bool enterPressed =
                imgui->inputText("##node_rename", m_renameBuf, sizeof(m_renameBuf), flags, nullptr, nullptr);

            if (!m_renameFocusSet)
            {
                imgui->setKeyboardFocusHere(-1);
                m_renameFocusSet = true;
            }

            bool active = imgui->isItemActive();

            if (enterPressed)
            {
                m_renameResult = m_renameBuf;
                m_renameResultNodeId = m_renameNodeId;
                m_renameCommitted = true;
                m_renameActive = false;
            }
            else if (m_renameFocusSet && !active)
            {
                m_renameResult = m_renameBuf;
                m_renameResultNodeId = m_renameNodeId;
                m_renameCommitted = true;
                m_renameActive = false;
            }

            imgui->popItemWidth();
        }
        else
        {
            uint32_t titleCol = lighten(data.textColor, 20);
            bool readable = (headerH > 6.0f) && (maxW > 20.0f);
            if (readable && maxW > 10.0f * effScale)
            {
                auto fullSz = imgui->calcTextSize(data.name.c_str(), nullptr, false, -1.0f);
                if (fullSz.x <= maxW)
                {
                    imgui->addText(dl, { textX, textY }, titleCol, data.name.c_str(), nullptr);
                }
                else
                {
                    std::string trunc = data.name;
                    while (trunc.size() > 1)
                    {
                        trunc.pop_back();
                        std::string test = trunc + "...";
                        auto sz = imgui->calcTextSize(test.c_str(), nullptr, false, -1.0f);
                        if (sz.x <= maxW)
                        {
                            imgui->addText(dl, { textX, textY }, titleCol, test.c_str(), nullptr);
                            break;
                        }
                    }
                }
            }
        }
    }

    // LOD 0 (≥ 0.60): expansion icon + optional "..." menu
    if (effScale >= m_style.lodThreshold0)
    {
        float midY = y + (headerH - barH) * 0.5f;

        // "..." menu dots (rightmost, only when node has menu items)
        if (data.hasMenu)
        {
            uint32_t kMenuDotCol = m_style.menuDotColor;
            float menuX = x + w - 10.0f * effScale;
            float menuDotR = m_style.menuDotRadius * effScale;
            float menuDotGap = m_style.menuDotGap * effScale;
            imgui->addCircleFilled(dl, { menuX, midY }, menuDotR, kMenuDotCol, 8);
            imgui->addCircleFilled(dl, { menuX - menuDotGap, midY }, menuDotR, kMenuDotCol, 8);
            imgui->addCircleFilled(dl, { menuX - 2.0f * menuDotGap, midY }, menuDotR, kMenuDotCol, 8);
        }

        // Expansion icon (shifts left when menu is present)
        float expCenter = data.hasMenu ? (x + w - 28.0f * effScale) : (x + w - 14.0f * effScale);

        static const char* kExpandKeys[] = {
            "__expand_open",
            "__expand_minimized",
            "__expand_closed",
        };
        int state = data.expansionState;
        if (state < 0 || state > 2)
            state = 0;
        void* expTex = getIconTexture(kExpandKeys[state]);

        float expSz = m_style.expandIconSize * effScale;
        float expX = expCenter - expSz * 0.5f;
        float expY = midY - expSz * 0.5f;

        if (expTex)
        {
            carb::imgui::TextureId tid{};
            tid.ptr = expTex;
            imgui->addImage(dl, tid, { expX, expY }, { expX + expSz, expY + expSz }, { 0.0f, 0.0f }, { 1.0f, 1.0f },
                            m_style.expandIconTint);
        }
        else
        {
            uint32_t kFallback = m_style.expandFallback;
            float cx = expCenter;
            float arm = 3.0f * effScale;
            float lw = 1.6f * effScale;
            if (state == 0)
            {
                imgui->addLine(dl, { cx - arm, midY - arm * 0.6f }, { cx, midY + arm * 0.6f }, kFallback, lw);
                imgui->addLine(dl, { cx + arm, midY - arm * 0.6f }, { cx, midY + arm * 0.6f }, kFallback, lw);
            }
            else if (state == 1)
            {
                imgui->addLine(dl, { cx - arm, midY }, { cx + arm, midY }, kFallback, lw);
            }
            else
            {
                imgui->addLine(dl, { cx - arm * 0.6f, midY - arm }, { cx + arm * 0.6f, midY }, kFallback, lw);
                imgui->addLine(dl, { cx - arm * 0.6f, midY + arm }, { cx + arm * 0.6f, midY }, kFallback, lw);
            }
        }

        // InputNode mode indicator — hidden until hover/focus expansion
        // is implemented.  The view mode state exists on the Python side
        // but the UI control is deferred.
    }
}

// ---------- Drawing: single port ----------

void GraphCanvasWidget::drawNodePort(carb::imgui::ImGui* imgui,
                                     carb::imgui::DrawList* dl,
                                     const PortData& port,
                                     float x,
                                     float portY,
                                     float w,
                                     float effScale,
                                     bool drawText) const
{
    float indent = static_cast<float>(port.level) * kGroupIndent * effScale;
    float portH = kPortHeight * effScale;
    float centerY = portY + portH * 0.5f;
    bool rightSide = port.isOutput && !port.isInput;

    // LOD-driven port size and opacity reduction
    float portSizeMul = 1.0f;
    float lodAlpha = 1.0f;
    if (effScale < m_style.lodThreshold2)
    {
        portSizeMul = m_style.portSizeLod2;
        lodAlpha = m_style.portAlphaLod2;
    } // LOD 2
    else if (effScale < m_style.lodThreshold0)
    {
        portSizeMul = m_style.portSizeLod1;
        lodAlpha = m_style.portAlphaLod1;
    } // LOD 1

    float portRadius = kPortRadius * effScale * portSizeMul;

    // Depth-based alpha fade: level >= 2 reduces alpha ~12%
    float depthAlpha = (port.level >= 2) ? 0.88f : 1.0f;
    float ifoAlpha = port.isInterfaceOnly ? m_style.interfaceOnlyPortAlpha : 1.0f;
    float combinedAlpha = depthAlpha * lodAlpha * ifoAlpha;

    auto applyAlpha = [](uint32_t col, float a) -> uint32_t {
        int origA = (col >> 24) & 0xFF;
        int newA = static_cast<int>(origA * a);
        return (col & 0x00FFFFFF) | (static_cast<uint32_t>(newA) << 24);
    };

    using namespace carb::imgui;

    // ---- Vertical guide lines for indent columns (alpha decays with depth) ----
    if (port.level > 0 && drawText)
    {
        for (int lv = 1; lv <= port.level; ++lv)
        {
            float guideX;
            if (rightSide)
                guideX = x + w - (static_cast<float>(lv - 1) * kGroupIndent + kGroupIndent * 0.5f) * effScale;
            else
                guideX = x + (static_cast<float>(lv - 1) * kGroupIndent + kGroupIndent * 0.5f) * effScale;
            int baseA = (lv == port.level) ? 0x18 : 0x0C;
            float decay = 1.0f;
            if (lv >= 3)
                decay = 0.6f;
            else if (lv >= 2)
                decay = 0.8f;
            int a = static_cast<int>(baseA * decay);
            uint32_t guideCol = (static_cast<uint32_t>(a) << 24) | 0x00FFFFFF;
            imgui->addLine(dl, { guideX, portY }, { guideX, portY + portH }, guideCol, 1.0f);
        }
    }

    // ---- Empty port (add-port placeholder) ----
    if (port.isEmpty)
    {
        float cx = rightSide ? (x + w) : x;
        imgui->addCircle(dl, { cx, centerY }, portRadius, m_style.emptyPortCircle, 24, 1.0f * effScale);
        if (drawText)
        {
            float labelY = centerY - 7.0f * effScale;
            uint32_t kAddPortTextCol = m_style.emptyPortText;
            const char* addPortLabel = "Add Port";
            if (rightSide)
            {
                auto ts = imgui->calcTextSize(addPortLabel, nullptr, false, -1.0f);
                float labelX = x + w - portRadius - 4.0f * effScale - ts.x;
                imgui->addText(dl, { labelX, labelY }, kAddPortTextCol, addPortLabel, nullptr);
            }
            else
            {
                float labelX = x + portRadius + 4.0f * effScale;
                imgui->addText(dl, { labelX, labelY }, kAddPortTextCol, addPortLabel, nullptr);
            }
        }
        return;
    }

    // ---- Port shapes (always at node edge, regardless of depth) ----
    // Varying: filled circle.  Uniform: filled rounded square (same bounding size).
    bool portUnresolved = port.isPolymorphic && !port.isResolved;
    bool drawUniform = port.isUniform && !portUnresolved;
    uint32_t portCol = portUnresolved ? m_style.unresolvedPortColor : port.color;
    float uniformR = 2.5f * effScale;

    auto drawPortShape = [&](float cx) {
        float glowR = portRadius * m_style.portGlowScale;
        float glowMul = (portUnresolved ? 0.88f : 1.0f) * (drawUniform ? 0.85f : 1.0f);
        uint32_t glowCol = (portCol & 0x00FFFFFF) | 0x18000000;
        if (drawUniform)
        {
            imgui->addRectFilled(dl, { cx - glowR, centerY - glowR }, { cx + glowR, centerY + glowR },
                                 applyAlpha(glowCol, combinedAlpha * glowMul), uniformR, kDrawCornerFlagAll);
            imgui->addRectFilled(dl, { cx - portRadius, centerY - portRadius }, { cx + portRadius, centerY + portRadius },
                                 applyAlpha(portCol, combinedAlpha), uniformR, kDrawCornerFlagAll);
        }
        else
        {
            imgui->addCircleFilled(dl, { cx, centerY }, glowR, applyAlpha(glowCol, combinedAlpha * glowMul), 16);
            if (portUnresolved)
                imgui->addCircle(
                    dl, { cx, centerY }, portRadius, applyAlpha(portCol, combinedAlpha), 24, 1.5f * effScale);
            else
                imgui->addCircleFilled(dl, { cx, centerY }, portRadius, applyAlpha(portCol, combinedAlpha), 24);
        }
    };

    auto drawPortErrorHalo = [&](float cx) {
        if (!port.hasError)
            return;
        uint32_t errRGB = m_style.errorColor & 0x00FFFFFF;
        float haloR = portRadius + m_style.errorPortHaloWidth * effScale;
        imgui->addCircleFilled(dl, { cx, centerY }, haloR, (m_style.errorPortHaloAlpha << 24) | errRGB, 24);
        imgui->addCircle(dl, { cx, centerY }, portRadius + m_style.errorPortRingWidth * effScale,
                         (m_style.errorPortRingAlpha << 24) | errRGB, 24, m_style.errorPortRingWidth * effScale);
    };

    if (port.isInput && !port.isGroup)
    {
        float cx = x;
        drawPortShape(cx);
        drawPortErrorHalo(cx);
        if (port.connectedTarget)
            imgui->addCircleFilled(
                dl, { cx, centerY }, portRadius * 0.5f, applyAlpha(m_style.connectedDot, lodAlpha), 16);
    }
    if (port.isOutput && !port.isGroup)
    {
        float cx = x + w;
        drawPortShape(cx);
        drawPortErrorHalo(cx);
        if (port.connectedSource)
            imgui->addCircleFilled(
                dl, { cx, centerY }, portRadius * 0.5f, applyAlpha(m_style.connectedDot, lodAlpha), 16);
    }

    // ---- Group expand/collapse indicator ----
    if (port.isGroup)
    {
        float gx = rightSide ? (x + w) : x;
        float half = kExpandIconSize * 0.5f * effScale;
        uint32_t gc = m_style.groupIconColor;
        imgui->addRectFilled(dl, { gx - half - 1.0f * effScale, centerY - half - 1.0f * effScale },
                             { gx + half + 1.0f * effScale, centerY + half + 1.0f * effScale }, gc, 2.0f * effScale,
                             kDrawCornerFlagAll);
        uint32_t symColor = 0xFFFFFFFF;
        imgui->addLine(dl, { gx - half, centerY }, { gx + half, centerY }, symColor, 1.5f * effScale);
        if (!port.isExpanded)
            imgui->addLine(dl, { gx, centerY - half }, { gx, centerY + half }, symColor, 1.5f * effScale);
    }

    // ---- Text labels ----
    if (drawText)
    {
        float labelY = centerY - 7.0f * effScale;

        uint32_t col = port.isGroup ? m_style.groupLabelColor : applyAlpha(m_style.portLabelColor, depthAlpha * ifoAlpha);

        if (rightSide)
        {
            float labelIndent = portRadius + indent + 4.0f * effScale;
            if (port.isGroup)
                labelIndent += kExpandIconSize * effScale + 2.0f * effScale;
            auto ts = imgui->calcTextSize(port.name.c_str(), nullptr, false, -1.0f);
            float rightX = x + w - labelIndent - ts.x;
            imgui->addText(dl, { rightX, labelY }, col, port.name.c_str(), nullptr);
        }
        else
        {
            float labelIndent = portRadius + indent + 4.0f * effScale;
            if (port.isGroup)
                labelIndent += kExpandIconSize * effScale + 2.0f * effScale;
            float labelX = x + labelIndent;
            imgui->addText(dl, { labelX, labelY }, col, port.name.c_str(), nullptr);
        }
    }

    // ---- Branch connector lines for sub-ports ----
    if (port.level > 0 && drawText)
    {
        bool isLast = (port.relativePosition == port.parentChildCount - 1);
        float topY = portY;
        float bottomY = isLast ? centerY : (portY + portH);
        uint32_t lineCol = applyAlpha(0xFF585858, depthAlpha);

        if (rightSide)
        {
            float bx = x + w - (static_cast<float>(port.level - 1) * kGroupIndent + kGroupIndent * 0.5f) * effScale;
            imgui->addLine(dl, { bx, topY }, { bx, bottomY }, lineCol, 1.0f * effScale);
            imgui->addLine(
                dl, { bx, centerY }, { bx - kGroupIndent * 0.35f * effScale, centerY }, lineCol, 1.0f * effScale);
        }
        else
        {
            float bx = x + (static_cast<float>(port.level - 1) * kGroupIndent + kGroupIndent * 0.5f) * effScale;
            imgui->addLine(dl, { bx, topY }, { bx, bottomY }, lineCol, 1.0f * effScale);
            imgui->addLine(
                dl, { bx, centerY }, { bx + kGroupIndent * 0.35f * effScale, centerY }, lineCol, 1.0f * effScale);
        }
    }
}

// ---------- Drawing: InputNode port (compact, with emphasis and group headers) ----------

void GraphCanvasWidget::drawInputNodePort(carb::imgui::ImGui* imgui,
                                          carb::imgui::DrawList* dl,
                                          const PortData& port,
                                          float x,
                                          float portY,
                                          float w,
                                          float rowHeight,
                                          float effScale,
                                          bool drawText) const
{
    if (port.isHidden)
        return;

    using namespace carb::imgui;

    float portH = rowHeight * effScale;
    float centerY = portY + portH * 0.5f;
    bool rightSide = port.isOutput && !port.isInput;

    // io_state-based emphasis: label, port, and glow alpha tuned per context state
    float ioLabelAlpha = m_style.ioActiveAlpha;
    float ioPortAlpha = m_style.ioActiveAlpha;
    float ioGlowAlpha = m_style.ioActiveAlpha;
    if (port.ioState == 1) // USED_IN_OTHER
    {
        ioLabelAlpha = m_style.ioOtherLabelAlpha;
        ioPortAlpha = m_style.ioOtherPortAlpha;
        ioGlowAlpha = m_style.ioOtherGlowAlpha;
    }
    else if (port.ioState == 2) // UNUSED
    {
        ioLabelAlpha = m_style.ioUnusedLabelAlpha;
        ioPortAlpha = m_style.ioUnusedPortAlpha;
        ioGlowAlpha = m_style.ioUnusedGlowAlpha;
    }

    // Hover restore: if the mouse is over this specific port row,
    // temporarily bring it back to full readability.
    if (port.ioState > 0)
    {
        float my = portY + portH * 0.5f;
        auto mpos = imgui->getMousePos();
        if (mpos.x >= x && mpos.x <= x + w && std::abs(mpos.y - my) < portH * 0.5f)
        {
            ioLabelAlpha = m_style.ioActiveAlpha;
            ioPortAlpha = m_style.ioActiveAlpha;
            ioGlowAlpha = m_style.ioActiveAlpha;
        }
    }

    auto applyAlpha = [](uint32_t col, float a) -> uint32_t {
        int origA = (col >> 24) & 0xFF;
        int newA = static_cast<int>(origA * a);
        return (col & 0x00FFFFFF) | (static_cast<uint32_t>(newA) << 24);
    };

    // ---- Group header rendering (synthetic headers AND model groups) ----
    if (port.isGroupHeader || port.isGroup)
    {
        if (drawText)
        {
            float labelY = centerY - 6.0f * effScale;
            uint32_t iconCol = m_style.groupIconColor;
            uint32_t lblCol = m_style.groupLabelColor;

            // +/- collapse indicator
            float half = 4.0f * effScale;
            float indX = x + 6.0f * effScale;
            imgui->addLine(dl, { indX - half, centerY }, { indX + half, centerY }, iconCol, 1.2f * effScale);
            if (port.groupCollapsed || !port.isExpanded)
                imgui->addLine(dl, { indX, centerY - half }, { indX, centerY + half }, iconCol, 1.2f * effScale);

            float labelX = indX + half + 4.0f * effScale;
            imgui->addText(dl, { labelX, labelY }, lblCol, port.name.c_str(), nullptr);

            // Subtle separator line
            float sepY = portY + portH - 1.0f * effScale;
            imgui->addLine(dl, { x + 4.0f * effScale, sepY }, { x + w - 4.0f * effScale, sepY },
                           applyAlpha(0xFF555555, 0.5f), 1.0f);
        }
        return;
    }

    // ---- Empty port (Add Input) ----
    if (port.isEmpty)
    {
        float portRadius = kPortRadius * effScale;
        float cx = rightSide ? (x + w) : x;
        imgui->addCircle(dl, { cx, centerY }, portRadius, m_style.emptyPortCircle, 24, 1.0f * effScale);
        if (drawText)
        {
            float labelY = centerY - 6.0f * effScale;
            const char* addLabel = "Add Port";
            if (rightSide)
            {
                auto ts = imgui->calcTextSize(addLabel, nullptr, false, -1.0f);
                imgui->addText(dl, { x + w - portRadius - 4.0f * effScale - ts.x, labelY }, m_style.emptyPortText,
                               addLabel, nullptr);
            }
            else
            {
                imgui->addText(
                    dl, { x + portRadius + 4.0f * effScale, labelY }, m_style.emptyPortText, addLabel, nullptr);
            }
        }
        return;
    }

    // ---- Normal InputNode port (compact) ----
    float portRadius = kPortRadius * effScale * 0.85f;
    float indent = static_cast<float>(port.level) * kGroupIndent * effScale;

    // Port shape (always at node edge)
    bool portUnresolved = port.isPolymorphic && !port.isResolved;
    bool drawUniform = port.isUniform && !portUnresolved;
    uint32_t portCol = portUnresolved ? m_style.unresolvedPortColor : port.color;
    float uniformR = 2.5f * effScale;

    auto drawPortShape = [&](float cx) {
        uint32_t col = applyAlpha(portCol, ioPortAlpha);
        float glowR = portRadius * m_style.portGlowScale;
        uint32_t glowCol = applyAlpha((portCol & 0x00FFFFFF) | 0x18000000, ioGlowAlpha);
        if (drawUniform)
        {
            imgui->addRectFilled(dl, { cx - glowR, centerY - glowR }, { cx + glowR, centerY + glowR }, glowCol,
                                 uniformR, kDrawCornerFlagAll);
            imgui->addRectFilled(dl, { cx - portRadius, centerY - portRadius },
                                 { cx + portRadius, centerY + portRadius }, col, uniformR, kDrawCornerFlagAll);
        }
        else
        {
            imgui->addCircleFilled(dl, { cx, centerY }, glowR, glowCol, 16);
            if (portUnresolved)
                imgui->addCircle(dl, { cx, centerY }, portRadius, col, 24, 1.5f * effScale);
            else
                imgui->addCircleFilled(dl, { cx, centerY }, portRadius, col, 24);
        }
    };

    auto drawInputPortErrorHalo = [&](float cx) {
        if (!port.hasError)
            return;
        uint32_t errRGB = m_style.errorColor & 0x00FFFFFF;
        float haloR = portRadius + m_style.errorPortHaloWidth * effScale;
        imgui->addCircleFilled(dl, { cx, centerY }, haloR, (m_style.errorPortHaloAlpha << 24) | errRGB, 24);
        imgui->addCircle(dl, { cx, centerY }, portRadius + m_style.errorPortRingWidth * effScale,
                         (m_style.errorPortRingAlpha << 24) | errRGB, 24, m_style.errorPortRingWidth * effScale);
    };

    if (port.isInput && !port.isGroup)
    {
        drawPortShape(x);
        drawInputPortErrorHalo(x);
        if (port.connectedTarget)
            imgui->addCircleFilled(
                dl, { x, centerY }, portRadius * 0.5f, applyAlpha(m_style.connectedDot, ioPortAlpha), 16);
    }
    if (port.isOutput && !port.isGroup)
    {
        drawPortShape(x + w);
        drawInputPortErrorHalo(x + w);
        if (port.connectedSource)
            imgui->addCircleFilled(
                dl, { x + w, centerY }, portRadius * 0.5f, applyAlpha(m_style.connectedDot, ioPortAlpha), 16);
    }

    // ---- Text label ----
    if (drawText)
    {
        float labelY = centerY - 6.0f * effScale;
        uint32_t labelCol = applyAlpha(m_style.portLabelColor, ioLabelAlpha);

        if (rightSide)
        {
            float labelIndent = portRadius + indent + 4.0f * effScale;
            auto ts = imgui->calcTextSize(port.name.c_str(), nullptr, false, -1.0f);
            imgui->addText(dl, { x + w - labelIndent - ts.x, labelY }, labelCol, port.name.c_str(), nullptr);
        }
        else
        {
            float labelIndent = portRadius + indent + 4.0f * effScale;
            imgui->addText(dl, { x + labelIndent, labelY }, labelCol, port.name.c_str(), nullptr);
        }
    }
}

// ---------- Drawing: single backdrop node ----------

void GraphCanvasWidget::drawBackdrop(carb::imgui::ImGui* imgui,
                                     carb::imgui::DrawList* dl,
                                     const SceneNodeEntry& node,
                                     float x,
                                     float y,
                                     float w,
                                     float h,
                                     float effScale)
{
    using namespace carb::imgui;
    const auto& data = node.data;
    float r = kBorderRadius * effScale;

    uint32_t kSelColor = m_style.selectionColor;
    bool bdSelected = data.selected;

    uint32_t baseColor = data.backgroundColor;
    auto desaturate = [](uint32_t col, float factor) -> uint32_t {
        int cr = col & 0xFF, cg = (col >> 8) & 0xFF, cb = (col >> 16) & 0xFF;
        int lum = (cr * 77 + cg * 150 + cb * 29) >> 8;
        cr = static_cast<int>(cr + (lum - cr) * factor);
        cg = static_cast<int>(cg + (lum - cg) * factor);
        cb = static_cast<int>(cb + (lum - cb) * factor);
        return (col & 0xFF000000) | (cb << 16) | (cg << 8) | cr;
    };

    // Stacking: deeper backdrops slightly darker
    int depth = std::max(0, std::min(data.stackingOrder, 3));
    float depthDarken = 1.0f - depth * m_style.backdropDepthDarken;

    // Body: very transparent annotation surface
    uint32_t mutedBase = desaturate(baseColor, m_style.backdropDesaturate);
    uint8_t bgR2 = static_cast<uint8_t>(std::min(255.0f, (mutedBase & 0xFF) * m_style.backdropBodyBright * depthDarken));
    uint8_t bgG2 =
        static_cast<uint8_t>(std::min(255.0f, ((mutedBase >> 8) & 0xFF) * m_style.backdropBodyBright * depthDarken));
    uint8_t bgB2 =
        static_cast<uint8_t>(std::min(255.0f, ((mutedBase >> 16) & 0xFF) * m_style.backdropBodyBright * depthDarken));
    uint32_t kBodyAlpha = m_style.backdropBodyAlpha;
    uint32_t darkBg = (kBodyAlpha << 24) | (static_cast<uint32_t>(bgB2) << 16) | (static_cast<uint32_t>(bgG2) << 8) |
                      static_cast<uint32_t>(bgR2);
    imgui->addRectFilled(dl, { x, y }, { x + w, y + h }, darkBg, r, kDrawCornerFlagAll);

    // Border: softened
    uint32_t borderCol = desaturate(baseColor, 0.25f);
    uint32_t softBorder = (borderCol & 0x00FFFFFF) | 0x80000000;
    imgui->addRect(dl, { x, y }, { x + w, y + h }, softBorder, r, kDrawCornerFlagAll, 1.0f * effScale);

    // Selection — centered stroke straddling the node edge
    if (bdSelected)
    {
        float selW = 3.0f * effScale;
        float selOuter = selW * 0.5f;
        float selGlowOut = selOuter + 2.0f * effScale;
        uint32_t selRGB = kSelColor & 0x00FFFFFF;
        imgui->addRect(dl, { x - selGlowOut, y - selGlowOut }, { x + w + selGlowOut, y + h + selGlowOut },
                       selRGB | (m_style.selectionGlowAlpha << 24), r + selGlowOut, kDrawCornerFlagAll,
                       selW + 4.0f * effScale);
        imgui->addRect(dl, { x - selOuter, y - selOuter }, { x + w + selOuter, y + h + selOuter },
                       selRGB | (m_style.selectionOutlineAlpha << 24), r + selOuter, kDrawCornerFlagAll, selW);

        float selInner = selW * 0.5f;
        float ix = x + selInner, iy = y + selInner;
        float iw = w - 2.0f * selInner, ih = h - 2.0f * selInner;
        float ir = std::max(r - selInner, 0.0f);
        imgui->addRectFilled(dl, { ix, iy }, { ix + iw, iy + ih }, darkBg, ir, kDrawCornerFlagAll);
    }

    // Header strip: stronger than body, anchors the title
    float headerH = kHeaderHeight * effScale;
    uint32_t kHdrAlpha = m_style.backdropHeaderAlpha;
    uint8_t hR3 = static_cast<uint8_t>(std::min(255.0f, (mutedBase & 0xFF) * m_style.backdropHeaderBright * depthDarken));
    uint8_t hG3 =
        static_cast<uint8_t>(std::min(255.0f, ((mutedBase >> 8) & 0xFF) * m_style.backdropHeaderBright * depthDarken));
    uint8_t hB3 =
        static_cast<uint8_t>(std::min(255.0f, ((mutedBase >> 16) & 0xFF) * m_style.backdropHeaderBright * depthDarken));
    uint32_t bdHeaderCol = (kHdrAlpha << 24) | (static_cast<uint32_t>(hB3) << 16) | (static_cast<uint32_t>(hG3) << 8) |
                           static_cast<uint32_t>(hR3);
    imgui->addRectFilled(dl, { x, y }, { x + w, y + headerH }, bdHeaderCol, r, kDrawCornerFlagTop);

    float sepY = std::floor(y + headerH) + 0.5f;
    imgui->addLine(dl, { x, sepY }, { x + w, sepY }, softBorder, 1.0f);

    // Color swatch
    float swatchSz = 14.0f * effScale;
    float swatchPad = (headerH - swatchSz) * 0.5f;
    float swX = x + swatchPad + 2.0f * effScale;
    float swY = y + swatchPad;
    imgui->addRectFilled(
        dl, { swX, swY }, { swX + swatchSz, swY + swatchSz }, baseColor, 2.0f * effScale, kDrawCornerFlagAll);
    imgui->addRect(dl, { swX, swY }, { swX + swatchSz, swY + swatchSz }, 0x60FFFFFF, 2.0f * effScale,
                   kDrawCornerFlagAll, 1.0f * effScale);

    // "..." menu dots for backdrop (same style as regular nodes)
    if (data.hasMenu && effScale >= m_style.lodThreshold0)
    {
        float midY = y + headerH * 0.5f;
        float menuX = x + w - 10.0f * effScale;
        float menuDotR = m_style.menuDotRadius * effScale;
        float menuDotGap = m_style.menuDotGap * effScale;
        uint32_t kMenuDotCol = m_style.menuDotColor;
        imgui->addCircleFilled(dl, { menuX, midY }, menuDotR, kMenuDotCol, 8);
        imgui->addCircleFilled(dl, { menuX - menuDotGap, midY }, menuDotR, kMenuDotCol, 8);
        imgui->addCircleFilled(dl, { menuX - 2.0f * menuDotGap, midY }, menuDotR, kMenuDotCol, 8);
    }

    // Double-click detection for backdrop areas
    auto mpos = imgui->getMousePos();
    bool dblClick = imgui->isMouseDoubleClicked(0);

    // Title text with opaque backing panel + inline rename on double-click
    uint32_t kTextBackingCol = m_style.textBackingColor;
    if (effScale >= 0.35f)
    {
        float textX = swX + swatchSz + 6.0f * effScale;
        float textY = y + (headerH - 14.0f * effScale) * 0.5f;
        float titleMaxW = w - (swatchSz + swatchPad + 18.0f) * effScale;

        bool isRenamingThis = m_renameActive && node.stableId == m_renameNodeId;

        if (isRenamingThis)
        {
            imgui->setCursorScreenPos({ textX, textY - 2.0f * effScale });
            imgui->pushItemWidth(titleMaxW);
            using namespace carb::imgui;
            InputTextFlags flags = kInputTextFlagEnterReturnsTrue | kInputTextFlagAutoSelectAll;
            bool enterPressed =
                imgui->inputText("##bd_rename", m_renameBuf, sizeof(m_renameBuf), flags, nullptr, nullptr);
            if (!m_renameFocusSet)
            {
                imgui->setKeyboardFocusHere(-1);
                m_renameFocusSet = true;
            }
            bool active = imgui->isItemActive();
            if (enterPressed || (m_renameFocusSet && !active))
            {
                m_renameResult = m_renameBuf;
                m_renameResultNodeId = m_renameNodeId;
                m_renameCommitted = true;
                m_renameActive = false;
            }
            imgui->popItemWidth();
        }
        else
        {
            auto ts = imgui->calcTextSize(data.name.c_str(), nullptr, false, -1.0f);
            float pad = 3.0f * effScale;
            imgui->addRectFilled(dl, { textX - pad, textY - pad * 0.5f },
                                 { textX + ts.x + pad, textY + ts.y + pad * 0.5f }, kTextBackingCol, 3.0f * effScale,
                                 kDrawCornerFlagAll);
            imgui->addText(dl, { textX, textY }, m_style.backdropTitleColor, data.name.c_str(), nullptr);

            if (dblClick && !m_renameActive && !m_descEditActive && mpos.x >= textX && mpos.x <= x + w && mpos.y >= y &&
                mpos.y <= y + headerH)
            {
                startRename(node.stableId, data.name);
            }
        }
    }

    // Description text — word-wrapped, clipped to body, with inline multiline edit
    if (effScale >= 0.60f)
    {
        float descX = x + 12.0f * effScale;
        float descY = y + headerH + 10.0f * effScale;
        float maxW = w - 24.0f * effScale;
        float maxH = h - headerH - 20.0f * effScale;
        float pad = 3.0f * effScale;

        bool isEditingThis = m_descEditActive && node.stableId == m_descEditNodeId;

        if (isEditingThis)
        {
            imgui->setCursorScreenPos({ descX, descY });
            imgui->pushItemWidth(maxW);
            float editH = std::max(maxH, 40.0f * effScale);
            imgui->inputTextMultiline(
                "##desc_edit", m_descEditBuf, sizeof(m_descEditBuf), { maxW, editH }, 0, nullptr, nullptr);

            if (!m_descEditFocusSet)
            {
                imgui->setKeyboardFocusHere(-1);
                m_descEditFocusSet = true;
            }
            else
            {
                bool active = imgui->isItemActive();
                if (!active)
                {
                    m_descEditResult = m_descEditBuf;
                    m_descEditResultNodeId = m_descEditNodeId;
                    m_descEditCommitted = true;
                    m_descEditActive = false;
                }
            }
            imgui->popItemWidth();
        }
        else
        {
            if (dblClick && !m_descEditActive && !m_renameActive && mpos.x >= x && mpos.x <= x + w &&
                mpos.y >= y + headerH && mpos.y <= y + h)
            {
                startDescEdit(node.stableId, data.description);
            }

            if (!data.description.empty())
            {
                imgui->pushClipRect({ descX, descY }, { x + w - pad, y + h - pad }, true);

                const std::string& text = data.description;
                float lineH = imgui->calcTextSize("Mg", nullptr, false, -1.0f).y;
                float curY = descY;
                size_t pos = 0;

                while (pos < text.size() && curY < y + h - pad)
                {
                    size_t lineEnd = text.find('\n', pos);
                    if (lineEnd == std::string::npos)
                        lineEnd = text.size();
                    std::string paragraph = text.substr(pos, lineEnd - pos);

                    if (paragraph.empty())
                    {
                        curY += lineH;
                        pos = lineEnd + 1;
                        continue;
                    }

                    size_t wp = 0;
                    while (wp < paragraph.size())
                    {
                        std::string line;
                        while (wp < paragraph.size())
                        {
                            size_t sp = paragraph.find(' ', wp);
                            if (sp == std::string::npos)
                                sp = paragraph.size();
                            std::string word = paragraph.substr(wp, sp - wp);
                            std::string test = line.empty() ? word : line + " " + word;
                            auto ts = imgui->calcTextSize(test.c_str(), nullptr, false, -1.0f);
                            if (!line.empty() && ts.x > maxW)
                                break;
                            line = std::move(test);
                            wp = sp + 1;
                            if (sp == paragraph.size())
                                break;
                        }

                        if (!line.empty())
                        {
                            auto ls = imgui->calcTextSize(line.c_str(), nullptr, false, -1.0f);
                            imgui->addRectFilled(dl, { descX - pad, curY - pad * 0.5f },
                                                 { descX + ls.x + pad, curY + ls.y + pad * 0.5f }, kTextBackingCol,
                                                 3.0f * effScale, kDrawCornerFlagAll);
                            imgui->addText(dl, { descX, curY }, m_style.backdropDescColor, line.c_str(), nullptr);
                            curY += lineH + 1.0f * effScale;
                        }
                    }
                    pos = lineEnd + 1;
                }

                imgui->popClipRect();
            }
        }
    }

    // Resize handle
    {
        float handleSz = 14.0f * effScale;
        float hx0 = x + w - handleSz;
        float hy0 = y + h;
        float hx1 = x + w;
        float hy1 = y + h - handleSz;
        imgui->addTriangleFilled(dl, { hx0, hy0 }, { hx1, hy1 }, { hx1, hy0 }, softBorder);
    }
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

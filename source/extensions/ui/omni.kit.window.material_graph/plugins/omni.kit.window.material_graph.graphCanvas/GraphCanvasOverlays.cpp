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

#include <cmath>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Draws major and minor grid lines over the visible window region. Spacing follows
// the style; when zoomed out, minor lines merge into coarser steps so lines stay
// readable and the total line count stays under a fixed cap.
void GraphCanvasWidget::drawGrid(
    carb::imgui::ImGui* imgui, carb::imgui::DrawList* dl, float originX, float originY, float effScale) const
{
    if (effScale <= 0.0f)
        return;

    auto clipMin = imgui->getWindowContentRegionMin();
    auto clipMax = imgui->getWindowContentRegionMax();
    auto winPos = imgui->getWindowPos();
    float screenLeft = winPos.x + clipMin.x;
    float screenTop = winPos.y + clipMin.y;
    float screenRight = winPos.x + clipMax.x;
    float screenBottom = winPos.y + clipMax.y;

    if (screenRight <= screenLeft || screenBottom <= screenTop)
        return;

    float kMinorSpacing = m_style.gridMinorSpacing;
    int kMajorEvery = m_style.gridMajorEvery;
    uint32_t minorColor = m_style.gridMinorColor;
    uint32_t majorColor = m_style.gridMajorColor;

    float screenSpacing = kMinorSpacing * effScale;

    float drawSpacing = kMinorSpacing;
    int drawMajor = kMajorEvery;
    if (screenSpacing < 6.0f)
    {
        drawSpacing = kMinorSpacing * kMajorEvery;
        drawMajor = 1;
        if (drawSpacing * effScale < 6.0f)
            return;
    }

    float canvasLeft = (screenLeft - originX) / effScale;
    float canvasTop = (screenTop - originY) / effScale;
    float canvasRight = (screenRight - originX) / effScale;
    float canvasBottom = (screenBottom - originY) / effScale;

    int i0 = static_cast<int>(std::floor(canvasLeft / drawSpacing));
    int i1 = static_cast<int>(std::ceil(canvasRight / drawSpacing));
    int j0 = static_cast<int>(std::floor(canvasTop / drawSpacing));
    int j1 = static_cast<int>(std::ceil(canvasBottom / drawSpacing));

    constexpr int kMaxLines = 500;
    if ((i1 - i0) + (j1 - j0) > kMaxLines)
        return;

    for (int i = i0; i <= i1; ++i)
    {
        float sx = originX + static_cast<float>(i) * drawSpacing * effScale;
        uint32_t col = (i % drawMajor == 0) ? majorColor : minorColor;
        imgui->addLine(dl, { sx, screenTop }, { sx, screenBottom }, col, 1.0f);
    }
    for (int j = j0; j <= j1; ++j)
    {
        float sy = originY + static_cast<float>(j) * drawSpacing * effScale;
        uint32_t col = (j % drawMajor == 0) ? majorColor : minorColor;
        imgui->addLine(dl, { screenLeft, sy }, { screenRight, sy }, col, 1.0f);
    }
}

// Draws a single connection as a cubic Bezier from (x0,y0) to (x1,y1). Control points
// are offset horizontally by curveAmount so edges read as left-to-right flow.
void GraphCanvasWidget::drawConnection(carb::imgui::ImGui* imgui,
                                       carb::imgui::DrawList* dl,
                                       float x0,
                                       float y0,
                                       float x1,
                                       float y1,
                                       uint32_t color,
                                       float thickness,
                                       float curveAmount) const
{
    float cp1x = x0 + curveAmount;
    float cp1y = y0;
    float cp2x = x1 - curveAmount;
    float cp2y = y1;

    imgui->addBezierCurve(dl, { x0, y0 }, { cp1x, cp1y }, { cp2x, cp2y }, { x1, y1 }, color, thickness, 0);
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

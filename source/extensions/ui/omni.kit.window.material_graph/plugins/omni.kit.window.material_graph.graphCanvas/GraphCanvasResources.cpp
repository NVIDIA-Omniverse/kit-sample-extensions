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
#include "GraphCanvasResourceUtils.h"

#include <carb/Framework.h>
#include <carb/imgui/ImGui.h>
#include <omni/ui/KitGlyphManagerAcquire.h>

#include <algorithm>
#include <cmath>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Lazily acquires the carb ImGui interface once and reuses it for font measurement
// and texture upload paths that run before the main widget draw.
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

// Loads each available IGlyphManager font style once, records its measured cap height,
// and sorts entries so pickFont can choose the closest native size to a desired height.
void GraphCanvasWidget::ensureFonts()
{
    if (m_fontsLoaded)
        return;
    m_fontsLoaded = true;

    auto* gm = omni::ui::acquireGlyphManager();
    if (!gm)
        return;

    auto* imgui = acquireImGui();
    if (!imgui)
        return;

    static const omni::ui::FontStyle styles[] = {
        omni::ui::FontStyle::eXXXS,       omni::ui::FontStyle::eXXS,    omni::ui::FontStyle::eExtraSmall,
        omni::ui::FontStyle::eSmall,      omni::ui::FontStyle::eNormal, omni::ui::FontStyle::eLarge,
        omni::ui::FontStyle::eExtraLarge, omni::ui::FontStyle::eXXL,    omni::ui::FontStyle::eXXXL,
        omni::ui::FontStyle::eUltra,
    };

    for (auto style : styles)
    {
        auto* f = reinterpret_cast<carb::imgui::Font*>(gm->getFont(style));
        if (!f)
            continue;

        // Measure the actual rasterized size (accounts for DPI and font scale)
        imgui->pushFont(f);
        imgui->setWindowFontScale(1.0f);
        auto ts = imgui->calcTextSize("Mg", nullptr, false, -1.0f);
        imgui->setWindowFontScale(1.0f);
        imgui->popFont();

        float actualSize = ts.y;
        if (actualSize > 0.0f)
            m_fonts.push_back({ actualSize, f });
    }

    std::sort(m_fonts.begin(), m_fonts.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
}

// Chooses the loaded font whose native pixel height is closest to desiredSize on a log
// scale, and returns a scale factor so drawing can match the requested size exactly.
std::pair<carb::imgui::Font*, float> GraphCanvasWidget::pickFont(float desiredSize) const
{
    if (m_fonts.empty())
        return { nullptr, 1.0f };

    // Pick the font whose correction ratio (desired/native) is closest to 1.0.
    carb::imgui::Font* best = m_fonts.front().second;
    float bestSize = m_fonts.front().first;
    float bestDist = std::abs(std::log(desiredSize / bestSize));

    for (const auto& [sz, f] : m_fonts)
    {
        float dist = std::abs(std::log(desiredSize / sz));
        if (dist < bestDist)
        {
            best = f;
            bestSize = sz;
            bestDist = dist;
        }
    }

    float correction = (bestSize > 0.0f) ? desiredSize / bestSize : 1.0f;
    return { best, correction };
}

// Signed distance to a rounded rectangle centered in a square T-pixel texture; used to anti-alias
// the fill and border when rasterizing the background and shadow atlases.
static float roundedRectSDF(float fx, float fy, float halfT, float boxHalf, float R)
{
    float qx = std::abs(fx - halfT) - boxHalf;
    float qy = std::abs(fy - halfT) - boxHalf;
    float outsideDist = std::sqrt(std::max(qx, 0.0f) * std::max(qx, 0.0f) + std::max(qy, 0.0f) * std::max(qy, 0.0f));
    float insideDist = std::min(std::max(qx, qy), 0.0f);
    return outsideDist + insideDist - R;
}

// Creates the node background and soft-shadow GPU textures once: grey rounded quad
// with a narrow AA band, plus a second atlas with wider AA for a softer outer falloff.
void GraphCanvasWidget::ensureBgTexture()
{
    if (m_bgTexCreated)
        return;
    m_bgTexCreated = true;

    constexpr int T = kBgTexSize;
    constexpr int C = kBgTexCorner;
    constexpr float R = static_cast<float>(C);
    constexpr float halfT = static_cast<float>(T) * 0.5f;
    constexpr float boxHalf = halfT - R;

    // Background texture with baked border (tight AA for crisp edges)
    {
        constexpr float kAAWidth = 2.0f;
        std::vector<uint8_t> pixels(T * T * 4, 0);

        for (int py = 0; py < T; ++py)
        {
            for (int px = 0; px < T; ++px)
            {
                float fx = static_cast<float>(px) + 0.5f;
                float fy = static_cast<float>(py) + 0.5f;
                float dist = roundedRectSDF(fx, fy, halfT, boxHalf, R);

                float alpha;
                if (dist < 0.0f)
                    alpha = 1.0f;
                else if (dist < kAAWidth)
                    alpha = 1.0f - dist / kAAWidth;
                else
                    alpha = 0.0f;

                uint8_t grey = 255;

                int idx = (py * T + px) * 4;
                pixels[idx + 0] = grey;
                pixels[idx + 1] = grey;
                pixels[idx + 2] = grey;
                pixels[idx + 3] = static_cast<uint8_t>(alpha * 255.0f);
            }
        }

        m_bgTexProvider = std::make_shared<omni::ui::ByteImageProvider>();
        m_bgTexProvider->setBytesData(pixels.data(), { static_cast<uint32_t>(T), static_cast<uint32_t>(T) });
        m_bgTexId = m_bgTexProvider->getImGuiReference();
    }

    // Shadow texture (wider AA for soft falloff outside the rounded shape)
    {
        constexpr float kShadowAA = 8.0f;
        std::vector<uint8_t> pixels(T * T * 4, 0);

        for (int py = 0; py < T; ++py)
        {
            for (int px = 0; px < T; ++px)
            {
                float fx = static_cast<float>(px) + 0.5f;
                float fy = static_cast<float>(py) + 0.5f;
                float dist = roundedRectSDF(fx, fy, halfT, boxHalf, R);

                float alpha;
                if (dist < 0.0f)
                    alpha = 1.0f;
                else if (dist < kShadowAA)
                    alpha = 1.0f - dist / kShadowAA;
                else
                    alpha = 0.0f;

                int idx = (py * T + px) * 4;
                pixels[idx + 0] = 255;
                pixels[idx + 1] = 255;
                pixels[idx + 2] = 255;
                pixels[idx + 3] = static_cast<uint8_t>(alpha * 255.0f);
            }
        }

        m_shadowTexProvider = std::make_shared<omni::ui::ByteImageProvider>();
        m_shadowTexProvider->setBytesData(pixels.data(), { static_cast<uint32_t>(T), static_cast<uint32_t>(T) });
        m_shadowTexId = m_shadowTexProvider->getImGuiReference();
    }
}

// Draws a textured rounded rectangle as nine UV patches so corners stay fixed radius
// while edges and center stretch; cornerPx clamps so tiny boxes do not invert patches.
void GraphCanvasWidget::draw9Slice(carb::imgui::ImGui* imgui,
                                   carb::imgui::DrawList* dl,
                                   void* texId,
                                   float x,
                                   float y,
                                   float w,
                                   float h,
                                   float cornerPx,
                                   uint32_t col) const
{
    using namespace carb::imgui;
    constexpr float T = static_cast<float>(kBgTexSize);
    constexpr float C = static_cast<float>(kBgTexCorner);
    float uvC = C / T;

    float cp = std::min(cornerPx, std::min(w * 0.5f, h * 0.5f));

    TextureId tid{};
    tid.ptr = texId;

    float x0 = x, x1 = x + cp, x2 = x + w - cp, x3 = x + w;
    float y0 = y, y1 = y + cp, y2 = y + h - cp, y3 = y + h;
    float u0 = 0.0f, u1 = uvC, u2 = 1.0f - uvC, u3 = 1.0f;
    float v0 = 0.0f, v1 = uvC, v2 = 1.0f - uvC, v3 = 1.0f;

    // TL, T, TR
    imgui->addImage(dl, tid, { x0, y0 }, { x1, y1 }, { u0, v0 }, { u1, v1 }, col);
    imgui->addImage(dl, tid, { x1, y0 }, { x2, y1 }, { u1, v0 }, { u2, v1 }, col);
    imgui->addImage(dl, tid, { x2, y0 }, { x3, y1 }, { u2, v0 }, { u3, v1 }, col);
    // L, C, R
    imgui->addImage(dl, tid, { x0, y1 }, { x1, y2 }, { u0, v1 }, { u1, v2 }, col);
    imgui->addImage(dl, tid, { x1, y1 }, { x2, y2 }, { u1, v1 }, { u2, v2 }, col);
    imgui->addImage(dl, tid, { x2, y1 }, { x3, y2 }, { u2, v1 }, { u3, v2 }, col);
    // BL, B, BR
    imgui->addImage(dl, tid, { x0, y2 }, { x1, y3 }, { u0, v2 }, { u1, v3 }, col);
    imgui->addImage(dl, tid, { x1, y2 }, { x2, y3 }, { u1, v2 }, { u2, v3 }, col);
    imgui->addImage(dl, tid, { x2, y2 }, { x3, y3 }, { u2, v2 }, { u3, v3 }, col);
}

// Stores raw RGBA icon pixels under key and registers the ImGui texture handle for drawing.
void GraphCanvasWidget::setIconPixels(const std::string& key, int w, int h, const uint8_t* rgba, size_t len)
{
    size_t requiredBytes = 0;
    if (key.empty() || !rgba || !checkedRgbaByteCount(w, h, requiredBytes) || len < requiredBytes)
        return;

    auto provider = std::make_shared<omni::ui::ByteImageProvider>();
    provider->setBytesData(rgba, { static_cast<uint32_t>(w), static_cast<uint32_t>(h) });
    m_iconProviders[key] = provider;
    m_iconTextures[key] = provider->getImGuiReference();
}

// Registers an icon from a file path (SVG or raster); skips if key already has a
// provider. Prepares a 64x64 draw target; updateIconProviders resolves ImGui refs when ready.
void GraphCanvasWidget::setIconPath(const std::string& key, const std::string& path)
{
    if (key.empty() || path.empty())
        return;
    if (m_iconProviders.count(key))
        return;


    bool isSvg = (path.size() >= 4 &&
                  (path.compare(path.size() - 4, 4, ".svg") == 0 || path.compare(path.size() - 4, 4, ".SVG") == 0));

    std::shared_ptr<omni::ui::ImageProvider> provider;
    if (isSvg)
    {
        auto vp = std::make_shared<omni::ui::VectorImageProvider>(path);
        vp->prepareDraw(64.0f, 64.0f);
        provider = vp;
    }
    else
    {
        auto rp = std::make_shared<omni::ui::RasterImageProvider>(path);
        rp->prepareDraw(64.0f, 64.0f);
        provider = rp;
    }
    m_iconProviders[key] = provider;
}

// For each icon provider without a valid texture yet, re-runs prepareDraw and caches
// the ImGui reference once the image data is available (async decode paths).
void GraphCanvasWidget::updateIconProviders()
{
    for (auto& [key, provider] : m_iconProviders)
    {
        if (m_iconTextures.count(key) && m_iconTextures[key] != nullptr)
            continue;

        provider->prepareDraw(64.0f, 64.0f);
        if (provider->isReferenceValid())
        {
            m_iconTextures[key] = provider->getImGuiReference();
        }
    }
}

// Returns the cached ImGui texture pointer for key, or null if not loaded.
void* GraphCanvasWidget::getIconTexture(const std::string& key) const
{
    auto it = m_iconTextures.find(key);
    return (it != m_iconTextures.end()) ? it->second : nullptr;
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

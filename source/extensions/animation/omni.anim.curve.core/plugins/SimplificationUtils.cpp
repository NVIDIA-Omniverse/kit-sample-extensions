// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include "SimplificationUtils.h"

#include <carb/logging/Log.h>
#include <carb/profiler/Profile.h>

namespace omni
{
namespace anim
{

using namespace PXR_NS;

float tj(float ti, const GfVec2f& P0, const GfVec2f& P1, float alpha)
{
    GfVec2f d = P1 - P0;
    float a = GfDot(d, d);
    float b = std::pow(a, alpha * 0.5f);
    return ti + b;
}

GfVec2f catmullRom(const GfVec2f& P0, const GfVec2f& P1, const GfVec2f& P2, const GfVec2f& P3, float t, float alpha = 0.5f)
{
    float t0 = 0.0f;
    float t1 = tj(t0, P0, P1, alpha);
    float t2 = tj(t1, P1, P2, alpha);
    float t3 = tj(t2, P2, P3, alpha);
    t = GfLerp(t, t1, t2);

    GfVec2f A1 = P0 * ((t1 - t) / (t1 - t0)) + P1 * ((t - t0) / (t1 - t0));
    GfVec2f A2 = P1 * ((t2 - t) / (t2 - t1)) + P2 * ((t - t1) / (t2 - t1));
    GfVec2f A3 = P2 * (t3 - t) / (t3 - t2) + P3 * (t - t2) / (t3 - t2);
    GfVec2f B1 = A1 * (t2 - t) / (t2 - t0) + A2 * (t - t0) / (t2 - t0);
    GfVec2f B2 = A2 * (t3 - t) / (t3 - t1) + A3 * (t - t1) / (t3 - t1);
    return B1 * (t2 - t) / (t2 - t1) + B2 * (t - t1) / (t2 - t1);
}

bool catmullRomFindX(GfVec2f& pOut,
                     const GfVec2f& P0,
                     const GfVec2f& P1,
                     const GfVec2f& P2,
                     const GfVec2f& P3,
                     float x,
                     float x0,
                     float x1,
                     float alpha = 0.5f)
{
    float targetError = 0.01f;

    float t = (x - x0) / (x1 - x0);
    GfVec2f p = catmullRom(P0, P1, P2, P3, t, alpha);
    float px = p[0];
    float t0 = 0, t1 = 1;
    constexpr int MaxIterations = 20;
    int i = 0;
    // Find curve parameter t for which CatmullRom(t).x is close to x, with binary search
    while (std::abs(x - px) > targetError and i < MaxIterations)
    {
        if (px > x)
        {
            t1 = t;
            t = t0 + (t - t0) * 0.5f;
        }
        else
        {
            t0 = t;
            t = t + (t1 - t) * 0.5f;
        }
        p = catmullRom(P0, P1, P2, P3, t, alpha);
        px = p[0];
        i = i + 1;
    }

    pOut = p;
    return i != MaxIterations;
}

float getRange(const std::vector<float>& values)
{
    if (values.empty())
    {
        return 0;
    }

    float vmin, vmax;
    vmin = std::numeric_limits<float>::infinity();
    vmax = -std::numeric_limits<float>::infinity();
    for (float v : values)
    {
        vmin = std::min(vmin, v);
        vmax = std::max(vmax, v);
    }
    return vmax - vmin;
}

std::vector<std::pair<float, float>> simplifyCatmull(const std::vector<float>& keys,
                                                     const std::vector<float>& values,
                                                     float valueRangeEps,
                                                     float maxErrorRatio)
{
    CARB_PROFILE_ZONE(1, "omni::anim::simplifyCatmull");

    constexpr bool optimized = true; // until we find failure cases
    std::vector<std::pair<float, float>> result;
    if (keys.size() != values.size())
    {
        CARB_LOG_ERROR("simplifyCatmull: sizes of keys and values do not match");
        return result;
    }

    if (keys.size() < 5)
    {
        result.reserve(keys.size());
        for (size_t i = 0; i < keys.size(); ++i)
        {
            result.push_back({ keys[i], values[i] });
        }
        return result;
    }

    float valueRange = getRange(values);
    if (valueRange < valueRangeEps)
    {
        result.push_back({ keys.front(), values.front() });
        result.push_back({ keys.back(), values.back() });
        return result;
    }
    float maxError = valueRange * maxErrorRatio;

    float minError = 0;
    std::vector<std::pair<size_t, float>> fitErrors(keys.size());
    std::set<size_t> remainingKeys;
    for (size_t i = 0; i < keys.size(); ++i)
    {
        remainingKeys.insert(i);
    }
    while (remainingKeys.size() >= 5 && minError < maxError)
    {
        minError = std::numeric_limits<float>::infinity();
        size_t minIndex = 2;
        size_t errorCount = 0;
        for (auto indexIt = std::next(remainingKeys.begin()); indexIt != std::prev(remainingKeys.end()); ++indexIt)
        {
            size_t im1 = *std::prev(indexIt);
            size_t i = *indexIt;
            size_t ip1 = *std::next(indexIt);
            GfVec2f P1(keys[im1], values[im1]);
            GfVec2f P2(keys[ip1], values[ip1]);
            GfVec2f P0(0, 0);
            if (indexIt == std::next(remainingKeys.begin()))
            {
                P0 = P1 + (P1 - P2);
            }
            else
            {
                size_t im2 = *std::prev(std::prev(indexIt));
                P0 = GfVec2f(keys[im2], values[im2]);
            }
            GfVec2f P3(0, 0);
            if (std::next(std::next(indexIt)) == remainingKeys.end())
            {
                P3 = P2 + (P2 - P1);
            }
            else
            {
                size_t ip2 = *std::next(std::next(indexIt));
                P3 = GfVec2f(keys[ip2], values[ip2]);
            }

            GfVec2f vInterp;
            bool success = catmullRomFindX(vInterp, P0, P1, P2, P3, keys[i], keys[ip1], keys[im1]);
            if (!success)
            {
                continue;
            }

            float error = std::abs(values[i] - vInterp[1]);
            if (error < minError)
            {
                minError = error;
                minIndex = i;
                fitErrors[errorCount] = { i, error };
                ++errorCount;
            }
        }
        if (errorCount == 0)
        {
            break;
        }
        if (optimized)
        {
            std::sort(fitErrors.begin(), fitErrors.begin() + errorCount,
                      [](const auto& a, const auto& b) -> bool { return a.second < b.second; });
            for (size_t i = 0; i < errorCount; ++i)
            {
                if (fitErrors[i].second > maxError)
                {
                    break;
                }
                remainingKeys.erase(fitErrors[i].first);
            }
        }
        else
        {
            remainingKeys.erase(minIndex);
        }
    }

    result.reserve(remainingKeys.size());
    for (size_t i : remainingKeys)
    {
        result.push_back({ keys[i], values[i] });
    }

    return result;
}

} // namespace anim
} // namespace omni

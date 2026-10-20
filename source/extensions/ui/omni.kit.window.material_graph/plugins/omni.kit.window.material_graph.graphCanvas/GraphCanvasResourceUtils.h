// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <cstddef>
#include <limits>

namespace omni
{
namespace kit
{
namespace materialGraph
{

inline bool checkedRgbaByteCount(int width, int height, size_t& byteCount) noexcept
{
    byteCount = 0;
    if (width <= 0 || height <= 0)
        return false;

    constexpr size_t kChannels = 4;
    const size_t unsignedWidth = static_cast<size_t>(width);
    const size_t unsignedHeight = static_cast<size_t>(height);
    const size_t maximum = std::numeric_limits<size_t>::max();
    if (unsignedWidth > maximum / unsignedHeight)
        return false;

    const size_t pixelCount = unsignedWidth * unsignedHeight;
    if (pixelCount > maximum / kChannels)
        return false;

    byteCount = pixelCount * kChannels;
    return true;
}

} // namespace materialGraph
} // namespace kit
} // namespace omni

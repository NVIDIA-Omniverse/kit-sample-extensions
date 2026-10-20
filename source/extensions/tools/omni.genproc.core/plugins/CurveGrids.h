// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>

#include <stdint.h>

namespace omni
{
namespace genproc
{

using omni::math::linalg::matrix3f;
using omni::math::linalg::vec3f;

inline size_t gridQuadCount(size_t rowPointCount, size_t colPointCount, bool rowWrap, bool colWrap)
{
    return (rowPointCount - size_t(!rowWrap)) * (colPointCount - size_t(!colWrap));
}

inline size_t gridPointCount(size_t rowPointCount, size_t colPointCount)
{
    return rowPointCount * colPointCount;
}

void gridVertexIndices(size_t rowPointCount, size_t colPointCount, bool rowWrap, bool colWrap, int startIndex, int* indices);

void curveGridPoints(size_t curvePointCount,
                     const vec3f* curvePoints,
                     const vec3f* tangents,
                     const vec3f* ups,
                     const vec3f* outs,
                     const bool hasScalePerPoint,
                     const float* scales,
                     const float* curveOpacities,
                     const matrix3f* stretches,
                     size_t sectionPointCount,
                     const vec3f* sectionPoints,
                     vec3f* gridPoints,
                     float* gridOpacities);

}
}

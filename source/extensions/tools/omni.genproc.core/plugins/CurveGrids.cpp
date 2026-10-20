// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "CurveGrids.h"

#include <omni/math/linalg/vec.h>

#include <stdint.h>

namespace omni
{
namespace genproc
{

void gridVertexIndices(size_t rowPointCount, size_t colPointCount, bool rowWrap, bool colWrap, int startIndex, int* indices)
{
    int rowStartIndex = startIndex;
    for (size_t row = 0; row < rowPointCount - 1; ++row)
    {
        for (size_t col = 0; col < colPointCount - 1; ++col)
        {
            indices[0] = rowStartIndex + int(col);
            indices[1] = rowStartIndex + int(col + 1);
            indices[2] = rowStartIndex + int(col + 1 + colPointCount);
            indices[3] = rowStartIndex + int(col + colPointCount);
            indices += 4;
        }

        if (colWrap)
        {
            indices[0] = rowStartIndex + int(colPointCount - 1);
            indices[1] = rowStartIndex;
            indices[2] = rowStartIndex + int(colPointCount);
            indices[3] = rowStartIndex + int(2 * colPointCount - 1);
            indices += 4;
        }

        rowStartIndex += int(colPointCount);
    }

    if (rowWrap)
    {
        for (size_t col = 0; col < colPointCount - 1; ++col)
        {
            indices[0] = rowStartIndex + int(col);
            indices[1] = rowStartIndex + int(col + 1);
            indices[2] = int(col + 1);
            indices[3] = int(col);
            indices += 4;
        }

        if (colWrap)
        {
            indices[0] = rowStartIndex + int(colPointCount - 1);
            indices[1] = rowStartIndex;
            indices[2] = 0;
            indices[3] = int(colPointCount - 1);
            indices += 4;
        }
    }
}

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
                     float* gridOpacities)
{
    for (size_t row = 0, i = 0; row < curvePointCount; ++row)
    {
        const float scale = scales ? scales[hasScalePerPoint ? row : 0] : 1.0f;
        const vec3f curvePoint = curvePoints[row];
        vec3f up = scale * ups[row];
        vec3f tangent = scale * tangents[row];
        vec3f out = scale * outs[row];
        if (stretches)
        {
            // The stretches are in output space, not cross section space, so they
            // need to act like a post-transform below.  These multiplies here, though,
            // work in either order, since stretches should be symmetric.
            up = up * stretches[row];
            tangent = tangent * stretches[row];
            out = out * stretches[row];
        }

        // Transform the cross section's points into this curve point's space.
        for (size_t col = 0; col < sectionPointCount; ++col, ++i)
        {
            const vec3f& sectionPoint = sectionPoints[col];
            gridPoints[i] = curvePoint + (sectionPoint[0] * out) + (sectionPoint[1] * up) + (sectionPoint[2] * tangent);
            if (curveOpacities != nullptr && gridOpacities != nullptr)
            {
                gridOpacities[i] = curveOpacities[row];
            }
        }
    }
}

}
}

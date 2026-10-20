// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.


#pragma once

#include <omni/math/linalg/vec.h>

#include <numeric>
#include <vector>

using namespace omni::math::linalg;

// Based on G. Barequet and M. Sharir, Filling gaps in the boundary of a polyhedron, Computer-Aided Geometric Design
// (CAGD), 12 (2), 207-229, March 1995. It finds the triangulation of the single polygon which minimizes the total sum
// of weight function defined on all triangles. It does not handle the case referred as "hole", "inner polygon" and
// "multiple polygon". Eurographics Symposium on Geometry Processing (SGP) 2013, Computer Graphics Forum, Ming Zou, Tao
// Ju, Nathan Carr provides a generic solution for multiple polygons.
inline void triangulateTrace(uint32_t i,
                             uint32_t k,
                             std::vector<uint32_t>& triIndices,
                             const std::vector<std::vector<uint32_t>>& wIndices)
{
    if (i + 2 == k)
    {
        triIndices.push_back(i);
        triIndices.push_back(i + 1);
        triIndices.push_back(k);
    }
    else
    {
        uint32_t index = wIndices[i][k];
        if (index != i + 1)
        {
            triangulateTrace(i, index, triIndices, wIndices);
        }
        triIndices.push_back(i);
        triIndices.push_back(index);
        triIndices.push_back(k);
        if (index + 1 != k)
        {
            triangulateTrace(index, k, triIndices, wIndices);
        }
    }
}

template <class DataType, class WeightFunction>
std::vector<uint32_t> triangulatePolygon(const vec3<DataType>* verts, const uint32_t n, WeightFunction f)
{
    std::vector<uint32_t> result;
    // Corner case
    if (n <= 3)
    {
        result.resize(n);
        std::iota(result.begin(), result.end(), 0);
        return result;
    }
    // Estimation of how many triangles a vertex is involved in.
    result.reserve(3 * n);

    // Initialize weights and indices
    std::vector<std::vector<DataType>> weights(n);
    std::vector<std::vector<uint32_t>> indices(n);
    for (uint32_t i = 0; i < n; ++i)
    {
        weights[i].resize(n, DataType(0));
        indices[i].resize(n, 0);
    }
    for (uint32_t i = 0; i <= n - 3; ++i)
    {
        weights[i][i + 2] = f(verts[i], verts[i + 1], verts[i + 2]);
    }
    for (uint32_t j = 3; j <= n - 1; ++j)
    {
        for (uint32_t i = 0; i <= n - j - 1; ++i)
        {
            const uint32_t k = i + j;
            uint32_t m = i + 1;
            weights[i][k] = weights[i][m] + weights[m][k] + f(verts[i], verts[m], verts[k]);
            indices[i][k] = m;
            for (m = i + 2; m < k; ++m)
            {
                DataType w = weights[i][m] + weights[m][k] + f(verts[i], verts[m], verts[k]);
                if (w < weights[i][k])
                {
                    weights[i][k] = w;
                    indices[i][k] = m;
                }
            }
        }
    }

    triangulateTrace(0, n - 1, result, indices);
    return result;
}

template <class DataType>
struct TriangleAreaWeightFunction
{
    using vecType = vec3<DataType>;
    DataType operator()(const vecType& v0, const vecType& v1, const vecType& v2)
    {
        return DataType(0.5) * GfCross(v1 - v0, v2 - v0).GetLength();
    }
};

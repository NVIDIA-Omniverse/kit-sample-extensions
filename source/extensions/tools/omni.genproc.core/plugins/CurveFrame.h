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
using omni::math::linalg::vec3;
using omni::math::linalg::vec3f;

// Fills tangents with tangents computed from the sequence of points.
void curveFrameTangents(size_t pointCount,
                        const vec3f* points,
                        const bool wrap,
                        vec3f* tangents,
                        matrix3f* stretches = nullptr,
                        const float maxScale = 10.0f);

template <typename T>
vec3<T> arbitraryPerpendicular(const vec3<T> v)
{
    size_t minAxis = (fabs(v[1]) < fabs(v[0])) ? 1 : 0;
    minAxis = (fabs(v[2]) < fabs(v[minAxis])) ? 2 : minAxis;
    vec3<T> output(0, 0, 0);
    output[minAxis] = 1;
    return output.GetComplement(v).GetNormalized();
}

template <typename T>
vec3<T> reflectThrough(const vec3<T>& v, const vec3<T>& unitVector)
{
    const vec3<T> projection = v.GetProjection(unitVector);
    const vec3<T> complement = v - projection;
    return projection - complement;
}

template <typename T>
vec3<T> rotateSameAs(const vec3<T>& v, const vec3<T>& from, const vec3<T>& to)
{
    const vec3<T> reflected = reflectThrough(v, from);
    return reflectThrough(reflected, vec3<T>((from + to).GetNormalized()));
}

// Fills ups with up vectors computed from the sequence of points and tangents,
// starting with the vector closest to firstUp that is perpendicular to tangents[0].
// NOTE: tangents *must* be unit vectors.
// TODO: Handle wrapping by spreading out the final twist.
template <typename T>
void curveFrameUps(size_t pointCount, const vec3<T>* tangents, const vec3<T>& firstUp, vec3<T>* ups, bool propagateUp = true)
{
    if (pointCount == 0)
        return;

    vec3<T> up;
    for (size_t i = 0; i < pointCount; ++i)
    {
        // Compute first up vector (or all up vectors if propagateUp is false)
        if (1.f - abs(tangents[i].Dot(firstUp)) < 1e-6f)
        {
            // use firstUp rather than tangents[i], because in the expected use cases firstUp is likely a constant
            // e.g. given by the scene's up axis, whereas small perturbations in tangents[i] can lead to different
            // perpendicular vectors
            up = arbitraryPerpendicular(firstUp);
        }
        else
        {
            up = firstUp.GetComplement(tangents[i]).GetNormalized();
        }

        ups[i] = up;

        if (propagateUp)
            break;
    }

    if (propagateUp)
    {
        for (size_t i = 1; i < pointCount; ++i)
        {
            // Apply the minimum rotation that takes the previous tangent to the current tangent.
            up = rotateSameAs(up, tangents[i - 1], tangents[i]);
            ups[i] = up;
        }
    }
}

template <typename T>
void curveFrameOuts(size_t pointCount, const vec3<T>* tangents, const vec3<T>* ups, vec3<T>* outs)
{
    for (size_t i = 0; i < pointCount; ++i)
    {
        outs[i] = omni::math::linalg::GfCross(ups[i], tangents[i]);
    }
}

void pointsToCurveCaptureCoords(size_t curvePointCount,
                                const vec3f* curvePoints,
                                const vec3f* tangents,
                                const vec3f* ups,
                                const vec3f* outs,
                                size_t pointsToCaptureCount,
                                const vec3f* pointsToCapture,
                                vec3f* captureCoords);

void curveCaptureCoordsToPoints(size_t curvePointCount,
                                const vec3f* curvePoints,
                                const vec3f* tangents,
                                const vec3f* ups,
                                const vec3f* outs,
                                size_t captureCoordCount,
                                const vec3f* captureCoords,
                                vec3f* outputPoints);

}
}

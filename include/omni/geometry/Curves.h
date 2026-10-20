// SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <carb/Defines.h>

#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>

#include <vector>

#ifndef __CUDACC__
#    define CUDA_SAFE_ASSERT(cond, ...) CARB_ASSERT(cond, ##__VA_ARGS__)
#    define CUDA_CALLABLE
#else
#    define CUDA_SAFE_ASSERT(cond, ...)
#    define CUDA_CALLABLE __device__ __host__
#endif

namespace omni
{
namespace geometry
{
namespace curves
{

using omni::math::linalg::matrix4f;
using omni::math::linalg::vec4f;

enum class eBasisCurveType
{
    Bezier = 0,
    CatmullRom = 1,
    BSpline = 2
};

enum class eBasisCurveWrap
{
    Periodic = 0,
    NonPeriodic = 1,
    Pinned = 2
};

inline CUDA_CALLABLE const matrix4f& getBasis(eBasisCurveType type);
inline CUDA_CALLABLE const matrix4f& getTangentBasis(eBasisCurveType type);

// Wrapper class for cubic spline based curves
class SplineCurve
{
public:
    CUDA_CALLABLE SplineCurve(eBasisCurveWrap wrapMode,
                              uint32_t vstep,
                              const matrix4f* basis,
                              const matrix4f* tangentBasis = nullptr)
        : m_wrapMode(wrapMode), m_vstep(vstep), m_basis(basis), m_tangentBasis(tangentBasis)
    {
    }
    // NOTE: Bezier curves don't need any special handling for pinned ends,
    //       since each segment is completely independent, hence the skipping by 3, instead of 1.
    CUDA_CALLABLE SplineCurve(eBasisCurveWrap wrapMode, eBasisCurveType type)
        : m_wrapMode((type == eBasisCurveType::Bezier && wrapMode == eBasisCurveWrap::Pinned) ?
                         eBasisCurveWrap::NonPeriodic :
                         wrapMode),
          m_vstep((type == eBasisCurveType::Bezier) ? 3 : 1),
          m_basis(&getBasis(type)),
          m_tangentBasis(&getTangentBasis(type))
    {
    }

    CUDA_CALLABLE size_t getSegmentCount(const size_t controlPointCount) const
    {
        if (controlPointCount < 2)
        {
            return 0;
        }
        if (controlPointCount == 2)
        {
            return 1;
        }

        // FIXME: Handle controlPointCount being 3!
        CUDA_SAFE_ASSERT(controlPointCount != 3);

        size_t segmentCount = 0;
        switch (m_wrapMode)
        {
        case eBasisCurveWrap::Periodic:
            if (m_vstep == 1)
            {
                segmentCount = controlPointCount;
            }
            else
            {
                // sometimes the CV count can be m_vstep * segmentCount or  m_vstep * segment + 1 to indicate peridoic
                // for USD it is m_vstep * segmentCount. In either case, segmentCount = controlPointCount / m_vstep
                // works
                segmentCount = controlPointCount / m_vstep;
            }
            break;
        case eBasisCurveWrap::NonPeriodic:
            segmentCount = (controlPointCount - 4) / m_vstep + 1;
            break;
        case eBasisCurveWrap::Pinned:
            // 2 more than non-periodic for pinned segments
            segmentCount = (controlPointCount - 4) / m_vstep + 3;
            break;
        }
        return segmentCount;
    }

    CUDA_CALLABLE size_t getTessellationPointCount(const size_t controlPointCount,
                                                   const size_t stepsPerSegment,
                                                   bool includeSegmentFinalSamples = false) const
    {
        if (controlPointCount < 3)
        {
            if (controlPointCount <= 1)
                return controlPointCount;

            // TODO: Should this subsample?
            return 2;
        }
        if (m_wrapMode == eBasisCurveWrap::Periodic)
        {
            // Some systems store a redundant duplicate of the first point at the end
            // of a cubic Bezier, so allow a modulus of 1 in that case.
            CUDA_SAFE_ASSERT(controlPointCount % m_vstep == 0 || (m_vstep == 3 && controlPointCount % m_vstep == 1));
            CUDA_SAFE_ASSERT(m_vstep >= 1 && m_vstep <= 3);
            return (controlPointCount / m_vstep) * (stepsPerSegment + size_t(includeSegmentFinalSamples));
        }
        // FIXME: Handle controlPointCount being 3!
        CUDA_SAFE_ASSERT(controlPointCount != 3);
        if (controlPointCount == 3)
            return 0;
        const size_t centralSegmentCount = (controlPointCount - 4) / m_vstep + 1;
        // NOTE: Bezier curves use NonPeriodic in place of Pinned
        size_t segmentCount = centralSegmentCount + ((m_wrapMode == eBasisCurveWrap::Pinned) ? 2 : 0);
        size_t pointCount = segmentCount * (stepsPerSegment + size_t(includeSegmentFinalSamples));
        // Add the final point if it wasn't already included
        if (!includeSegmentFinalSamples)
            ++pointCount;
        return pointCount;
    }

    /// tessellate curve with a fixed number of samples per segment
    ///
    /// \param controlPoints:
    ///         control points of the curve
    /// \param controlPointCount
    ///         number of control points
    /// \param tessellatedPoints
    ///         collection to which tessellated points will be appended
    /// \param stepsPerSegment
    ///         number of tessellated points that will be produced per segment
    /// \param includeSegmentFinalSamples
    ///         If true, endpoints of segments will be sampled for tessellation,
    ///         resulting in stepsPerSegment+1 points per segment.
    ///         If false, only the final segment's endpoint is sampled
    ///         (i.e. the end of the curve).
    /// \param tessellatedTangents
    ///         If a pointer is provided, tangents corresponding to the
    ///         tessellated points will be appended to this collection
    template <typename T>
    void tessellate(const T* controlPoints,
                    const size_t controlPointCount,
                    std::vector<T>& tessellatedPoints,
                    const size_t stepsPerSegment,
                    bool includeSegmentFinalSamples = false,
                    std::vector<T>* tessellatedTangents = nullptr) const
    {
        size_t tessellatedPointCount =
            getTessellationPointCount(controlPointCount, stepsPerSegment, includeSegmentFinalSamples);
        tessellatedPoints.resize(tessellatedPointCount);
        if (tessellatedTangents)
            tessellatedTangents->resize(tessellatedPointCount);
        tessellate(controlPoints, controlPointCount, tessellatedPoints.data(), stepsPerSegment,
                   includeSegmentFinalSamples, tessellatedTangents ? tessellatedTangents->data() : nullptr);
    }

    // NOTE: Use getTessellationPointCount to allocate tessellatedPoints and (if needed) tessellatedTangents.
    template <typename T>
    CUDA_CALLABLE void tessellate(const T* controlPoints,
                                  const size_t controlPointCount,
                                  T* tessellatedPoints,
                                  const size_t stepsPerSegment,
                                  bool includeSegmentFinalSamples = false,
                                  T* tessellatedTangents = nullptr) const
    {
        // Small edge cases
        if (controlPointCount < 3)
        {
            if (controlPointCount == 0)
                return;
            T p0 = controlPoints[0];
            tessellatedPoints[0] = p0;
            if (controlPointCount == 2)
            {
                // Straight line
                // TODO: Should this subsample?
                T p1 = controlPoints[1];
                T t = p1 - p0;
                tessellatedPoints[1] = p1;
                if (tessellatedTangents != nullptr)
                {
                    tessellatedTangents[0] = t;
                    tessellatedTangents[1] = t;
                }
            }
            else
            {
                if (tessellatedTangents != nullptr)
                {
                    // Single point, so arbitrarily pick zero tangent
                    tessellatedTangents[0] = T(0);
                }
            }
            return;
        }

        const size_t outputPointsPerSegment = stepsPerSegment + size_t(includeSegmentFinalSamples);

        if (m_wrapMode == eBasisCurveWrap::Periodic)
        {
            // Periodic, so all segments are the same basis, apart from wrapping indices.
            // Some systems store a redundant duplicate of the first point at the end
            // of a cubic Bezier, so allow a modulus of 1 in that case.
            CUDA_SAFE_ASSERT(controlPointCount % m_vstep == 0 || (m_vstep == 3 && controlPointCount % m_vstep == 1));
            // This should work for step size 2 (e.g. pos,tan,pos,tan) or 3 (pos,tan,tan,pos)
            // though for 3, the only thing that wraps is the last position, not its tangent.
            CUDA_SAFE_ASSERT(m_vstep >= 1 && m_vstep <= 3);
            if (m_vstep == 1)
            {
                // Start first segment with point 0 at index 1, instead of index 0.
                tessellateSegment(controlPoints, controlPointCount, tessellatedPoints, tessellatedTangents,
                                  controlPointCount - 1, stepsPerSegment, includeSegmentFinalSamples);
                tessellatedPoints += outputPointsPerSegment;
                if (tessellatedTangents)
                    tessellatedTangents += outputPointsPerSegment;
            }
            for (size_t controlPointIndex = 0; controlPointIndex < controlPointCount - 1; controlPointIndex += m_vstep)
            {
                tessellateSegment(controlPoints, controlPointCount, tessellatedPoints, tessellatedTangents,
                                  controlPointIndex, stepsPerSegment, includeSegmentFinalSamples);
                tessellatedPoints += outputPointsPerSegment;
                if (tessellatedTangents)
                    tessellatedTangents += outputPointsPerSegment;
            }
        }
        else
        {
            // FIXME: Handle controlPointCount being 3!
            CUDA_SAFE_ASSERT(controlPointCount != 3);
            if (controlPointCount == 3)
                return;

            if (m_wrapMode == eBasisCurveWrap::Pinned)
            {
                tessellateEndSegment(controlPoints, controlPointCount, tessellatedPoints, tessellatedTangents, 0,
                                     stepsPerSegment, includeSegmentFinalSamples);
                tessellatedPoints += outputPointsPerSegment;
                if (tessellatedTangents)
                    tessellatedTangents += outputPointsPerSegment;
            }

            const size_t centralSegmentCount = (controlPointCount - 4) / m_vstep + 1;
            const bool includeCentralFinalSample = (m_wrapMode == eBasisCurveWrap::NonPeriodic);
            size_t controlPointIndex = 0;
            for (size_t i = 0; i < centralSegmentCount; ++i)
            {
                const bool includeFinalSample =
                    includeSegmentFinalSamples || ((i == centralSegmentCount - 1) && includeCentralFinalSample);
                tessellateSegment(controlPoints, controlPointCount, tessellatedPoints, tessellatedTangents,
                                  controlPointIndex, stepsPerSegment, includeFinalSample);
                controlPointIndex += m_vstep;
                tessellatedPoints += outputPointsPerSegment;
                if (tessellatedTangents)
                    tessellatedTangents += outputPointsPerSegment;
            }

            if (m_wrapMode == eBasisCurveWrap::Pinned)
            {
                tessellateEndSegment(controlPoints, controlPointCount, tessellatedPoints, tessellatedTangents,
                                     controlPointCount, stepsPerSegment, true);
            }
        }
    }

    /// tessellate curve at prescribed parametric values
    ///
    /// \param controlPoints:
    ///         control points of the curve
    /// \param controlPointCount
    ///         number of control points
    /// \param tessellatedPoints
    ///         collection to be filled with tessellated points
    /// \param tSamples
    ///         parametric sample locations. These samples must
    ///         be in the range [0, segmentCount).
    ///         The floor of a sample is used to specify the segment,
    ///         and the fractional part of a sample is used to specify
    ///         the sample value within the segment.
    /// \param tessellatedTangents
    ///         If a pointer is provided, the collection will be filled
    ///         with tangents corresponding to the tessellated points
    template <typename T>
    void tessellate(const T* controlPoints,
                    const size_t controlPointCount,
                    std::vector<T>& tessellatedPoints,
                    const std::vector<float>& tSamples,
                    std::vector<T>* tessellatedTangents = nullptr) const
    {
        tessellatedPoints.resize(tSamples.size());
        if (tessellatedTangents != nullptr)
        {
            tessellatedTangents->resize(tSamples.size());
        }

        tessellate(controlPoints, controlPointCount, tSamples.data(), tSamples.size(), tessellatedPoints.data(),
                   tessellatedTangents ? tessellatedTangents->data() : nullptr);
    }

    template <typename T>
    CUDA_CALLABLE void tessellate(const T* controlPoints,
                                  const size_t controlPointCount,
                                  const float* tSamples,
                                  const size_t tSampleCount,
                                  T* tessellatedPoints,
                                  T* tessellatedTangents = nullptr) const
    {
        // TODO: handle controlPointCount <= 3?
        CUDA_SAFE_ASSERT(controlPointCount > 3);

        if (m_wrapMode == eBasisCurveWrap::Periodic)
        {
            // Periodic, so all segments are the same basis, apart from wrapping indices.
            // Some systems store a redundant duplicate of the first point at the end
            // of a cubic Bezier, so allow a modulus of 1 in that case.
            CUDA_SAFE_ASSERT(controlPointCount % m_vstep == 0 || (m_vstep == 3 && controlPointCount % m_vstep == 1));
            // This should work for step size 2 (e.g. pos,tan,pos,tan) or 3 (pos,tan,tan,pos)
            // though for 3, the only thing that wraps is the last position, not its tangent.
            CUDA_SAFE_ASSERT(m_vstep >= 1 && m_vstep <= 3);
        }

        const size_t segmentCount = getSegmentCount(controlPointCount);

        size_t index[4];
        T p[4];
        size_t currentSegment = 0;

        for (size_t i = 0; i < tSampleCount; i++)
        {
            const float& t = tSamples[i];
            const size_t sampleSegment = (size_t(t) >= segmentCount ? segmentCount - 1 : size_t(t));
            if (sampleSegment != currentSegment || i == 0)
            {
                // need to change which segment we're using
                currentSegment = sampleSegment;

                CUDA_SAFE_ASSERT(currentSegment < segmentCount);

                switch (m_wrapMode)
                {
                case eBasisCurveWrap::Periodic:
                    if (m_vstep == 1)
                    {
                        if (currentSegment == 0)
                        {
                            index[0] = controlPointCount - 1;
                        }
                        else
                        {
                            index[0] = (currentSegment - 1);
                        }
                        CUDA_SAFE_ASSERT(index[0] < controlPointCount - 1);
                    }
                    else
                    {
                        index[0] = currentSegment * m_vstep;
                        CUDA_SAFE_ASSERT(index[0] < controlPointCount - 1);
                    }
                    // wrap around as needed
                    index[1] = (index[0] + 1 < controlPointCount) ? (index[0] + 1) : 0;
                    index[2] = (index[1] + 1 < controlPointCount) ? (index[1] + 1) : 0;
                    index[3] = (index[2] + 1 < controlPointCount) ? (index[2] + 1) : 0;
                    p[0] = controlPoints[index[0]];
                    p[1] = controlPoints[index[1]];
                    p[2] = controlPoints[index[2]];
                    p[3] = controlPoints[index[3]];
                    break;
                case eBasisCurveWrap::NonPeriodic:
                    index[0] = currentSegment * m_vstep;
                    index[1] = index[0] + 1;
                    index[2] = index[1] + 1;
                    index[3] = index[2] + 1;
                    CUDA_SAFE_ASSERT(index[3] < controlPointCount);
                    p[0] = controlPoints[index[0]];
                    p[1] = controlPoints[index[1]];
                    p[2] = controlPoints[index[2]];
                    p[3] = controlPoints[index[3]];
                    break;
                case eBasisCurveWrap::Pinned:
                    if (currentSegment == 0)
                    {
                        index[1] = 0;
                        index[2] = 1;
                        index[3] = 2;

                        p[1] = controlPoints[index[1]];
                        p[2] = controlPoints[index[2]];
                        p[3] = controlPoints[index[3]];
                        p[0] = 2 * p[1] - p[2];
                    }
                    else if (currentSegment == segmentCount - 1)
                    {
                        index[0] = controlPointCount - 3;
                        index[1] = controlPointCount - 2;
                        index[2] = controlPointCount - 1;

                        p[0] = controlPoints[index[0]];
                        p[1] = controlPoints[index[1]];
                        p[2] = controlPoints[index[2]];
                        p[3] = 2 * p[2] - p[1];
                    }
                    else
                    {
                        index[0] = (currentSegment - 1) * m_vstep;
                        index[1] = index[0] + 1;
                        index[2] = index[1] + 1;
                        index[3] = index[2] + 1;
                        CUDA_SAFE_ASSERT(index[3] < controlPointCount);
                        p[0] = controlPoints[index[0]];
                        p[1] = controlPoints[index[1]];
                        p[2] = controlPoints[index[2]];
                        p[3] = controlPoints[index[3]];
                    }
                    break;
                default:
                    CUDA_SAFE_ASSERT(false);
                }
            }

            const float u = t - float(currentSegment);
            const vec4f v(1.f, u, u * u, u * u * u);
            const vec4f coeffs = (*m_basis) * v;
            tessellatedPoints[i] = p[0] * coeffs[0] + p[1] * coeffs[1] + p[2] * coeffs[2] + p[3] * coeffs[3];
            if (tessellatedTangents != nullptr)
            {
                const vec4f tangentCoeffs = (*m_tangentBasis) * v;
                tessellatedTangents[i] = p[0] * tangentCoeffs[0] + p[1] * tangentCoeffs[1] + p[2] * tangentCoeffs[2] +
                                         p[3] * tangentCoeffs[3];
            }
        }
    }

    template <typename T>
    CUDA_CALLABLE void tessellateSegment(const T* controlPoints,
                                         const size_t controlPointCount,
                                         T* tessellatedPoints,
                                         T* tessellatedTangents,
                                         size_t index,
                                         const size_t stepsPerSegment,
                                         bool includeFinalSample,
                                         const float startT = 0.f,
                                         const float endT = 1.f) const
    {
        // Wrap around as needed, for periodic case.
        const size_t index1 = (index + 1 < controlPointCount) ? (index + 1) : 0;
        const size_t index2 = (index1 + 1 < controlPointCount) ? (index1 + 1) : 0;
        const size_t index3 = (index2 + 1 < controlPointCount) ? (index2 + 1) : 0;

        tessellateSegment(controlPoints[index], controlPoints[index1], controlPoints[index2], controlPoints[index3],
                          tessellatedPoints, tessellatedTangents, stepsPerSegment, includeFinalSample, startT, endT);
    }

    template <typename T>
    CUDA_CALLABLE T evaluateSegment(const T* controlPoints,
                                    const size_t controlPointCount,
                                    const size_t index,
                                    float u,
                                    int order = 0,
                                    T* tangent = nullptr) const
    {
        // NOTE that index is the starting control point index, *not* the segment index.

        // Wrap around as needed, for periodic case.
        const size_t index1 = (index + 1 < controlPointCount) ? (index + 1) : 0;
        const size_t index2 = (index1 + 1 < controlPointCount) ? (index1 + 1) : 0;
        const size_t index3 = (index2 + 1 < controlPointCount) ? (index2 + 1) : 0;

        return evaluateSegment(controlPoints[index], controlPoints[index1], controlPoints[index2],
                               controlPoints[index3], u, order, tangent);
    }

    template <typename T>
    CUDA_CALLABLE void tessellateSegment(const T& p0,
                                         const T& p1,
                                         const T& p2,
                                         const T& p3,
                                         T* tessellatedPoints,
                                         T* tessellatedTangents,
                                         const size_t stepsPerSegment,
                                         bool includeFinalSample,
                                         const float startT = 0.f,
                                         const float endT = 1.f) const
    {
        const size_t sampleCount = stepsPerSegment + size_t(includeFinalSample);
        for (size_t sample = 0; sample < sampleCount; ++sample)
        {
            // From 0 to 1 along the segment
            const float u = startT + float(sample) / float(stepsPerSegment) * (endT - startT);
            const float u2 = u * u;
            const vec4f v(1.0f, u, u2, u * u2);
            const vec4f coeffs = (*m_basis) * v;
            tessellatedPoints[sample] = (p0 * coeffs[0] + p1 * coeffs[1] + p2 * coeffs[2] + p3 * coeffs[3]);
            if (tessellatedTangents != nullptr)
            {
                const vec4f tangentCoeffs = (*m_tangentBasis) * v;
                tessellatedTangents[sample] =
                    (p0 * tangentCoeffs[0] + p1 * tangentCoeffs[1] + p2 * tangentCoeffs[2] + p3 * tangentCoeffs[3]);
            }
        }
    }

    template <typename T>
    CUDA_CALLABLE T evaluateSegment(
        const T& p0, const T& p1, const T& p2, const T& p3, float u, int order = 0, T* tangent = nullptr) const
    {
        const float u2 = u * u;
        const float u3 = u * u2;
        const vec4f v = (order == 0 ? vec4f(1, u, u2, u3) :
                         order == 1 ? vec4f(0, 1, 2 * u, 3 * u2) :
                         order == 2 ? vec4f(0, 0, 2, 6 * u) :
                         order == 3 ? vec4f(0, 0, 0, 6) :
                                      vec4f(0, 0, 0, 0));
        const vec4f coeffs = (*m_basis) * v;

        if (tangent != nullptr)
        {
            const vec4f tangentCoeffs = (*m_tangentBasis) * v;
            *tangent = (p0 * tangentCoeffs[0] + p1 * tangentCoeffs[1] + p2 * tangentCoeffs[2] + p3 * tangentCoeffs[3]);
        }

        return (p0 * coeffs[0] + p1 * coeffs[1] + p2 * coeffs[2] + p3 * coeffs[3]);
    }

    template <typename T>
    CUDA_CALLABLE void tessellateEndSegment(const T* controlPoints,
                                            const size_t controlPointCount,
                                            T* tessellatedPoints,
                                            T* tessellatedTangents,
                                            size_t index,
                                            const size_t stepsPerSegment,
                                            bool includeFinalSample) const
    {
        T p0;
        T p1;
        T p2;
        T p3;
        if (index == 0)
        {
            p1 = controlPoints[index];
            p2 = controlPoints[index + 1];
            p3 = controlPoints[index + 2];
            p0 = 2 * p1 - p2;
        }
        else
        {
            p0 = controlPoints[index - 3];
            p1 = controlPoints[index - 2];
            p2 = controlPoints[index - 1];
            p3 = 2 * p2 - p1;
        }

        tessellateSegment(p0, p1, p2, p3, tessellatedPoints, tessellatedTangents, stepsPerSegment, includeFinalSample);
    }

    eBasisCurveWrap m_wrapMode;
    uint32_t m_vstep;
    const matrix4f* m_basis;
    const matrix4f* m_tangentBasis;
};

namespace bases
{
static constexpr float s_catmullRomFloats[4][4] = {
    { 0.0f, -0.5f, 1.0f, -0.5f }, { 1.0f, 0.0f, -2.5f, 1.5f }, { 0.0f, 0.5f, 2.0f, -1.5f }, { 0.0f, 0.0f, -0.5f, 0.5f }
};
static constexpr float s_catmullRomTangentFloats[4][4] = {
    { -0.5f, 2.0f, -1.5f, 0.0f }, { 0.0f, -5.0f, 4.5f, 0.0f }, { 0.5f, 4.0f, -4.5f, 0.0f }, { 0.0f, -1.0f, 1.5f, 0.0f }
};
static constexpr float s_bezierFloats[4][4] = {
    { 1.0f, -3.0f, 3.0f, -1.0f }, { 0.0f, 3.0f, -6.0f, 3.0f }, { 0.0f, 0.0f, 3.0f, -3.0f }, { 0.0f, 0.0f, 0.0f, 1.0f }
};
static constexpr float s_bezierTangentFloats[4][4] = {
    { -3.0f, 6.0f, -3.0f, 0.0f }, { 3.0f, -12.0f, 9.0f, 0.0f }, { 0.0f, 6.0f, -9.0f, 0.0f }, { 0.0f, 0.0f, 3.0f, 0.0f }
};
static constexpr float s_bsplineFloats[4][4] = { { (1.0f / 6.0f), -0.5f, 0.5f, -(1.0f / 6.0f) },
                                                 { (2.0f / 3.0f), 0.0f, -1.0f, 0.5f },
                                                 { (1.0f / 6.0f), 0.5f, 0.5f, -0.5f },
                                                 { 0.0f, 0.0f, 0.0f, (1.0f / 6.0f) } };
static constexpr float s_bsplineTangentFloats[4][4] = {
    { -0.5f, 1.0f, -0.5f, 0.0f }, { 0.0f, -2.0f, 1.5f, 0.0f }, { 0.5f, 1.0f, -1.5f, 0.0f }, { 0.0f, 0.0f, 0.5f, 0.0f }
};

// This is used for Bezier curves with 3 CVs and pinned
// BSpline curves with 3 CVs.
static constexpr float s_qBezierFloats[3][3] = { { 1.0f, -2.0f, 1.0f }, { 0.0f, 2.0f, -2.0f }, { 0.0f, 0.0f, 1.0f } };

static constexpr float s_qBezierTangentFloats[3][3] = { { -2.0f, 2.0f, 0.0f },
                                                        { 2.0f, -4.0f, 0.0f },
                                                        { 0.0f, 2.0f, 0.0f } };

// This is used for pinned Catmull-Rom curves with 3 CVs,
// where u=0 is at p0, u=0.5 is at p1, and u=1 is at p2.
// Lagrange polynomial:
//  p0*((u-0.5)*(u-1))/((0-0.5)*(0-1))
// +p1*((u-0)*(u-1))/((0.5-0)*(0.5-1))
// +p2*((u-0)*(u-0.5))/((1-0)*(1-0.5))
// =p0*(2*u^2 - 3*u + 1)
// +p1*(-4*u^2 + 4*u)
// +p2*(2*u^2 - u)
static constexpr float s_qCatmullRomFloats[3][3] = { { 1.0f, -3.0f, 2.0f }, { 0.0f, 4.0f, -4.0f }, { 0.0f, -1.0f, 2.0f } };

static constexpr float s_qCatmullRomTangentsFloats[3][3] = { { -3.0f, 4.0f, 0.0f },
                                                             { 4.0f, -8.0f, 0.0f },
                                                             { -1.0f, 4.0f, 0.0f } };
}

inline CUDA_CALLABLE const matrix4f& getBasis(eBasisCurveType type)
{
    static const matrix4f bezierBasis(bases::s_bezierFloats);
    static const matrix4f catmullRomBasis(bases::s_catmullRomFloats);
    static const matrix4f bsplineBasis(bases::s_bsplineFloats);
    switch (type)
    {
    case eBasisCurveType::Bezier:
        return bezierBasis;
    case eBasisCurveType::CatmullRom:
        return catmullRomBasis;
    case eBasisCurveType::BSpline:
        return bsplineBasis;
    }
    CUDA_SAFE_ASSERT(0);
    return bsplineBasis;
}

inline CUDA_CALLABLE const matrix4f& getTangentBasis(eBasisCurveType type)
{
    static const matrix4f bezierBasis(bases::s_bezierTangentFloats);
    static const matrix4f catmullRomBasis(bases::s_catmullRomTangentFloats);
    static const matrix4f bsplineBasis(bases::s_bsplineTangentFloats);
    switch (type)
    {
    case eBasisCurveType::Bezier:
        return bezierBasis;
    case eBasisCurveType::CatmullRom:
        return catmullRomBasis;
    case eBasisCurveType::BSpline:
        return bsplineBasis;
    }
    CUDA_SAFE_ASSERT(0);
    return bsplineBasis;
}

} // namespace curves
} // namespace geometry
} // namespace omni

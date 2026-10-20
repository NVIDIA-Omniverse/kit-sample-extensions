// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <omni/graph/core/Handle.h>
#include <omni/math/linalg/matrix.h>

#include <cuda.h> // CUDA_VERSION
#include <cuda_runtime.h>
#include <limits>

// #include <newton/ConjugateGradientNormalEquations.h> // XXX see note in target-deps.packman.xml
#include "CurveUtils.h"
#include "newton/ConjugateGradientNormalEquations.h"

namespace omni
{
namespace genproc
{

using omni::math::linalg::vec4f;
using namespace newton;

bool fitCubicBezierToPoints(const std::vector<vec3f>& points, const size_t numSegments, std::vector<vec3f>& controlPoints)
{

    bool success = false;

#if CUDA_VERSION >= 11000

    const size_t m = numSegments;
    const size_t n = points.size();

    controlPoints.resize(3 * m + 1);

    std::vector<float> tValues(n);
    std::vector<size_t> segmentIndices(n);

    // We map n points on a curve to m curve segments, with the (strong) assumption that the points are evenly
    // distributed across the segments and have evenly-spaced t-values within each segment.

    // With that assumption, we can say (for each spatial dimension separately)
    // A x = b
    // where b is the n x 1 vector of points on the curve,
    // x is the (3m + 1) x 1 vector of control points
    // and A is the n x (3m + 1) matrix of bezier coefficients.

    // for a small example, suppose we want to fit a curve with two segments
    // to eight points. Then the matrix would be:
    //
    // B0(t0)  B1(t0)  B2(t0)  B3(t0)    0       0       0
    // B0(t1)  B1(t1)  B2(t1)  B3(t1)    0       0       0
    // B0(t2)  B1(t2)  B2(t2)  B3(t2)    0       0       0
    // B0(t3)  B1(t3)  B2(t3)  B3(t3)    0       0       0
    //   0       0       0     B0(t4), B1(t4), B2(t4), B3(t4)
    //   0       0       0     B0(t5), B1(t5), B2(t5), B3(t5)
    //   0       0       0     B0(t6), B1(t6), B2(t6), B3(t6)
    //   0       0       0     B0(t7), B1(t7), B2(t7), B3(t7)
    //
    // t0 through t7 are used just to show that each row's t value can be distinct,
    // but in practice we use the same t values within each segment, so
    // t0 == t4, t1 == t5, t2 == t6, t3 == t7
    //
    // Note that adjacent segments have one control point in common,
    // which prevents us from solving for the segments independently.
    //
    // You can also see that the matrix gets sparser as the number of segments increases,
    // because we have 3m+1 columns but only four nonzeros per row.
    //
    // We can do the usual least squares problem:
    // minimize ||Ax - b||^2
    // with the conjugate gradient solver from mcong's newton library.

    const size_t pointsPerSegment = n / m;
    const size_t pointsPerLastSegment = n - pointsPerSegment * (m - 1);
    for (size_t i = 0; i < n; i++)
    {
        const size_t segmentIndex = std::min(i / pointsPerSegment, m - 1);
        segmentIndices[i] = segmentIndex;
        if (segmentIndex == m - 1)
        {
            const size_t idx = i - pointsPerSegment * (m - 1);
            tValues[i] = (float)idx / (float)(pointsPerLastSegment);
        }
        else
        {
            tValues[i] = (float)(i % pointsPerSegment) / (float)(pointsPerSegment);
        }
    }

    typedef int32_t IndexT;
    typedef float ScalarT;

    IndexT* rows = nullptr;
    IndexT* columns = nullptr;
    ScalarT* values = nullptr;
    ScalarT* x = nullptr;
    ScalarT* b = nullptr;

    // build matrix and solve once for each dimension:

    // NOTE: avoidSharpTurns was an experiment that doesn't produce very good curves.
    // So it's unconditionally false here, but I haven't brought myself to deleting it yet..
    const bool avoidSharpTurns = false;
    if (avoidSharpTurns)
    {
        size_t numNonZeros = 4 * n;

        cudaError_t cudaStatus = cudaMallocManaged(&rows, numNonZeros * sizeof(IndexT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&columns, numNonZeros * sizeof(IndexT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&values, numNonZeros * sizeof(ScalarT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&x, (2 * m + 2) * sizeof(ScalarT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&b, n * sizeof(ScalarT));
        CARB_ASSERT(cudaStatus == cudaSuccess);

        for (size_t i = 0; i < n; i++)
        {
            const size_t& segmentIndex = segmentIndices[i];

            const float& t = tValues[i];
            const vec4f tVec(1.f, t, t * t, t * t * t);
            const vec4f coeffs = getBasis(eBasisCurveType::Bezier) * tVec;

            rows[4 * i] = (int32_t)i;
            rows[4 * i + 1] = (int32_t)i;
            rows[4 * i + 2] = (int32_t)i;
            rows[4 * i + 3] = (int32_t)i;

            columns[4 * i] = (int32_t)(2 * segmentIndex);
            columns[4 * i + 1] = (int32_t)(2 * segmentIndex + 1);
            columns[4 * i + 2] = (int32_t)(2 * segmentIndex + 2);
            columns[4 * i + 3] = (int32_t)(2 * segmentIndex + 3);

            if (segmentIndex == 0)
            {
                values[4 * i] = coeffs[0];
                values[4 * i + 1] = coeffs[1];
                values[4 * i + 2] = coeffs[2];
                values[4 * i + 3] = coeffs[3];
            }
            else
            {
                values[4 * i] = -2.f * coeffs[1];
                values[4 * i + 1] = coeffs[0] + 2.f * coeffs[1];
                values[4 * i + 2] = coeffs[2];
                values[4 * i + 3] = coeffs[3];
            }
        }

        ConjugateGradientNormalEquations<ScalarT, IndexT> cgnr(n, 2 * m + 2, numNonZeros, rows, columns, values);

        const ScalarT relativeTolerance = (ScalarT)1e-6;
        const ScalarT absoluteTolerance = (ScalarT)1e-8;
        const int maxIterations = 1000;

        for (size_t d = 0; d < vec3f::dimension; d++)
        {
            for (size_t i = 0; i < n; i++)
            {
                b[i] = points[i][d];
            }

            cudaStatus = cudaMemset(x, 0, (3 * m + 1) * sizeof(ScalarT));
            CARB_ASSERT(cudaStatus == cudaSuccess);

            cgnr.solve(x, b, relativeTolerance, absoluteTolerance, maxIterations);

            // m is at least 1, so we have at least the first four CVs
            for (size_t i = 0; i < 4; i++)
            {
                controlPoints[i][d] = x[i];
            }
            for (size_t i = 0; i < m - 1; i++)
            {
                controlPoints[4 + 3 * i][d] = 2.f * x[4 + 2 * i - 1] - x[4 + 2 * i - 2];
                controlPoints[4 + 3 * i + 1][d] = x[4 + 2 * i];
                controlPoints[4 + 3 * i + 2][d] = x[4 + 2 * i + 1];
            }
        }
    }
    else
    {
        size_t numNonZeros = 4 * n;

        cudaError_t cudaStatus = cudaMallocManaged(&rows, numNonZeros * sizeof(IndexT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&columns, numNonZeros * sizeof(IndexT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&values, numNonZeros * sizeof(ScalarT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&x, (3 * m + 1) * sizeof(ScalarT));
        CARB_ASSERT(cudaStatus == cudaSuccess);
        cudaStatus = cudaMallocManaged(&b, n * sizeof(ScalarT));
        CARB_ASSERT(cudaStatus == cudaSuccess);

        for (size_t i = 0; i < n; i++)
        {
            const size_t& segmentIndex = segmentIndices[i];

            const float& t = tValues[i];
            const vec4f tVec(1.f, t, t * t, t * t * t);
            const vec4f coeffs = getBasis(eBasisCurveType::Bezier) * tVec;

            rows[4 * i] = (int32_t)i;
            rows[4 * i + 1] = (int32_t)i;
            rows[4 * i + 2] = (int32_t)i;
            rows[4 * i + 3] = (int32_t)i;

            columns[4 * i] = (int32_t)(3 * segmentIndex);
            columns[4 * i + 1] = (int32_t)(3 * segmentIndex + 1);
            columns[4 * i + 2] = (int32_t)(3 * segmentIndex + 2);
            columns[4 * i + 3] = (int32_t)(3 * segmentIndex + 3);

            values[4 * i] = coeffs[0];
            values[4 * i + 1] = coeffs[1];
            values[4 * i + 2] = coeffs[2];
            values[4 * i + 3] = coeffs[3];
        }

        ConjugateGradientNormalEquations<ScalarT, IndexT> cgnr(n, 3 * m + 1, numNonZeros, rows, columns, values);

        const ScalarT relativeTolerance = (ScalarT)1e-6;
        const ScalarT absoluteTolerance = (ScalarT)1e-8;
        const int maxIterations = 1000;

        for (size_t d = 0; d < vec3f::dimension; d++)
        {
            for (size_t i = 0; i < n; i++)
            {
                b[i] = points[i][d];
            }

            cudaStatus = cudaMemset(x, 0, (3 * m + 1) * sizeof(ScalarT));
            CARB_ASSERT(cudaStatus == cudaSuccess);

            cgnr.solve(x, b, relativeTolerance, absoluteTolerance, maxIterations);

            for (size_t i = 0; i < 3 * m + 1; i++)
            {
                controlPoints[i][d] = x[i];
            }
        }
    }

    cudaFree(b);
    cudaFree(x);
    cudaFree(values);
    cudaFree(columns);
    cudaFree(rows);

    success = true;

#else
    CARB_LOG_ERROR_ONCE("Unsupported CUDA version for curve fitting. No fitting operation has been performed.");
#endif
    return success;
}

bool samplePointsOnCurve(ConstBundlePrims& curvePrims,
                         const std::vector<float>& uValues,
                         std::vector<vec3f>& /*out*/ pointsOnCurve,
                         std::vector<vec3f>& /*out*/ tangentsAtPoint)
{
    bool foundCurve = false;

    auto processingOp = [&](const bool validCurve, const std::string& errorMessage, const size_t primIndex,
                            const size_t curveIndex, const SplineCurve* curve, const std::vector<vec3f>* controlPoints)
    {
        if (foundCurve)
        {
            return;
        }

        if (!validCurve)
        {
            CARB_LOG_WARN_ONCE(errorMessage.c_str());
            return;
        }

        const bool normalizeLengths = true;
        const size_t samplesPerSegment = 20;
        const std::vector<float> curveDistances =
            approximateDistanceAlongCurve(*curve, *controlPoints, normalizeLengths, samplesPerSegment);
        const size_t segmentCount = curve->getSegmentCount(controlPoints->size());
        std::vector<float> segmentDistances(segmentCount); // TODO: cache these distances in node state until bundle
                                                           // prim dirty ID changes
        for (size_t i = 0; i < segmentCount; i++)
        {
            const size_t lastOffset = (i == segmentCount - 1 ? 1 : 0);
            segmentDistances[i] = curveDistances[(i + 1) * samplesPerSegment + lastOffset - 1];
        }

        pointsOnCurve.resize(uValues.size());
        tangentsAtPoint.resize(uValues.size());
        for (size_t i = 0; i < uValues.size(); i++)
        {
            size_t segmentIndex = 0;

            while (segmentDistances[segmentIndex] < uValues[i])
            {
                if (segmentIndex == segmentDistances.size() - 1)
                {
                    break;
                }
                else
                {
                    segmentIndex++;
                }
            }
            const float denom =
                segmentDistances[segmentIndex] - (segmentIndex == 0 ? 0.f : segmentDistances[segmentIndex - 1]);
            const float parametricValue =
                (uValues[i] - (segmentIndex == 0 ? 0.f : segmentDistances[segmentIndex - 1])) / denom;

            const size_t segmentStartIndex = segmentIndex * curve->m_vstep;
            const int order = 0;
            pointsOnCurve[i] = curve->evaluateSegment(controlPoints->data(), controlPoints->size(), segmentStartIndex,
                                                      parametricValue, order, &tangentsAtPoint[i]);
        }

        foundCurve = true;
    };

    processCurvesInBundle(curvePrims, processingOp);

    return foundCurve;
}

} // namespace genproc
} // namespace omni

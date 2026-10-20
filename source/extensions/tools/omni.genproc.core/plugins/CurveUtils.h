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

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include "Utils.h"

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/iComputeGraph.h>
#include <omni/math/linalg/quat.h>
#include <omni/math/linalg/vec.h>

#include <iostream>

namespace omni
{
namespace genproc
{

using omni::geometry::curves::eBasisCurveWrap;
using omni::geometry::curves::SplineCurve;
using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;
using omni::graph::core::GraphContextObj;
using omni::graph::core::NameToken;
using omni::graph::core::NodeObj;
using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using namespace omni::geometry::curves;

bool fitCubicBezierToPoints(const std::vector<vec3f>& points, const size_t numSegments, std::vector<vec3f>& controlPoints);

bool samplePointsOnCurve(ConstBundlePrims& curvePrims,
                         const std::vector<float>& uValues,
                         std::vector<vec3f>& /*out*/ pointsOnCurve,
                         std::vector<vec3f>& /*out*/ tangentsAtPoint);

template <class TV>
std::vector<typename TV::ScalarType> approximateDistanceAlongCurve(const SplineCurve& curve,
                                                                   const std::vector<TV>& controlPoints,
                                                                   const bool normalizeLengths,
                                                                   size_t stepsPerSegment = 20,
                                                                   std::vector<TV>* pointsOut = nullptr,
                                                                   std::vector<TV>* tangentsOut = nullptr)
{
    using T = typename TV::ScalarType;
    const bool includeSegmentFinalSamples = false;

    // do a tessellation with some relatively high resolution to approximate curve length
    std::vector<TV> tessellatedPoints;
    curve.tessellate(controlPoints.data(), controlPoints.size(), tessellatedPoints, stepsPerSegment,
                     includeSegmentFinalSamples, tangentsOut);

    const bool isPeriodic = (curve.m_wrapMode == eBasisCurveWrap::Periodic);

    std::vector<T> distanceAlongCurve(tessellatedPoints.size() + size_t(isPeriodic));

    T length = (T)0;
    for (size_t i = 0; i < tessellatedPoints.size(); i++)
    {
        if (i != 0)
            length += (tessellatedPoints[i] - tessellatedPoints[i - 1]).GetLength();
        distanceAlongCurve[i] = length;
    }

    if (isPeriodic)
    {
        length += (tessellatedPoints[0] - tessellatedPoints.back()).GetLength();
        distanceAlongCurve.back() = length;
        if (tangentsOut != nullptr)
        {
            tangentsOut->push_back((*tangentsOut)[0]);
        }
    }

    if (normalizeLengths && length > 0)
    {
        for (size_t i = 0; i < distanceAlongCurve.size(); i++)
        {
            distanceAlongCurve[i] /= length;
        }
    }

    if (pointsOut != nullptr)
    {
        (*pointsOut) = std::move(tessellatedPoints);
    }

    return distanceAlongCurve;
}

template <typename ProcessingOpT>
void processCurvesInBundle(ConstBundlePrims& curvePrims, const ProcessingOpT& processingOp)
{
    static const auto tPoints = NameToken("points");
    static const auto tCurveVertexCounts = NameToken("curveVertexCounts");
    static const auto tBasis = NameToken("basis");
    static const auto tWrap = NameToken("wrap");
    static const auto tNonPeriodic = NameToken("nonperiodic");
    static const auto tPeriodic = NameToken("periodic");
    static const auto tPinned = NameToken("pinned");
    static const auto tBezier = NameToken("bezier");
    static const auto tBSpline = NameToken("bspline");
    static const auto tCatmullRom = NameToken("catmullRom");

    const size_t curvePrimCount = curvePrims.getPrimCount();

    std::vector<matrix4d> transforms;
    getPrimTransforms(curvePrims, transforms);

    for (size_t primIndex = 0; primIndex < curvePrimCount; primIndex++)
    {
        ConstBundlePrim* curvePrim = curvePrims.getConstPrim(primIndex);
        const matrix4d& transform = transforms[primIndex];

        BundleAttrib const* pointsInAttr = curvePrim->getConstAttr(tPoints);
        BundleAttrib const* curveVertexCountsAttr = curvePrim->getConstAttr(tCurveVertexCounts);
        BundleAttrib const* curveBasisAttr = curvePrim->getConstAttr(tBasis);
        BundleAttrib const* wrapTypeAttr = curvePrim->getConstAttr(tWrap);

        // Note: it's ok if curveVertexCountsAttr does not exist, in the case of a single curve
        if (pointsInAttr == nullptr || curveBasisAttr == nullptr || wrapTypeAttr == nullptr)
        {
            std::cout << "pointsInAttr: " << pointsInAttr << std::endl;
            std::cout << "curveBasisAttr: " << curveBasisAttr << std::endl;
            std::cout << "wrapTypeAttr: " << wrapTypeAttr << std::endl;
            processingOp(false, "Input prim does not have basis curve attributes.", primIndex, 0, nullptr, nullptr);
            continue;
        }

        const size_t pointsInCount = pointsInAttr->size();
        if (pointsInCount == 0)
        {
            processingOp(false, "No points in input prim.", primIndex, 0, nullptr, nullptr);
            continue;
        }

        const vec3f* const pointsIn = pointsInAttr->getData<vec3f>();
        const int* curveVertexCounts = curveVertexCountsAttr == nullptr ? nullptr : curveVertexCountsAttr->getData<int>();
        const size_t curveCount = curveVertexCounts == nullptr ? 0 : curveVertexCountsAttr->size();
        const auto* basisToken = curveBasisAttr->getData<omni::graph::core::NameToken>();
        const auto* wrapToken = wrapTypeAttr->getData<omni::graph::core::NameToken>();

        if (pointsIn == nullptr || basisToken == nullptr || wrapToken == nullptr)
        {
            processingOp(false, "Input prim does not have valid basis curve data.", primIndex, 0, nullptr, nullptr);
            continue;
        }

        eBasisCurveWrap curveWrapType;
        if (*wrapToken == tNonPeriodic)
        {
            curveWrapType = eBasisCurveWrap::NonPeriodic;
        }
        else if (*wrapToken == tPeriodic)
        {
            curveWrapType = eBasisCurveWrap::Periodic;
        }
        else if (*wrapToken == tPinned)
        {
            curveWrapType = eBasisCurveWrap::Pinned;
        }
        else
        {
            processingOp(false, "Invalid curve wrap type", primIndex, 0, nullptr, nullptr);
            continue;
        }

        eBasisCurveType curveBasisType;

        if (*basisToken == tBSpline)
        {
            curveBasisType = eBasisCurveType::BSpline;
        }
        else if (*basisToken == tBezier)
        {
            curveBasisType = eBasisCurveType::Bezier;
        }
        else if (*basisToken == tCatmullRom)
        {
            curveBasisType = eBasisCurveType::CatmullRom;
        }
        else
        {
            processingOp(false, "Invalid curve basis type", primIndex, 0, nullptr, nullptr);
            continue;
        }

        for (size_t curveIndex = 0, startIndex = 0; curveIndex < (curveCount == 0 ? 1 : curveCount); curveIndex++)
        {
            const size_t count = (curveCount == 0 ? pointsInCount : curveVertexCounts[curveIndex]);

            std::vector<vec3f> controlPoints;
            std::transform(pointsIn + startIndex, pointsIn + startIndex + count, std::back_inserter(controlPoints),
                           [&](const vec3f& x) { return transform.Transform(x); });

            startIndex += count;

            SplineCurve curve(curveWrapType, curveBasisType);

            // all that... just to call this:
            processingOp(true, "", primIndex, curveIndex, &curve, &controlPoints);
        }
    }
}


} // namespace genproc
} // namespace omni

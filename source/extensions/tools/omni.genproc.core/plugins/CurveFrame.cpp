// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "CurveFrame.h"

#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>

#include <cassert>
#include <stdint.h>

namespace omni
{
namespace genproc
{

using omni::math::linalg::matrix3f;

static matrix3f stretchMatrix(const vec3f& prevEdge, const vec3f& nextEdge, const float maxScale)
{
    const vec3f perp = (prevEdge - nextEdge).GetNormalized();
    // This is 1/cos(theta/2), where theta is the angle difference between prevEdge and nextEdge
    float scale = sqrt(2 / (1 + prevEdge.Dot(nextEdge)));
    if (scale > maxScale)
        scale = maxScale;
    // To avoid depending on perp near a scale of 1 (angle of 0), since it can be nondegenerate or chaotic,
    // just add (scale-1) * outerProduct(perp, perp) to the identity matrix
    matrix3f extra;
    extra.SetRow(0, (scale - 1) * perp[0] * perp);
    extra.SetRow(1, (scale - 1) * perp[1] * perp);
    extra.SetRow(2, (scale - 1) * perp[2] * perp);
    return extra + matrix3f(1);
}

void curveFrameTangents(
    size_t pointCount, const vec3f* points, const bool wrap, vec3f* tangents, matrix3f* stretches, const float maxScale)
{
    if (pointCount <= 2)
    {
        if (pointCount == 1)
        {
            // Only point, no edge; just use z axis, since curveGridPoints() uses
            // tangent for the z axis of the cross sections it's transforming,
            // so this corresponds with not applying a transformation to it.
            tangents[0] = vec3f(0, 0, 1);
            if (stretches)
                stretches[0].SetIdentity();
        }
        else if (pointCount == 2)
        {
            // Only one edge
            const vec3f diff = (points[1] - points[0]).GetNormalized();
            tangents[0] = diff;
            tangents[1] = diff;
            if (stretches)
            {
                stretches[0].SetIdentity();
                stretches[1].SetIdentity();
            }
        }
        return;
    }

    // The first tangent follows the first edge.
    vec3f prevEdge = (points[1] - points[0]).GetNormalized();
    const vec3f firstEdge = prevEdge;
    if (!wrap)
    {
        tangents[0] = prevEdge;
        if (stretches)
            stretches[0].SetIdentity();
    }
    else
    {
        vec3f lastEdge = (points[0] - points[pointCount - 1]).GetNormalized();
        tangents[0] = (lastEdge + prevEdge).GetNormalized();
        if (stretches)
            stretches[0] = stretchMatrix(lastEdge, prevEdge, maxScale);
    }

    for (size_t edgei = 1; edgei < pointCount - 1; ++edgei)
    {
        vec3f nextEdge = (points[edgei + 1] - points[edgei]).GetNormalized();
        // Average the two directions.
        tangents[edgei] = (prevEdge + nextEdge).GetNormalized();
        if (stretches)
            stretches[edgei] = stretchMatrix(prevEdge, nextEdge, maxScale);
        prevEdge = nextEdge;
    }

    // The last tangent follows the last edge.
    if (!wrap)
    {
        tangents[pointCount - 1] = prevEdge;
        if (stretches)
            stretches[pointCount - 1].SetIdentity();
    }
    else
    {
        tangents[pointCount - 1] = (prevEdge + firstEdge).GetNormalized();
        if (stretches)
            stretches[pointCount - 1] = stretchMatrix(prevEdge, firstEdge, maxScale);
    }
}

static void computeUVAndDistSq(const vec3f& P,
                               const float t,
                               const vec3f& x0,
                               const vec3f& x1,
                               const vec3f& y0,
                               const vec3f& y1,
                               const vec3f& p0,
                               const vec3f& p1,
                               float& u,
                               float& v,
                               float& distanceSquared)
{
    vec3f x = x0 + t * (x1 - x0);
    vec3f y = y0 + t * (y1 - y0);
    vec3f diff = P - (p0 + t * (p1 - p0));
    float x2 = x.GetLengthSq();
    float y2 = y.GetLengthSq();
    float xy = x.Dot(y);
    float xd = x.Dot(diff);
    float yd = y.Dot(diff);
    // Solve:
    // [x2 xy][u] = [xd]
    // [xy y2][v] = [yd]
    //
    // [u] = (x2*y2 - xy^2)^-1[ y2 -xy][xd]
    // [v]                    [-xy  x2][yd]
    float det = x2 * y2 - xy * xy;
    if (det == 0)
    {
        // Unlikely; just fall back to 0,0
        u = 0;
        v = 0;
    }
    else
    {
        u = (xd * y2 - yd * xy) / det;
        v = (yd * x2 - xd * xy) / det;
    }
    vec3f fullDiff = (diff - u * x - v * y);
    distanceSquared = fullDiff.GetLengthSq();
}

void pointsToCurveCaptureCoords(size_t curvePointCount,
                                const vec3f* curvePoints,
                                const vec3f* tangents,
                                const vec3f* ups,
                                const vec3f* outs,
                                size_t pointsToCaptureCount,
                                const vec3f* pointsToCapture,
                                vec3f* captureCoords)
{
    // Edge cases
    if (curvePointCount == 0)
    {
        // No curve points, so just assume same space
        for (size_t i = 0; i < pointsToCaptureCount; ++i)
        {
            captureCoords[i] = pointsToCapture[i];
        }
        return;
    }
    if (curvePointCount == 1)
    {
        // Only one curve point, so don't interpolate.
        const vec3f curvePoint = curvePoints[0];
        for (size_t i = 0; i < pointsToCaptureCount; ++i)
        {
            const vec3f point = pointsToCapture[i] - curvePoint;
            // Inverse of a rotation matrix is its transpose.
            const matrix3f inverseRotation(outs[0][0], outs[0][1], outs[0][2], ups[0][0], ups[0][1], ups[0][2],
                                           tangents[0][0], tangents[0][1], tangents[0][2]);
            captureCoords[i] = inverseRotation * point;
        }
        return;
    }

    // Common case
    CARB_ASSERT(curvePointCount >= 2);
    const size_t curveEdgeCount = curvePointCount - 1;
    for (size_t i = 0; i < pointsToCaptureCount; ++i)
    {
        const vec3f pointToCapture = pointsToCapture[i];

        // Check for which edge has t for this point in [0,1] and is closest to the edge.
        // If none do, it should be either in the space before (t < 0) the first edge or
        // after (t > 1) the last edge, so consider those, too, including in the closest
        // check, in case something is in range for some edge, but closer to an end point.
        // This is not a great approach if the point is farther from the curve than the
        // radius of curvature at nearby locations of the curve, but it's an okay first step.
        bool hasValidCoord = false;
        float minDistanceSquare;
        vec3f bestCoord;
        for (size_t edgei = 0; edgei < curveEdgeCount; ++edgei)
        {
            const vec3f edgePoint0 = curvePoints[edgei];
            const vec3f edgePoint1 = curvePoints[edgei + 1];

            // Find the t along the edge where the plane of the interpolated out (x) and up (y) contains the point.
            // P = p0 + t*(p1-p0) + u*(x0 + t*(x1-x0)) + v*(y0 + t*(y1-y0))
            // For a particular t, it's easy to find the u and v that will give the point P' closest to P:
            // A = [x y] (3x2), where x and y are column vectors (x0 + t*(x1-x0)) and (y0 + t*(y1-y0))
            // 2x2 least squares solution:
            // (A^T)A[u v]^T = (A^T)(P-p)
            // (Since x and y are usually close to orthonormal, (A^T)A is close to identity, so should behave nicely.)
            // We want to find the t that minimizes (to zero)
            // |P-P'|^2 = (P - p - u*x - v*y) dot (P - p - u*x - v*y)
            // We could do a Newton search on t to find where the t derivative equals zero,
            // but the derivatives get hairy due to u and v being dependnent on t, and we're primarily
            // interested in t in [0,1], so let's do 5 evaluations and then "bisection", picking the two
            // ranges around the lowest value to narrow in on.
            // TODO: Do this a way that converges faster.

            float distanceSquares[5];
            float ts[5] = { 0.0f, 0.25f, 0.5f, 0.75f, 1.0f };
            float dt = 0.25f;
            size_t bestTestIndex = 0;
            for (size_t testi = 0; testi < 5; ++testi)
            {
                float u;
                float v;
                computeUVAndDistSq(pointToCapture, ts[testi], outs[edgei], outs[edgei + 1], ups[edgei], ups[edgei + 1],
                                   edgePoint0, edgePoint1, u, v, distanceSquares[testi]);
                if (distanceSquares[testi] < distanceSquares[bestTestIndex])
                {
                    bestTestIndex = testi;
                }
            }
            for (size_t iteration = 0; iteration < 12; ++iteration)
            {
                // Zoom in on the ones around the best index
                dt *= 0.5f;
                if (bestTestIndex <= 1)
                {
                    // Keep beginning half
                    ts[4] = ts[2];
                    ts[3] = 0.5f * (ts[1] + ts[2]);
                    ts[2] = ts[1];
                    ts[1] = 0.5f * (ts[0] + ts[1]);
                    distanceSquares[4] = distanceSquares[2];
                    distanceSquares[2] = distanceSquares[1];
                    bestTestIndex *= 2;
                }
                else if (bestTestIndex == 2)
                {
                    // Keep middle half
                    ts[0] = ts[1];
                    ts[1] = 0.5f * (ts[1] + ts[2]);
                    ts[4] = ts[3];
                    ts[3] = 0.5f * (ts[2] + ts[3]);
                    distanceSquares[0] = distanceSquares[1];
                    distanceSquares[4] = distanceSquares[3];
                }
                else
                {
                    // Keep last half
                    ts[0] = ts[2];
                    ts[1] = 0.5f * (ts[2] + ts[3]);
                    ts[2] = ts[3];
                    ts[3] = 0.5f * (ts[3] + ts[4]);
                    distanceSquares[0] = distanceSquares[2];
                    distanceSquares[2] = distanceSquares[3];
                    bestTestIndex = (bestTestIndex == 3) ? 2 : 4;
                }
                // Recompute distanceSquared for 1 and 3 (the new ts)
                for (size_t testi = 1; testi < 5; testi += 2)
                {
                    float u;
                    float v;
                    computeUVAndDistSq(pointToCapture, ts[testi], outs[edgei], outs[edgei + 1], ups[edgei],
                                       ups[edgei + 1], edgePoint0, edgePoint1, u, v, distanceSquares[testi]);
                    if (distanceSquares[testi] < distanceSquares[bestTestIndex])
                    {
                        bestTestIndex = testi;
                    }
                }
            }

            // Find the t implied by the 3 closest
            // f(t) = f0*(t-t1)*(t-t2)/((t0-t1)*(t0-t2)) + f1*(t-t0)*(t-t2)/((t1-t0)*(t1-t2)) +
            // f2*(t-t0)*(t-t1)/((t2-t0)*(t2-t1))
            //      = f0*(t-t1)*(t-t2)/(2*dt*dt) + f1*(t-t0)*(t-t2)/(dt*dt) + f2*(t-t0)*(t-t1)/(2*dt*dt)
            //      = ((f0 + 2*f1 + f2)*(t*t) - (f0*(t1+t2) + 2*f1*(t0+t2) + f2*(t0*t1))*t + (f0*t1*t2 + f1*t0*t2 +
            //      f2*t0*t1))/(2*dt*dt)
            // f'(t) = 0 = (2*(f0 + 2*f1 + f2)*t - (f0*(t1+t2) + 2*f1*(t0+t2) + f2*(t0*t1)))/(2*dt*dt)
            // t = (f0*(t1+t2) + 2*f1*(t0+t2) + f2*(t0*t1))/(2*(f0 + 2*f1 + f2))
            if (bestTestIndex == 0)
                ++bestTestIndex;
            else if (bestTestIndex == 4)
                --bestTestIndex;

            float t0 = ts[bestTestIndex - 1];
            float t1 = ts[bestTestIndex];
            float t2 = ts[bestTestIndex + 1];
            float f0 = distanceSquares[bestTestIndex - 1];
            float f1 = distanceSquares[bestTestIndex];
            float f2 = distanceSquares[bestTestIndex + 1];
            float denominator = f0 + (2 * f1) + f2;
            float numerator = 0.5f * (f0 * (t1 + t2) + 2 * f1 * (t0 + t2) + f2 * (t0 + t1));
            float t;
            if (denominator == 0.0f)
            {
                // At or near a point where the distance is independent of t,
                // which can happen near points along the line where the end planes meet.
                t = t1;
            }
            else if ((denominator <= -1.0e-5f * numerator) || (denominator >= (1 + 1.0e-5f) * numerator))
            {
                // Out of range for this edge
                continue;
            }
            else
            {
                t = numerator / denominator;
                if (t < 0)
                    t = 0;
                else if (t > 1)
                    t = 1;
            }

            float u;
            float v;
            float fitDistanceSquared;
            computeUVAndDistSq(pointToCapture, t, outs[edgei], outs[edgei + 1], ups[edgei], ups[edgei + 1], edgePoint0,
                               edgePoint1, u, v, fitDistanceSquared);

            vec3f edgePoint = edgePoint0 + t * (edgePoint1 - edgePoint0);
            float edgePointToPointDistanceSq = (pointToCapture - edgePoint).GetLengthSq();
            if (!hasValidCoord || edgePointToPointDistanceSq < minDistanceSquare)
            {
                hasValidCoord = true;
                minDistanceSquare = edgePointToPointDistanceSq;
                bestCoord = vec3f(u, v, t + edgei);
            }
        }

        if (!hasValidCoord)
        {
            // Check both end hemispheres
            const vec3f diff0 = pointToCapture - curvePoints[0];
            const vec3f diff1 = pointToCapture - curvePoints[curvePointCount - 1];
            const float distanceSquared0 = diff0.GetLengthSq();
            const float distanceSquared1 = diff1.GetLengthSq();
            const float t0 = diff0.Dot(tangents[0]);
            const float t1 = diff1.Dot(tangents[curvePointCount - 1]);
            if (t0 <= 0)
            {
                hasValidCoord = true;
                bestCoord = vec3f(diff0.Dot(outs[0]), diff0.Dot(ups[0]), t0);
            }
            if (t1 >= 0 && (!hasValidCoord || distanceSquared1 < distanceSquared0))
            {
                hasValidCoord = true;
                bestCoord = vec3f(diff1.Dot(outs[curvePointCount - 1]), diff1.Dot(ups[curvePointCount - 1]),
                                  (curvePointCount - 1) + t1);
            }
            // The only way we should be likely to have no valid coords is if there
            // are infinities or NaNs involved.
            assert(hasValidCoord);
        }
        captureCoords[i] = (hasValidCoord ? bestCoord : vec3f(0, 0, 0));
    }
}

void curveCaptureCoordsToPoints(size_t curvePointCount,
                                const vec3f* curvePoints,
                                const vec3f* tangents,
                                const vec3f* ups,
                                const vec3f* outs,
                                size_t captureCoordCount,
                                const vec3f* captureCoords,
                                vec3f* outputPoints)
{
    // Edge cases
    if (curvePointCount == 0)
    {
        // No curve points, so just assume same space
        for (size_t i = 0; i < captureCoordCount; ++i)
        {
            outputPoints[i] = captureCoords[i];
        }
        return;
    }
    if (curvePointCount == 1)
    {
        // Only one curve point, so don't interpolate.
        const vec3f curvePoint = curvePoints[0];
        for (size_t i = 0; i < captureCoordCount; ++i)
        {
            const vec3f& captureCoord = captureCoords[i];
            outputPoints[i] =
                curvePoint + (captureCoord[0] * outs[0]) + (captureCoord[1] * ups[0]) + (captureCoord[2] * tangents[0]);
        }
        return;
    }

    // Common case
    CARB_ASSERT(curvePointCount >= 2);
    const size_t curveEdgeCount = curvePointCount - 1;
    for (size_t i = 0; i < captureCoordCount; ++i)
    {
        const vec3f& captureCoord = captureCoords[i];
        if (captureCoord[2] <= 0)
        {
            // Before first edge
            outputPoints[i] = curvePoints[0] + (captureCoord[0] * outs[0]) + (captureCoord[1] * ups[0]) +
                              (captureCoord[2] * tangents[0]);
        }
        else if (captureCoord[2] >= curveEdgeCount)
        {
            // After last edge
            float remaining = captureCoord[2] - curveEdgeCount;
            outputPoints[i] = curvePoints[curveEdgeCount] + (captureCoord[0] * outs[curveEdgeCount]) +
                              (captureCoord[1] * ups[curveEdgeCount]) + (remaining * tangents[curveEdgeCount]);
        }
        else
        {
            // In an edge, so interpolate.
            const size_t edgei = size_t(captureCoord[2]);
            CARB_ASSERT(edgei < curveEdgeCount);
            const float t = captureCoord[2] - edgei;

            // The t space is the space of the edge.
            // NOTE: The frame will usually be not quite orthogonal, but this is unavoidable if the edge is
            //       a straight segment incident to two non-collinear edges, since the frame at the beginning
            //       of the edge is different from at the end of the edge.
            vec3f edge = curvePoints[edgei + 1] - curvePoints[edgei];
            vec3f pointOnEdge = curvePoints[edgei] + (t * edge);

            // Linearly interpolate axes, but then normalize them to somewhat preserve distances from the edge.
            vec3f uaxis = outs[edgei] + t * (outs[edgei + 1] - outs[edgei]);
            uaxis.Normalize();
            vec3f vaxis = ups[edgei] + t * (ups[edgei + 1] - ups[edgei]);
            vaxis.Normalize();
            outputPoints[i] = pointOnEdge + (captureCoord[0] * uaxis) + (captureCoord[1] * vaxis);
        }
    }
}

}
}

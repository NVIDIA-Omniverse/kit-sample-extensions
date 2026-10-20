// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "Scatter.h"

#include "PhysXUtils.h"

#include <omni/math/linalg/vec.h>
#include <physx/include/geometry/PxGeometryQuery.h>
#include <physx/include/geometry/PxMeshQuery.h>
#include <physx/include/geometry/PxTriangle.h>

#include <unordered_map>

using omni::math::linalg::vec2f;
using omni::math::linalg::vec3f;

float triangleArea(const vec3f& p0, const vec3f& p1, const vec3f& p2)
{
    return (0.5f * GfCross(p1 - p0, p2 - p0).GetLength());
}

void validateBarycentric(float& u, float& v)
{
    if (u + v > 1.f)
    {
        const float excess = (u + v - 1.f);
        u -= excess;
        v -= excess;
    }
}

void calculateBarycentric(const vec3f& a, const vec3f& b, const vec3f& c, const vec3f& p, float& u, float& v)
{
    const float abcArea = triangleArea(a, b, c);
    const float capArea = triangleArea(c, a, p);
    const float abpArea = triangleArea(a, b, p);
    u = capArea / abcArea;
    v = abpArea / abcArea;
}

void triangleAreaCDF(const std::vector<vec3f>& points, const std::vector<int>& triIndices, std::vector<double>& cdf)
{
    const size_t pointCount = points.size();
    const size_t triangleCount = triIndices.size() / 3;
    if (triangleCount * 3 != triIndices.size())
    {
        // FIXME: Add warning about invalid array size!
    }
    // One more value than triangles, so that no special case is required for either end when sampling.
    cdf.reserve(triangleCount + 1);
    cdf.push_back(0);
    double sum = 0;
    for (size_t tri = 0, i = 0; tri < triangleCount; ++tri, i += 3)
    {
        int ptis[3] = { triIndices[i], triIndices[i + 1], triIndices[i + 2] };
        if (ptis[0] < pointCount || ptis[1] < pointCount || ptis[2] < pointCount)
        {
            const vec3f pt0 = points[ptis[0]];
            const vec3f pt1 = points[ptis[1]];
            const vec3f pt2 = points[ptis[2]];
            const double area = (double)triangleArea(pt0, pt1, pt2);
            sum += area;
        }
        else
        {
            // Invalid triangle
            // FIXME: Report an error!
        }
        cdf.push_back(sum);
    }
}

static const float degreeThreshold = cos(omni::math::linalg::GfDegreesToRadians(5.f));
static constexpr float distanceThreshold = 1E-4f;

bool pointInMeshRegion(const vec3f& point,
                       const physx::PxTriangleMeshGeometry& meshGeometry,
                       const physx::PxTriangleMeshGeometry& regionGeometry,
                       const bool selfOcclude)
{
    // An heuristic way to check if a point sampled from the mesh is within the region.
    // First check if the point is close enough to the mesh, otherwise check if the direction
    // between the point and the closest point on the region geometry aligns with the hit normal.
    vec3f closestPoint;
    if (!omni::genproc::getMeshClosestPoint(point, regionGeometry, closestPoint))
        return false;

    vec3f direction = closestPoint - point;
    if (direction.GetLengthSq() <= distanceThreshold)
    {
        return true;
    }
    direction.Normalize();

    physx::PxVec3 pxOrigin = physx::PxVec3(point[0], point[1], point[2]);
    physx::PxVec3 pxDirection = physx::PxVec3(direction[0], direction[1], direction[2]);
    const physx::PxTransform pose = physx::PxTransform(physx::PxIdentity);
    const physx::PxReal maxDistance = std::numeric_limits<physx::PxReal>::max();
    physx::PxHitFlags hitFlags =
        physx::PxHitFlag::ePOSITION | physx::PxHitFlag::eMESH_BOTH_SIDES | physx::PxHitFlag::eNORMAL;
    const physx::PxU32 maxRaycastHits = 1;
    physx::PxGeomRaycastHit rayHit;

    physx::PxU32 hitCount =
        physx::PxGeometryQuery::raycast(pxOrigin, pxDirection, regionGeometry, pose, maxDistance, hitFlags,
                                        maxRaycastHits, &rayHit, physx::PxU32(sizeof(physx::PxGeomRaycastHit)));

    if (hitCount == 0)
        return false;

    const float absDot = abs(pxDirection.dot(rayHit.normal));
    if (absDot < degreeThreshold)
    {
        return false;
    }

    if (selfOcclude)
    {
        // Do another raycast on the mesh geometry to ensure the point is not occluded by other part of the mesh
        pxOrigin = physx::PxVec3(closestPoint[0], closestPoint[1], closestPoint[2]);
        hitFlags = physx::PxHitFlag::ePOSITION | physx::PxHitFlag::eMESH_BOTH_SIDES;

        hitCount =
            physx::PxGeometryQuery::raycast(pxOrigin, -pxDirection, meshGeometry, pose, maxDistance, hitFlags,
                                            maxRaycastHits, &rayHit, physx::PxU32(sizeof(physx::PxGeomRaycastHit)));

        if (hitCount == 1)
        {
            // Check if hit another point on the mesh
            vec3f hitPosition{ rayHit.position.x, rayHit.position.y, rayHit.position.z };
            if ((point - hitPosition).GetLengthSq() > distanceThreshold)
            {
                return false;
            }
        }
    }

    return true;
}

bool pointInRegions(const vec3f& point,
                    const physx::PxTriangleMeshGeometry& mesh,
                    const std::vector<physx::PxTriangleMeshGeometry>& regions,
                    const bool selfOcclude)
{
    for (const auto& region : regions)
    {
        if (pointInMeshRegion(point, mesh, region, selfOcclude))
        {
            return true;
        }
    }
    return false;
}

bool pointInVolumes(const vec3f& point, const std::vector<physx::PxTriangleMeshGeometry>& volumes)
{
    const physx::PxVec3 physxPoint(point[0], point[1], point[2]);
    for (const auto& volume : volumes)
    {
        physx::PxU32 nearIndex;
        physx::PxVec3 nearPoint, normal;
        if (omni::genproc::IsPointWithinMesh(physxPoint, volume, nearIndex, nearPoint, normal))
        {
            return true;
        }
    }
    return false;
}

void calculateTangent(size_t index,
                      const std::vector<vec3f>& points,
                      const std::vector<int>& triIndices,
                      const std::vector<vec2f>& triTexCoords,
                      const vec3f& normal,
                      vec3f& tangent,
                      vec3f& binormal)
{
    const int i0 = triIndices[index];
    const int i1 = triIndices[index + 1];
    const int i2 = triIndices[index + 2];

    const auto& p0 = points[i0];
    const auto& p1 = points[i1];
    const auto& p2 = points[i2];
    const auto& w0 = triTexCoords[index];
    const auto& w1 = triTexCoords[index + 1];
    const auto& w2 = triTexCoords[index + 2];

    const vec3f e1 = p1 - p0;
    const vec3f e2 = p2 - p0;
    float x1 = w1[0] - w0[0];
    float x2 = w2[0] - w0[0];
    float y1 = w1[1] - w0[1];
    float y2 = w2[1] - w0[1];

    float r = 1.f / (x1 * y2 - x2 * y1);
    vec3f t = (e1 * y2 - e2 * y1) * r;
    vec3f b = (e2 * x1 - e1 * x2) * r;
    t = t - GfDot(t, normal) * normal;
    t.Normalize();
    b = b - GfDot(b, normal) * normal - GfDot(b, t) * t;
    b.Normalize();
    tangent = t;
    binormal = b;
}

void randomAcrossPoints(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                        const std::vector<int>& triIndices,
                        const size_t desiredCount,
                        std::mt19937_64& random,
                        std::vector<PointSample>& samples)
{
    const size_t triIndicesCount = triIndices.size();
    for (size_t i = 0; i < desiredCount; ++i)
    {
        const size_t index = random() % triIndicesCount;
        PointSample sample;
        sample.type = PointSample::SampleType::eOnPoints;
        sample.index = index;
        sample.point = meshPoints[triIndices[index]];
        samples.push_back(sample);
    }
}

void randomAcrossPointsRegion(const std::vector<vec3f>& meshPoints,
                              const std::vector<int>& triIndices,
                              const std::vector<size_t>& originalLookup,
                              const physx::PxTriangleMeshGeometry& mesh,
                              const std::vector<physx::PxTriangleMeshGeometry>& regions,
                              const size_t desiredCount,
                              std::mt19937_64& random,
                              const bool inside,
                              std::vector<PointSample>& samples)
{
    const size_t triIndicesCount = triIndices.size();
    for (size_t i = 0; i < desiredCount; ++i)
    {
        size_t index = random() % triIndicesCount;
        uint32_t vertex = triIndices[index];
        bool inRegion = pointInRegions(meshPoints[vertex], mesh, regions, true);
        if (inside != inRegion)
        {
            // Find a valid vertex in the triangle
            const size_t startIndex = (index / 3) * 3;
            size_t offset = index - startIndex;
            for (size_t oCnt = 0; oCnt < 2; ++oCnt)
            {
                offset = (offset + 1) % 3;
                index = startIndex + offset;
                vertex = triIndices[index];
                inRegion = pointInRegions(meshPoints[vertex], mesh, regions, true);
                if (inside == inRegion)
                {
                    break;
                }
            }
        }
        PointSample sample;
        sample.type = PointSample::SampleType::eOnPoints;
        sample.index = originalLookup[index];
        sample.point = meshPoints[vertex];
        samples.push_back(sample);
    }
}

void randomTriangleSurfacePoints(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                                 const std::vector<int>& triIndices,
                                 const std::vector<double>& cdf,
                                 const size_t desiredCount,
                                 std::mt19937_64& random,
                                 std::vector<PointSample>& samples)
{
    if (triIndices.size() != (cdf.size() - 1) * 3)
    {
        // Invalid array sizes, so output nothing.
        // FIXME: Report an error!
        return;
    }
    const size_t pointsCount = meshPoints.size();
    const double totalArea = cdf.back();
    constexpr double unitScale = (1.0 / 18446744073709551616.0);
    const double areaScale = totalArea * unitScale;
    for (size_t i = 0; i < desiredCount; ++i)
    {
        const double cdfSample = random() * areaScale;
        const size_t triangle = (std::upper_bound(cdf.begin(), cdf.end() - 1, cdfSample) - cdf.begin()) - 1;
        const int verts[3] = { triIndices[3 * triangle], triIndices[3 * triangle + 1], triIndices[3 * triangle + 2] };
        if (verts[0] < pointsCount || verts[1] < pointsCount || verts[2] < pointsCount)
        {
            float u = random() * float(unitScale);
            float v = random() * float(unitScale);
            validateBarycentric(u, v);
            PointSample sample;
            sample.type = PointSample::SampleType::eOnSurfaces;
            sample.index = 3 * triangle;
            sample.point = sampleTriangle(meshPoints[verts[0]], meshPoints[verts[1]], meshPoints[verts[2]], u, v);
            sample.uv = vec2f{ u, v };
            samples.push_back(sample);
        }
        else
        {
            // Invalid triangle: this shouldn't happen if cdf was initialized by triangleAreaCDF.
            // FIXME: Report an error!
        }
    }
}

void randomTriangleSurfacePointsRegion(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                                       const std::vector<int>& triIndices,
                                       const std::vector<size_t>& originalLookup,
                                       const std::vector<double>& cdf,
                                       const physx::PxTriangleMeshGeometry& mesh,
                                       const std::vector<physx::PxTriangleMeshGeometry>& regions,
                                       const size_t desiredCount,
                                       std::mt19937_64& random,
                                       const bool inside,
                                       std::vector<PointSample>& samples)
{
    if (triIndices.size() != (cdf.size() - 1) * 3)
    {
        // Invalid array sizes, so output nothing.
        // FIXME: Report an error!
        return;
    }
    const size_t pointsCount = meshPoints.size();
    const double totalArea = cdf.back();
    constexpr double unitScale = (1.0 / 18446744073709551616.0);
    const double areaScale = totalArea * unitScale;
    for (size_t i = 0; i < desiredCount; ++i)
    {
        const double cdfSample = random() * areaScale;
        const size_t triangle = (std::upper_bound(cdf.begin(), cdf.end() - 1, cdfSample) - cdf.begin()) - 1;
        const int verts[3] = { triIndices[3 * triangle], triIndices[3 * triangle + 1], triIndices[3 * triangle + 2] };
        if (verts[0] < pointsCount || verts[1] < pointsCount || verts[2] < pointsCount)
        {
            float u = random() * float(unitScale);
            float v = random() * float(unitScale);
            validateBarycentric(u, v);

            const vec3f p0 = meshPoints[verts[0]];
            const vec3f p1 = meshPoints[verts[1]];
            const vec3f p2 = meshPoints[verts[2]];
            vec3f point = sampleTriangle(p0, p1, p2, u, v);
            bool inRegion = pointInRegions(point, mesh, regions, true);
            if (inside != inRegion)
            {
                // Find a valid vertex in the triangle
                size_t offset = random() % 3;
                for (size_t oCnt = 0; oCnt < 3; ++oCnt)
                {
                    inRegion = pointInRegions(meshPoints[verts[offset]], mesh, regions, true);
                    if (inside == inRegion)
                    {
                        break;
                    }
                    offset = (offset + 1) % 3;
                }
                const vec3f validP = meshPoints[verts[offset]];
                inRegion = !inside;
                // approach validP from point
                float distance = (point - validP).GetLength() / 2.f;
                const vec3f direction = (point - validP).GetNormalized();
                constexpr float threshold = 1E-3f;
                while (inside != inRegion && distance > threshold)
                {
                    point = validP + direction * distance;
                    inRegion = pointInRegions(point, mesh, regions, true);
                    distance /= 2.f;
                }
                calculateBarycentric(p0, p1, p2, point, u, v);
            }
            PointSample sample;
            sample.type = PointSample::SampleType::eOnSurfaces;
            sample.index = originalLookup[3 * triangle];
            sample.point = point;
            sample.uv = vec2f{ u, v };
            samples.push_back(sample);
        }
        else
        {
            // Invalid triangle: this shouldn't happen if cdf was initialized by triangleAreaCDF.
            // FIXME: Report an error!
        }
    }
}

float nextRandomFloat(std::mt19937_64& r)
{
    // This is dividing by 2 to the 64, for the range to be in [0,1].
    return r() * (1.0f / 18446744073709551616.0f);
}

static const physx::PxTransform s_identityPose = physx::PxTransform(physx::PxIdentity);

float randomFloatBetween(std::mt19937_64& random, float min, float max)
{
    // This is dividing by 2 to the 64, for the range to be in [0,1].
    float randomFloatNormalized = random() * (1.0f / 18446744073709551616.0f);

    return randomFloatNormalized * (max - min) + min;
};

void randomMeshVolumePoints(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                            const std::vector<int>& triIndices,
                            const physx::PxTriangleMeshGeometry& mesh,
                            const size_t desiredCount,
                            std::mt19937_64& random,
                            std::vector<PointSample>& samples)
{
    physx::PxBounds3 meshBounds;
    physx::PxGeometryQuery::computeGeomBounds(meshBounds, mesh, s_identityPose);
    const physx::PxU32* mapping = mesh.triangleMesh->getTrianglesRemap();
    const size_t targetSamplesCount = samples.size() + desiredCount;
    // this algorithm doesn't necessarily add a point every iteration. at some point we have to give up
    // so just keep going until we exhaust some reasonable number of attempts, otherwise we
    // may loop indefinitely
    const size_t MAX_ATTEMPTS = desiredCount * 100;
    size_t attemptCount = 0;
    while (samples.size() < targetSamplesCount && attemptCount < MAX_ATTEMPTS)
    {
        ++attemptCount;
        float x = randomFloatBetween(random, meshBounds.minimum.x, meshBounds.maximum.x);
        float y = randomFloatBetween(random, meshBounds.minimum.y, meshBounds.maximum.y);
        float z = randomFloatBetween(random, meshBounds.minimum.z, meshBounds.maximum.z);

        physx::PxU32 nearIndex;
        physx::PxVec3 nearPoint, normal;
        if (omni::genproc::IsPointWithinMesh(physx::PxVec3(x, y, z), mesh, nearIndex, nearPoint, normal))
        {
            PointSample sample;
            sample.type = PointSample::SampleType::eInVolume;
            sample.index = mapping[nearIndex] * 3;
            sample.point = vec3f{ x, y, z };

            const uint32_t v0 = triIndices[sample.index];
            const uint32_t v1 = triIndices[sample.index + 1];
            const uint32_t v2 = triIndices[sample.index + 2];
            float u, v;
            calculateBarycentric(
                meshPoints[v0], meshPoints[v1], meshPoints[v2], vec3f{ nearPoint.x, nearPoint.y, nearPoint.z }, u, v);
            sample.uv = vec2f{ u, v };

            samples.push_back(sample);
        }
    }
}

void randomMeshVolumePointsRegion(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                                  const std::vector<int>& triIndices,
                                  const physx::PxTriangleMeshGeometry& mesh,
                                  const std::vector<physx::PxTriangleMeshGeometry>& regions,
                                  const size_t desiredCount,
                                  std::mt19937_64& random,
                                  std::vector<PointSample>& samples)
{
    physx::PxBounds3 meshBounds;
    physx::PxGeometryQuery::computeGeomBounds(meshBounds, mesh, s_identityPose);
    const physx::PxU32* mapping = mesh.triangleMesh->getTrianglesRemap();
    const size_t targetSamplesCount = samples.size() + desiredCount;
    // this algorithm doesn't necessarily add a point every iteration. at some point we have to give up
    // so just keep going until we exhaust some reasonable number of attempts, otherwise we
    // may loop indefinitely
    const size_t MAX_ATTEMPTS = desiredCount * 100;
    size_t attemptCount = 0;
    while (samples.size() < targetSamplesCount && attemptCount < MAX_ATTEMPTS)
    {
        ++attemptCount;
        float x = randomFloatBetween(random, meshBounds.minimum.x, meshBounds.maximum.x);
        float y = randomFloatBetween(random, meshBounds.minimum.y, meshBounds.maximum.y);
        float z = randomFloatBetween(random, meshBounds.minimum.z, meshBounds.maximum.z);

        physx::PxU32 nearIndex;
        physx::PxVec3 nearPoint, normal;
        if (omni::genproc::IsPointWithinMesh(physx::PxVec3{ x, y, z }, mesh, nearIndex, nearPoint, normal) &&
            pointInRegions(vec3f{ x, y, z }, mesh, regions, false))
        {
            PointSample sample;
            sample.type = PointSample::SampleType::eInVolume;
            sample.index = mapping[nearIndex] * 3;
            sample.point = vec3f{ x, y, z };

            const uint32_t v0 = triIndices[sample.index];
            const uint32_t v1 = triIndices[sample.index + 1];
            const uint32_t v2 = triIndices[sample.index + 2];
            float u, v;
            calculateBarycentric(
                meshPoints[v0], meshPoints[v1], meshPoints[v2], vec3f{ nearPoint.x, nearPoint.y, nearPoint.z }, u, v);
            sample.uv = vec2f{ u, v };

            samples.push_back(sample);
        }
    }
}

void generateFromSamples(const std::vector<PointSample>& samples,
                         const std::vector<int>& triIndices,
                         const std::vector<vec3f>& meshPoints,
                         const std::vector<vec3f>& meshNormals,
                         const std::vector<vec2f>& meshTexCoords,
                         std::vector<vec3f>& outputPoints,
                         std::vector<vec3f>* outputNormals,
                         std::vector<vec3f>* outputTangents,
                         std::vector<vec3f>* outputBinormals)
{
    const size_t samplesCount = samples.size();
    for (size_t i = 0; i < samplesCount; ++i)
    {
        const PointSample& sample = samples[i];
        const size_t index = sample.index;
        outputPoints.push_back(sample.point);

        if (!outputNormals && !outputTangents && !outputBinormals)
        {
            continue;
        }

        vec3f normal;
        if (sample.type == PointSample::SampleType::eOnPoints)
        {
            normal = meshNormals[index];
        }
        else
        {
            const auto& n0 = meshNormals[index];
            const auto& n1 = meshNormals[index + 1];
            const auto& n2 = meshNormals[index + 2];
            const auto& uv = sample.uv;
            normal = sampleTriangle(n0, n1, n2, uv[0], uv[1]);
            normal.Normalize();
        }

        if (outputNormals)
        {
            outputNormals->push_back(normal);
        }

        if (outputTangents || outputBinormals)
        {
            vec3f tangent;
            vec3f binormal;
            const size_t tiIndex = (sample.type == PointSample::SampleType::eOnPoints) ? (index / 3 * 3) : index;
            calculateTangent(tiIndex, meshPoints, triIndices, meshTexCoords, normal, tangent, binormal);
            if (outputTangents)
            {
                outputTangents->push_back(tangent);
            }
            if (outputBinormals)
            {
                outputBinormals->push_back(binormal);
            }
        }
    }
}

void filterMeshWithRegions(const std::vector<vec3f>& meshPoints,
                           const std::vector<int>& triIndices,
                           const physx::PxTriangleMeshGeometry& mesh,
                           const std::vector<physx::PxTriangleMeshGeometry>& regions,
                           bool inside,
                           std::vector<int>& filteredTriIndices,
                           std::vector<size_t>& filteredTriLookup)
{
    const size_t triIndicesCount = triIndices.size();
    filteredTriIndices.reserve(triIndicesCount);
    filteredTriLookup.reserve(triIndicesCount);

    // cached region test for the points
    std::unordered_map<uint32_t, bool> cachedInRegions;
    auto regionTest = [&meshPoints, &mesh, &regions, &cachedInRegions](const uint32_t index)
    {
        bool inRegion = false;
        auto iterInRegion = cachedInRegions.find(index);
        if (iterInRegion != cachedInRegions.end())
        {
            inRegion = iterInRegion->second;
        }
        else
        {
            const vec3f& point = meshPoints[index];
            for (const auto& region : regions)
            {
                if (pointInMeshRegion(point, mesh, region, true))
                {
                    inRegion = true;
                    break;
                }
            }
            cachedInRegions[index] = inRegion;
        }
        return inRegion;
    };
    for (size_t i = 0; i < triIndicesCount; i += 3)
    {
        bool valid = false;
        const int pIndices[] = { triIndices[i], triIndices[i + 1], triIndices[i + 2] };
        for (const int index : pIndices)
        {
            if (regionTest(index) == inside)
            {
                valid = true;
                // Add triangle if any of the 3 vertices is valid
                break;
            }
        }
        if (valid)
        {
            filteredTriIndices.insert(filteredTriIndices.end(), pIndices, pIndices + 3);
            filteredTriLookup.push_back(i);
            filteredTriLookup.push_back(i + 1);
            filteredTriLookup.push_back(i + 2);
        }
    }
}

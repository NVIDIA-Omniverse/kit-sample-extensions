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

#include <omni/math/linalg/vec.h>

#include <random>
#include <vector>

namespace physx
{
// Forward declaration to avoid including header
class PxTriangleMeshGeometry;
}


void triangleAreaCDF(const std::vector<omni::math::linalg::vec3f>& points,
                     const std::vector<int>& triIndices,
                     std::vector<double>& cdf);

void validateBarycentric(float& u, float& v);

void calculateBarycentric(const omni::math::linalg::vec3f& a,
                          const omni::math::linalg::vec3f& b,
                          const omni::math::linalg::vec3f& c,
                          const omni::math::linalg::vec3f& p,
                          float& u,
                          float& v);

template <typename T, typename S>
T sampleTriangle(const T& p0, const T& p1, const T& p2, S u, S v)
{
    return p0 + u * (p1 - p0) + v * (p2 - p0);
}

float randomFloatBetween(std::mt19937_64& random, float min, float max);

bool pointInMeshRegion(const omni::math::linalg::vec3f& point,
                       const physx::PxTriangleMeshGeometry& meshGeometry,
                       const physx::PxTriangleMeshGeometry& regionGeometry,
                       const bool selfOcclude);

void calculateTangent(size_t index,
                      const std::vector<omni::math::linalg::vec3f>& points,
                      const std::vector<int>& triIndices,
                      const std::vector<omni::math::linalg::vec2f>& triTexCoords,
                      const omni::math::linalg::vec3f& normal,
                      omni::math::linalg::vec3f& tangent,
                      omni::math::linalg::vec3f& binormal);

// Represent the sample from a mesh: on the points, on the surfaces or inside the volume
struct PointSample
{
    enum class SampleType : uint8_t
    {
        eOnPoints,
        eOnSurfaces,
        eInVolume,
    };

    SampleType type;
    // Index on the mesh triIndices. For on points, it directly represents the sample point. For on surfaces, it
    // is the first index of the triangle where the point is sampled.
    size_t index;
    omni::math::linalg::vec3f point;
    omni::math::linalg::vec2f uv;
};

void randomAcrossPoints(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                        const std::vector<int>& triIndices,
                        const size_t desiredCount,
                        std::mt19937_64& random,
                        std::vector<PointSample>& samples);

void randomAcrossPointsRegion(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                              const std::vector<int>& triIndices,
                              const std::vector<size_t>& originalLookup,
                              const physx::PxTriangleMeshGeometry& mesh,
                              const std::vector<physx::PxTriangleMeshGeometry>& regions,
                              const size_t desiredCount,
                              std::mt19937_64& random,
                              const bool inside,
                              std::vector<PointSample>& samples);

void randomTriangleSurfacePoints(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                                 const std::vector<int>& triIndices,
                                 const std::vector<double>& cdf,
                                 const size_t desiredCount,
                                 std::mt19937_64& random,
                                 std::vector<PointSample>& samples);

void randomTriangleSurfacePointsRegion(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                                       const std::vector<int>& triIndices,
                                       const std::vector<size_t>& originalLookup,
                                       const std::vector<double>& cdf,
                                       const physx::PxTriangleMeshGeometry& mesh,
                                       const std::vector<physx::PxTriangleMeshGeometry>& regions,
                                       const size_t desiredCount,
                                       std::mt19937_64& random,
                                       const bool inside,
                                       std::vector<PointSample>& samples);

void randomMeshVolumePoints(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                            const std::vector<int>& triIndices,
                            const physx::PxTriangleMeshGeometry& mesh,
                            const size_t desiredCount,
                            std::mt19937_64& random,
                            std::vector<PointSample>& samples);

void randomMeshVolumePointsRegion(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                                  const std::vector<int>& triIndices,
                                  const physx::PxTriangleMeshGeometry& mesh,
                                  const std::vector<physx::PxTriangleMeshGeometry>& regions,
                                  const size_t desiredCount,
                                  std::mt19937_64& random,
                                  std::vector<PointSample>& samples);

void generateFromSamples(const std::vector<PointSample>& samples,
                         const std::vector<int>& triIndices,
                         const std::vector<omni::math::linalg::vec3f>& meshPoints,
                         const std::vector<omni::math::linalg::vec3f>& meshNormals,
                         const std::vector<omni::math::linalg::vec2f>& meshTexCoords,
                         std::vector<omni::math::linalg::vec3f>& outputPoints,
                         std::vector<omni::math::linalg::vec3f>* outputNormals,
                         std::vector<omni::math::linalg::vec3f>* outputTangents,
                         std::vector<omni::math::linalg::vec3f>* outputBinormals);

void filterMeshWithRegions(const std::vector<omni::math::linalg::vec3f>& meshPoints,
                           const std::vector<int>& triIndices,
                           const physx::PxTriangleMeshGeometry& mesh,
                           const std::vector<physx::PxTriangleMeshGeometry>& regions,
                           bool inside,
                           std::vector<int>& filteredTriIndices,
                           std::vector<size_t>& filteredTriLookup);

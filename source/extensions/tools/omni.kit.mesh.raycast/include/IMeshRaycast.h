// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once
#include "MeshRaycastTypes.h"

#include <carb/Interface.h>
#include <carb/Types.h>

#include <memory>
#include <vector>

namespace carb
{
namespace events
{
class IEventStream;
}
} // namespace carb

namespace omni
{
namespace meshraycast
{

struct IMeshRaycast
{
    CARB_PLUGIN_INTERFACE("omni::meshraycast::IMeshRaycast", 2, 1)

    /**
     * @brief startup service
     *
     */
    virtual void startup() = 0;

    /**
     * @brief shutdown service
     *
     */
    virtual void shutdown() = 0;

    /**
     * @brief change the BVH refresh rate.
     * @param rate the BvhRefreshRate to set to.
     * @param waitForUpdate if the function should block on an refresh before return.
     */
    virtual void setBvhRefreshRate(BvhRefreshRate rate, bool waitForUpdate) = 0;

    /**
     * @brief set the allowed mesh paths. If the allowed path is not empty, any physics query hit on the non-allowed
     * paths will be skipped.
     * @param paths mesh paths to be allowed in query. if paths is [], all supported meshes are allowed.
     * @param context RaycastContext to set the allowed paths to. If nullptr is provided, it sets to default context.
     * @param count size of the paths. Set to 0 to clear allowed paths and the entire stage will be allowed.
     */
    virtual void setAllowedMeshPaths(const char* const* paths, size_t count, RaycastContext* context = nullptr) = 0;

    /**
     * @brief closestRaycast
     * @param origin the origin position of raycast
     * @param dir the the directory of raycast
     * @param dist the max distance of raycast
     * @param context RaycastContext to be used with this query. If nullptr is provided, it falls back to default
     * context.
     * @return HitResult if not hit, HitResult.meshIndex is -1, otherwise is the index of meshPath in BVH
     */
    virtual HitResult closestRaycast(const carb::Float3& origin,
                                     const carb::Float3& dir,
                                     float dist,
                                     const RaycastContext* context = nullptr) = 0;

    /**
     * @brief closestRaycastBound
     * @param origin the origin position of raycast
     * @param dir the the directory of raycast
     * @param dist the max distance of raycast
     * @param context RaycastContext to be used with this query. If nullptr is provided, it falls back to default
     * context.
     * @return BoundResult if not hit, BoundResult.meshIndex is -1, otherwise is the index of meshPath in BVH
     */
    virtual BoundResult closestRaycastBound(const carb::Float3& origin,
                                            const carb::Float3& dir,
                                            float dist,
                                            const RaycastContext* context = nullptr) = 0;

    /**
     * @brief closestRaycast on single Mesh
     * @param meshPath the mesh prim Path raycast on
     * @param origin the origin position of raycast
     * @param dir the the directory of raycast
     * @param dist the max distance of raycast
     * @param forceCooking set True if mesh points changed after last raycast
     * @return HitResult if hit, HitResult.meshIndex is 0, otherwise is -1
     */
    virtual HitResult closestRaycastMesh(
        std::string& meshPath, const carb::Float3& origin, const carb::Float3& dir, float dist, bool forceCooking) = 0;

    /**
     * @brief casts a sphere with given radius from origin along dir for dist length to test overlapping.
     * @param origin the origin position of spherecast
     * @param dir the the directory of spherecast
     * @param radius the the radius of sphere
     * @param dist the max distance of spherecast
     * @param context RaycastContext to be used with this query. If nullptr is provided, it falls back to default
     * context.
     * @return OverlapResult with array of overlapped mesh indices. Must call @ref freeOverlapResult when done with the
     * result.
     */
    virtual OverlapResult spherecast(const carb::Float3& origin,
                                     const carb::Float3& dir,
                                     float radius,
                                     float dist,
                                     const RaycastContext* context = nullptr) = 0;

    /**
     * @brief frees the memory of an OverlapResult.
     * @param result the OverlapResult to be freed.
     */
    virtual void freeOverlapResult(OverlapResult& result) = 0;

    /**
     * @brief get random samples on mesh surface.
     * @param meshPath the mesh prim Path sample on
     * @param density sample density by unit
     * @param forceCooking set True will recooking the mesh
     * @param positions output sample positions
     * @param normals output sample normals
     */
    virtual void getFloodPoints(const std::string& meshPath,
                                const float density,
                                const bool forceCooking,
                                std::vector<carb::Float3>& positions,
                                std::vector<carb::Float3>& normals) = 0;

    /**
     * @brief does a sphere overlap with given radius at origin to test overlapping vertices.
     * @param origin the center of the sphere.
     * @radius the radius of the sphere.
     * @param context RaycastContext to be used with this query. If nullptr is provided, it falls back to default
     * context.
     * @return OverlapVerticesResult with array of overlapped mesh indices and the overlapped vertex indices within each
     * mesh. Must call @ref freeOverlapVerticesResult when done with the result.
     */
    virtual OverlapVerticesResult overlapVertices(const carb::Float3& origin,
                                                  float radius,
                                                  const RaycastContext* context = nullptr) = 0;

    /**
     * @brief frees the memory of an OverlapVerticesResult.
     * @param result the OverlapVerticesResult to be freed.
     */
    virtual void freeOverlapVerticesResult(OverlapVerticesResult& result) = 0;

    /**
     * @brief gets the mesh path by giving the bound index.
     * @param index the index of the mesh in BVH.
     * @return the mesh path if index is valid. Otherwise an empty string is return.
     */
    virtual const char* getMeshPathFromIndex(int32_t index) = 0;

    /**
     * @brief gets number of paths in BVH.
     * @return number of paths in BVH.
     */
    virtual size_t getMeshPathCount() const = 0;

    /**
     * @brief gets all paths in BVH.
     * @param paths an array of const char* to write to.
     * @param count size of the array. It should be the size of @ref getMeshPathCount
     */
    virtual void getMeshPaths(const char** paths, size_t count) const = 0;

    /**
     * @brief gets the raycast event stream.
     * @return raycast event stream.
     */
    virtual carb::events::IEventStream* getMeshRaycastEventStream() = 0;

    /**
     * @brief gets the vertex local position given its prim path and index.
     * @param meshPth, the mesh which the vertex belongs to.
     * @param vertIndexs, indexes of the vertex.
     * @param[out] positions the local position of the vertexes, of fetched successfully.
     * @return true if all vertex position is valid, false otherwise.
     */
    virtual bool getVertexLocalPositions(const char* meshPath,
                                         const std::vector<size_t>& vertIndexes,
                                         std::vector<carb::Float3>& positions) const = 0;

    /**
     * @beirf creates a RaycastContext to be used in various queries.
     *
     * @return created context.
     */
    virtual RaycastContext* createContext() = 0;

    /**
     * @beirf destroys a previously created RaycastContext.
     * @param context the RaycastContext to be destroyed.
     */
    virtual void destroyContext(RaycastContext* context) = 0;

    /**
     * @brief gets the BVH refresh rate.
     */
    virtual BvhRefreshRate getBvhRefreshRate() const = 0;

    /**
     * @brief sets custom filter on mesh paths.
     * @param fn Function to be called when hit a prim. Hit on this prim will be ignored if fn return False.
     * @param context RaycastContext to set the hit filter to. If nullptr is provided, it sets to default context.
     */
    virtual void setHitFilterFn(const std::function<bool(const char*)>& fn, RaycastContext* context = nullptr) = 0;

    /**
     * @brief sets disallowed mesh paths. Query that hits those meshes will be ignored. It overrides previous disallowed
     * paths.
     * @param paths paths to set to disallowed. Provide an empty array to clear disallowed paths.
     * @param count number of paths in the paths array.
     * @param includeDescendants whether the descendants of the paths should be considered disallowed as well.
     * @param context RaycastContext to set the disallowed paths to. If nullptr is provided, it sets to default context.
     */
    virtual void setDisallowedMeshPaths(const char* const* paths,
                                        size_t count,
                                        bool includeDescendants,
                                        RaycastContext* context = nullptr) = 0;

    /**
     * @brief tessellates a cubic UsdBasisCurves into line segments.
     * @param path path of the UsdBasisCurves prim.
     * @param stepsPerSegment number of line segments for each curve segment.
     * @param fillTangents whether tangents should be returned in the result. If false, only tessellated positions are
     * returned.
     * @return a CurveTessellateResult that contains tessellated positions and optionally tangents in prim's local
     * space. You must call @ref freeCurveTessellateResult afterwards to free the result.
     */
    virtual CurveTessellateResult tessellateCurve(const char* path, size_t stepsPerSegment, bool fillTangents) const = 0;

    /**
     * @brief frees a CurveTessellateResult returned by @ref tessellateCurve.
     * @param result the CurveTessellateResult instance to be freed.
     */
    virtual void freeCurveTessellateResult(CurveTessellateResult& result) const = 0;

    /**
     * @brief samples on a cubic UsdBasisCurves at given segment and t.
     * @param path path of the UsdBasisCurves prim.
     * @param curveIndex the curve index if the UsdBasisCurves contains more than one curve.
     * @param segmentIndex index on the curve of the segment.
     * @param t parametric sample location.
     * @param[out] position sampled position in curve's local space.
     * @param[out] tangent optional sampled tangent in curve's local space.
     */
    virtual bool sampleCurveSegmentAtT(const char* path,
                                       size_t curveIndex,
                                       size_t segmentIndex,
                                       float t,
                                       usdrt::GfVec3f* position,
                                       usdrt::GfVec3f* tangent = nullptr) const = 0;
};
} // namespace meshraycast
} // namespace omni

// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "Utils.h"

#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/Handle.h>
#include <omni/math/linalg/matrix.h>
#include <omni/timeline/ITimeline.h>

#include <limits>

namespace omni
{
namespace genproc
{

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::NameToken;

pxr::UsdPrim getUsdPrimFromNode(const GraphContextObj& context, const NodeObj& nodeObj)
{
    const omni::graph::core::INode* const iNode = nodeObj.iNode;
    const omni::graph::core::IGraphContext* const iContext = context.iContext;

    long int stageId = iContext->getStageId(context);
    auto usdStage = pxr::UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
    const char* primPathStr = iNode->getPrimPath(nodeObj);
    pxr::SdfPath primPath(primPathStr);
    return usdStage->GetPrimAtPath(primPath);
}

bool faceVaryingNormals(const vec3f* points,
                        const size_t pointsCount,
                        const int* faceCounts,
                        const size_t faceCountsCount,
                        const int* faceIndices,
                        const size_t faceIndicesCount,
                        std::vector<vec3f>& normals)
{
    size_t faceVaryingIndex = 0;

    for (size_t face = 0; face < faceCountsCount; ++face)
    {
        int faceVertexCount = faceCounts[face];
        if (faceVertexCount < 0)
        {
            // Can't handle a negative vertex count in a face.
            normals.resize(0);
            return false;
        }
        if (faceVertexCount == 0)
        {
            continue;
        }
        if (faceVaryingIndex + faceVertexCount > faceIndicesCount)
        {
            // Don't access indices out of bounds.
            normals.resize(0);
            return false;
        }

        vec3f faceNormal(0, 0, 1); // need something if we don't have a valid tri
        if (faceVertexCount > 2)
        {
            const int ptIndex0 = faceIndices[faceVaryingIndex];
            if (ptIndex0 >= 0 && ptIndex0 < pointsCount)
            {
                faceNormal = vec3f(0, 0, 0);
                const vec3f& pt0 = points[ptIndex0];
                for (size_t i = 1; i < faceVertexCount - 1; ++i)
                {
                    const int ptIndex1 = faceIndices[faceVaryingIndex + i];
                    const int ptIndex2 = faceIndices[faceVaryingIndex + i + 1];
                    if (ptIndex1 >= 0 && ptIndex1 < pointsCount && ptIndex2 >= 0 && ptIndex2 < pointsCount)
                    {
                        const vec3f& pt1 = points[ptIndex1];
                        const vec3f& pt2 = points[ptIndex2];
                        faceNormal += GfCross(pt1 - pt0, pt2 - pt0);
                    }
                }

                const float length = faceNormal.Normalize();
                if (length == 0)
                {
                    faceNormal = vec3f(0, 0, 1);
                }
            }
        }

        // face varying, so there's a normal for each index
        for (int i = 0; i < faceVertexCount; ++i)
        {
            normals.push_back(faceNormal);
        }

        faceVaryingIndex += faceVertexCount;
    }

    return true;
}

bool primInBundleToTriangles(ConstBundlePrims& prims,
                             const size_t primIndex,
                             std::vector<vec3f>& outputPoints,
                             std::vector<int>& outputIndices,
                             std::vector<vec3f>* outputNormals /*=nullptr*/,
                             std::vector<int>* outputIndicesMapping /*=nullptr*/,
                             std::vector<size_t>* outputFaceToPrim /*=nullptr*/,
                             std::vector<vec2f>* outputTexCoords /*=nullptr*/)
{
    static const auto tMesh = NameToken("Mesh");
    static const auto tPoints = NameToken("points");
    static const auto tCounts = NameToken("faceVertexCounts");
    static const auto tIds = NameToken("faceVertexIndices");
    static const auto tNormals = NameToken("normals");

    static const auto tInterpolation = NameToken("interpolation");
    static const auto tFaceVarying = NameToken("faceVarying");
    static const auto tTexCoords = NameToken("primvars:st");

    std::vector<matrix4d> transforms;
    getPrimTransforms(prims, transforms); // it's overkill to get all the xforms only to use one...

    const size_t primCount = prims.getPrimCount();

    CARB_ASSERT(primIndex < primCount);

    ConstBundlePrim* prim = prims.getConstPrim(primIndex);

    const matrix4d& transform = transforms[primIndex];

    // TODO: support for other prim types e.g. sphere, cube...
    if (prim->type() != tMesh)
    {
        CARB_LOG_ERROR("primInBundleToTriangles -- Input prim %s is of unsupported type %s. Skipping...",
                       prim->path().getText(), prim->type().getText());
        return false;
    }

    BundleAttrib const* pointsAttr = prim->getConstAttr(tPoints);
    BundleAttrib const* faceCountsAttr = prim->getConstAttr(tCounts);
    BundleAttrib const* faceIndicesAttr = prim->getConstAttr(tIds);
    BundleAttrib const* normalsAttr = prim->getConstAttr(tNormals);
    BundleAttrib const* texCoordsAttr = prim->getConstAttr(tTexCoords);

    // no normals is ok, but we need the rest of this stuff
    if (pointsAttr == nullptr || faceCountsAttr == nullptr || faceIndicesAttr == nullptr)
    {
        CARB_LOG_ERROR(
            "primInBundleToTriangles -- Input prim %s is missing the necessary attributes for a mesh. Skipping...",
            prim->path().getText());
        return false;
    }

    const size_t pointsCount = pointsAttr->size();
    const vec3f* const points = pointsAttr->getData<vec3f>();
    const size_t faceCountsCount = faceCountsAttr->size();
    const int* const faceCounts = faceCountsAttr->getData<int>();
    const size_t faceIndicesCount = faceIndicesAttr->size();
    const int* const faceIndices = faceIndicesAttr->getData<int>();
    bool normalsAreFaceVarying = normalsAttr != nullptr && normalsAttr->interpolation() == tFaceVarying;

    std::vector<vec3f> normals;
    if (outputNormals != nullptr)
    {
        if (normalsAttr != nullptr)
        {
            const size_t normalsCount = normalsAttr->size();
            if (normalsCount)
            {
                const vec3f* const normalsData = normalsAttr->getData<vec3f>();
                normals.assign(normalsData, normalsData + normalsCount);
            }
        }

        if (normals.empty())
        {
            faceVaryingNormals(points, pointsCount, faceCounts, faceCountsCount, faceIndices, faceIndicesCount, normals);
            normalsAreFaceVarying = true;
        }


        if (!normalsAreFaceVarying)
        {
            // if we have vertex-varying normals, convert them to face-varying
            std::vector<vec3f> vertexNormals(std::move(normals));

            // one normal per vertex -> one normal per index
            std::transform(faceIndices, faceIndices + faceIndicesCount, std::back_inserter(normals),
                           [&](int id) { return vertexNormals[id]; });

            normalsAreFaceVarying = true;
        }
        CARB_ASSERT(normals.size() == faceIndicesCount);
    }

    std::vector<vec2f> texcoords;
    if (outputTexCoords != nullptr && texCoordsAttr != nullptr)
    {
        bool tcFaceVaring = (texCoordsAttr->interpolation() == tFaceVarying);
        const size_t tcCount = texCoordsAttr->size();
        if (tcCount)
        {
            const vec2f* const tcData = texCoordsAttr->getData<vec2f>();
            texcoords.assign(tcData, tcData + tcCount);
        }

        if (!tcFaceVaring)
        {
            // if we have vertex-varying texcoords, convert them to face-varying
            std::vector<vec2f> vertexCoords(std::move(texcoords));
            std::transform(faceIndices, faceIndices + faceIndicesCount, std::back_inserter(texcoords),
                           [&](int id) { return vertexCoords[id]; });
        }
    }

    outputPoints.resize(pointsCount);
    for (size_t i = 0; i < pointsCount; ++i)
    {
        outputPoints[i] = transform.Transform(points[i]);
    }

    uint32_t trisCount = 0;
    for (size_t i = 0; i < faceCountsCount; ++i)
    {
        trisCount += faceCounts[i] - 2; // number of triangles in a face
    }
    const uint32_t idsCount = trisCount * 3; // number of triangles * 3 = number of ids to be added to the list

    std::vector<int> idsTriangulated(idsCount);

    size_t ii = 0;
    size_t jj = 0;
    for (size_t i = 0; i < faceCountsCount; ++i)
    {
        for (int j = 0; j < faceCounts[i] - 2; ++j)
        {
            // Triangle fan
            idsTriangulated[ii] = faceIndices[jj];
            idsTriangulated[ii + 1] = faceIndices[jj + j + 1];
            idsTriangulated[ii + 2] = faceIndices[jj + j + 2];

            ii += 3;
        }
        jj += faceCounts[i];
    }

    outputIndices.resize(idsCount);
    for (uint32_t i = 0; i < idsTriangulated.size(); ++i)
    {
        outputIndices[i] = idsTriangulated[i];
    }

    if (outputNormals != nullptr)
    {
        std::vector<vec3f> normalsTriangulated(idsCount);
        size_t ii = 0;
        size_t jj = 0;
        for (size_t i = 0; i < faceCountsCount; ++i)
        {
            for (int j = 0; j < faceCounts[i] - 2; ++j)
            {
                // since normals are face-varying, need to duplicate them for each index
                normalsTriangulated[ii] = normals[jj];
                normalsTriangulated[ii + 1] = normals[jj + j + 1];
                normalsTriangulated[ii + 2] = normals[jj + j + 2];

                ii += 3;
            }
            jj += faceCounts[i];
        }

        // since our normals are face-varying, new face-varying normals can just be appended to the list
        CARB_ASSERT(normalsAreFaceVarying);
        CARB_ASSERT(normalsTriangulated.size() == idsTriangulated.size());
        matrix4d normalTransform = transform.GetInverse();
        normalTransform = (normalTransform == matrix4d(.0)) ? transform : normalTransform.GetTranspose();
        std::transform(normalsTriangulated.begin(), normalsTriangulated.end(), std::back_inserter(*outputNormals),
                       [&](vec3f normal)
                       {
                           normal = normalTransform.TransformDir(normal);
                           return normal.GetNormalized();
                       });
    }

    if (outputTexCoords != nullptr && texcoords.size() == faceIndicesCount)
    {
        auto& outputTC = *outputTexCoords;
        outputTC.resize(idsCount);
        size_t ii = 0;
        size_t jj = 0;
        for (size_t i = 0; i < faceCountsCount; ++i)
        {
            for (int j = 0; j < faceCounts[i] - 2; ++j)
            {
                outputTC[ii] = texcoords[jj];
                outputTC[ii + 1] = texcoords[jj + j + 1];
                outputTC[ii + 2] = texcoords[jj + j + 2];

                ii += 3;
            }
            jj += faceCounts[i];
        }
    }

    if (outputIndicesMapping != nullptr)
    {
        std::vector<int>& indicesMapping = *outputIndicesMapping;
        indicesMapping.resize(trisCount);
        size_t ii = 0;
        for (size_t i = 0; i < faceCountsCount; ++i)
        {
            for (int j = 0; j < faceCounts[i] - 2; ++j)
            {
                // triangle ii maps to face i
                // (if all faces are triangles, then ii == i)
                indicesMapping[ii] = (int)i;
                ii++;
            }
        }
    }

    if (outputFaceToPrim != nullptr)
    {
        std::vector<size_t>& faceToPrim = *outputFaceToPrim;
        faceToPrim.resize(trisCount);
        for (size_t i = 0; i < trisCount; i++)
        {
            faceToPrim[i] = primIndex;
        }
    }

    // sanity checks
    // if we have IDs, and those IDs do not exceed the number of points
    if (!outputIndices.empty())
    {
        int maxIndex = *std::max_element(outputIndices.begin(), outputIndices.end());
        CARB_ASSERT(maxIndex < outputPoints.size());
    }

    return true;
}

void primsInBundleToTriangles(ConstBundlePrims& prims,
                              std::vector<vec3f>& outputPoints,
                              std::vector<int>& outputIndices,
                              std::vector<vec3f>* outputNormals /*=nullptr*/,
                              std::vector<int>* outputIndicesMapping /*=nullptr*/,
                              std::vector<size_t>* outputFaceToPrim /*=nullptr*/,
                              std::vector<vec2f>* outputTexCoords /*=nullptr*/,
                              std::vector<size_t>* outputMeshIndices /*=nullptr*/)
{
    static const auto tMesh = NameToken("Mesh");
    static const auto tPoints = NameToken("points");
    static const auto tCounts = NameToken("faceVertexCounts");
    static const auto tIds = NameToken("faceVertexIndices");
    static const auto tNormals = NameToken("normals");

    static const auto tInterpolation = NameToken("interpolation");
    static const auto tFaceVarying = NameToken("faceVarying");
    static const auto tTexCoords = NameToken("primvars:st");

    const size_t primCount = prims.getPrimCount();

    std::vector<matrix4d> transforms;
    getPrimTransforms(prims, transforms);

    size_t totalPointCount = 0;
    size_t totalIdsCount = 0;
    size_t totalTrisCount = 0;

    for (size_t primIndex = 0; primIndex < primCount; primIndex++)
    {
        ConstBundlePrim* prim = prims.getConstPrim(primIndex);

        const matrix4d& transform = transforms[primIndex];

        // TODO: support for other prim types e.g. sphere, cube...
        if (prim->type() != tMesh)
        {
            CARB_LOG_WARN("primsInBundleToTriangles -- Input prim %s is of unsupported type %s. Skipping...",
                          prim->path().getText(), prim->type().getText());
            continue;
        }

        BundleAttrib const* pointsAttr = prim->getConstAttr(tPoints);
        BundleAttrib const* faceCountsAttr = prim->getConstAttr(tCounts);
        BundleAttrib const* faceIndicesAttr = prim->getConstAttr(tIds);
        BundleAttrib const* normalsAttr = prim->getConstAttr(tNormals);
        BundleAttrib const* texCoordsAttr = prim->getConstAttr(tTexCoords);

        // no normals is ok, but we need the rest of this stuff
        if (pointsAttr == nullptr || faceCountsAttr == nullptr || faceIndicesAttr == nullptr)
        {
            CARB_LOG_WARN(
                "primsInBundleToTriangles -- Input prim %s is missing the necessary attributes for a mesh. Skipping...",
                prim->path().getText());
            continue;
        }

        const size_t pointsCount = pointsAttr->size();
        const vec3f* const points = pointsAttr->getData<vec3f>();
        const size_t faceCountsCount = faceCountsAttr->size();
        const int* const faceCounts = faceCountsAttr->getData<int>();
        const size_t faceIndicesCount = faceIndicesAttr->size();
        const int* const faceIndices = faceIndicesAttr->getData<int>();
        bool normalsAreFaceVarying = normalsAttr != nullptr && normalsAttr->interpolation() == tFaceVarying;

        std::vector<vec3f> normals;
        if (outputNormals != nullptr)
        {
            if (normalsAttr != nullptr)
            {
                const size_t normalsCount = normalsAttr->size();
                if (normalsCount)
                {
                    const vec3f* const normalsData = normalsAttr->getData<vec3f>();
                    normals.assign(normalsData, normalsData + normalsCount);
                }
            }

            if (normals.empty())
            {
                faceVaryingNormals(
                    points, pointsCount, faceCounts, faceCountsCount, faceIndices, faceIndicesCount, normals);
                normalsAreFaceVarying = true;
            }


            if (!normalsAreFaceVarying)
            {
                // if we have vertex-varying normals, convert them to face-varying
                std::vector<vec3f> vertexNormals(std::move(normals));

                // one normal per vertex -> one normal per index
                std::transform(faceIndices, faceIndices + faceIndicesCount, std::back_inserter(normals),
                               [&](int id) { return vertexNormals[id]; });

                normalsAreFaceVarying = true;
            }
            CARB_ASSERT(normals.size() == faceIndicesCount);
        }

        std::vector<vec2f> texcoords;
        if (outputTexCoords != nullptr && texCoordsAttr != nullptr)
        {
            bool tcFaceVaring = (texCoordsAttr->interpolation() == tFaceVarying);
            const size_t tcCount = texCoordsAttr->size();
            const vec2f* const tcData = tcCount ? texCoordsAttr->getData<vec2f>() : nullptr;
            if (tcCount && tcData)
            {
                const vec2f* const tcData = texCoordsAttr->getData<vec2f>();
                texcoords.assign(tcData, tcData + tcCount);

                if (tcFaceVaring && (tcCount != faceIndicesCount && tcCount == pointsCount))
                {
                    CARB_LOG_WARN(
                        "primsInBundleToTriangles -- Input prim %s has mismatched texcoord interpolation and size.",
                        prim->path().getText());
                }
                if (!tcFaceVaring || (tcCount != faceIndicesCount && tcCount == pointsCount))
                {
                    // if we have vertex-varying texcoords, convert them to face-varying
                    std::vector<vec2f> vertexCoords(std::move(texcoords));
                    std::transform(faceIndices, faceIndices + faceIndicesCount, std::back_inserter(texcoords),
                                   [&](int id) { return vertexCoords[id]; });
                }
            }
        }

        outputPoints.resize(totalPointCount + pointsCount);
        for (size_t i = 0; i < pointsCount; ++i)
        {
            outputPoints[totalPointCount + i] = transform.Transform(points[i]);
        }

        uint32_t trisCount = 0;
        for (size_t i = 0; i < faceCountsCount; ++i)
        {
            trisCount += faceCounts[i] - 2; // number of triangles in a face
        }
        const uint32_t idsCount = trisCount * 3; // number of triangles * 3 = number of ids to be added to the list

        std::vector<int> idsTriangulated(idsCount);

        size_t ii = 0;
        size_t jj = 0;
        for (size_t i = 0; i < faceCountsCount; ++i)
        {
            for (int j = 0; j < faceCounts[i] - 2; ++j)
            {
                // Triangle fan
                idsTriangulated[ii] = faceIndices[jj];
                idsTriangulated[ii + 1] = faceIndices[jj + j + 1];
                idsTriangulated[ii + 2] = faceIndices[jj + j + 2];

                ii += 3;
            }
            jj += faceCounts[i];
        }

        outputIndices.resize(totalIdsCount + idsCount);
        for (uint32_t i = 0; i < idsTriangulated.size(); ++i)
        {
            outputIndices[totalIdsCount + i] = (int)(totalPointCount + idsTriangulated[i]);
        }

        if (outputMeshIndices != nullptr)
        {
            outputMeshIndices->resize(totalIdsCount + idsCount);
            std::fill(outputMeshIndices->begin() + totalIdsCount, outputMeshIndices->end(), primIndex);
        }

        if (outputNormals != nullptr)
        {
            std::vector<vec3f> normalsTriangulated(idsCount);
            size_t ii = 0;
            size_t jj = 0;
            for (size_t i = 0; i < faceCountsCount; ++i)
            {
                for (int j = 0; j < faceCounts[i] - 2; ++j)
                {
                    // since normals are face-varying, need to duplicate them for each index
                    normalsTriangulated[ii] = normals[jj];
                    normalsTriangulated[ii + 1] = normals[jj + j + 1];
                    normalsTriangulated[ii + 2] = normals[jj + j + 2];

                    ii += 3;
                }
                jj += faceCounts[i];
            }

            // since our normals are face-varying, new face-varying normals can just be appended to the list
            CARB_ASSERT(normalsAreFaceVarying);
            CARB_ASSERT(normalsTriangulated.size() == idsTriangulated.size());
            matrix4d normalTransform = transform.GetInverse();
            normalTransform = (normalTransform == matrix4d(.0)) ? transform : normalTransform.GetTranspose();
            std::transform(normalsTriangulated.begin(), normalsTriangulated.end(), std::back_inserter(*outputNormals),
                           [&](vec3f normal)
                           {
                               normal = normalTransform.TransformDir(normal);
                               return normal.GetNormalized();
                           });
        }

        if (outputTexCoords != nullptr && texcoords.size() == faceIndicesCount)
        {
            auto& outputTC = *outputTexCoords;
            outputTC.resize(totalIdsCount + idsCount);
            size_t ii = totalIdsCount;
            size_t jj = 0;
            for (size_t i = 0; i < faceCountsCount; ++i)
            {
                for (int j = 0; j < faceCounts[i] - 2; ++j)
                {
                    outputTC[ii] = texcoords[jj];
                    outputTC[ii + 1] = texcoords[jj + j + 1];
                    outputTC[ii + 2] = texcoords[jj + j + 2];

                    ii += 3;
                }
                jj += faceCounts[i];
            }
        }

        if (outputIndicesMapping != nullptr)
        {
            std::vector<int>& indicesMapping = *outputIndicesMapping;
            indicesMapping.resize(totalTrisCount + trisCount);
            size_t ii = 0;
            for (size_t i = 0; i < faceCountsCount; ++i)
            {
                for (int j = 0; j < faceCounts[i] - 2; ++j)
                {
                    // triangle ii maps to face i
                    // (if all faces are triangles, then ii == i)
                    indicesMapping[totalTrisCount + ii] = (int)i;
                    ii++;
                }
            }
        }

        if (outputFaceToPrim != nullptr)
        {
            std::vector<size_t>& faceToPrim = *outputFaceToPrim;
            faceToPrim.resize(totalTrisCount + trisCount);
            for (size_t i = 0; i < trisCount; i++)
            {
                faceToPrim[totalTrisCount + i] = primIndex;
            }
        }

        totalPointCount += pointsCount;
        totalIdsCount += idsCount;
        totalTrisCount += trisCount;
    }

    // sanity checks
    // if we have IDs, and those IDs do not exceed the number of points
    if (!outputIndices.empty())
    {
        int maxIndex = *std::max_element(outputIndices.begin(), outputIndices.end());
        CARB_ASSERT(maxIndex < outputPoints.size());
    }
}

void getPrimBoundingSpheres(ConstBundlePrims& prims, std::vector<vec3f>& centers, std::vector<float>& radiiSquared)
{
    static const auto tPoints = NameToken("points");

    const size_t primCount = prims.getPrimCount();

    std::vector<matrix4d> transforms;
    getPrimTransforms(prims, transforms);

    centers.resize(primCount);
    radiiSquared.resize(primCount);

    for (size_t primIndex = 0; primIndex < primCount; primIndex++)
    {
        centers[primIndex] = vec3f(0);
        radiiSquared[primIndex] = 0.f;

        ConstBundlePrim* prim = prims.getConstPrim(primIndex);

        const matrix4d& transform = transforms[primIndex];

        BundleAttrib const* pointsAttr = prim->getConstAttr(tPoints);
        if (pointsAttr == nullptr || pointsAttr->size() == 0)
        {
            CARB_LOG_WARN("getPrimBoundingSphere -- Input prim %s is missing a `points' attribute. Skipping...",
                          prim->path().getText());
            continue;
        }

        const size_t pointsCount = pointsAttr->size();
        if (pointsCount == 0)
        {
            CARB_LOG_WARN("getPrimBoundingSphere -- Input prim %s has no points. Skipping...", prim->path().getText());
            continue;
        }

        const vec3f* const points = pointsAttr->getData<vec3f>();
        if (points == nullptr)
        {
            CARB_LOG_WARN(
                "getPrimBoundingSphere -- Input prim %s has a points attribute of an unsupported type. Skipping...",
                prim->path().getText());
            continue;
        }

        vec3f& centroid = centers[primIndex];
        for (size_t i = 0; i < pointsCount; i++)
        {
            centroid += transform.Transform(points[i]);
        }
        centroid /= (float)pointsCount;

        float& radiusSqr = radiiSquared[primIndex];
        for (size_t i = 0; i < pointsCount; i++)
        {
            radiusSqr = std::max(radiusSqr, (transform.Transform(points[i]) - centroid).GetLengthSq());
        }
    }
}

void getPrimBoundingBoxes(ConstBundlePrims& prims, std::vector<std::pair<vec3f, vec3f>>& extents)
{
    static const auto tPoints = NameToken("points");

    const size_t primCount = prims.getPrimCount();

    std::vector<matrix4d> transforms;
    getPrimTransforms(prims, transforms);

    extents.resize(primCount);

    for (size_t primIndex = 0; primIndex < primCount; primIndex++)
    {
        // default bbox is "infinitely inside-out"
        vec3f minCorner = vec3f(std::numeric_limits<float>::max());
        vec3f maxCorner = vec3f(std::numeric_limits<float>::lowest());
        extents[primIndex] = std::pair<vec3f, vec3f>(minCorner, maxCorner);

        ConstBundlePrim* prim = prims.getConstPrim(primIndex);

        const matrix4d& transform = transforms[primIndex];

        BundleAttrib const* pointsAttr = prim->getConstAttr(tPoints);
        if (pointsAttr == nullptr || pointsAttr->size() == 0)
        {
            CARB_LOG_WARN("getPrimBoundingBox -- Input prim %s is missing a `points' attribute. Skipping...",
                          prim->path().getText());
            continue;
        }

        const size_t pointsCount = pointsAttr->size();
        if (pointsCount == 0)
        {
            CARB_LOG_WARN("getPrimBoundingBox -- Input prim %s has no points. Skipping...", prim->path().getText());
            continue;
        }

        const vec3f* const points = pointsAttr->getData<vec3f>();
        if (points == nullptr)
        {
            CARB_LOG_WARN("getPrimBoundingBox -- Input prim %s has a points attribute of an unsupported type. Skipping...",
                          prim->path().getText());
            continue;
        }

        for (size_t i = 0; i < pointsCount; i++)
        {
            const vec3f worldPoint = transform.Transform(points[i]);
            for (size_t d = 0; d < vec3f::dimension; d++)
            {
                minCorner[d] = std::min(minCorner[d], worldPoint[d]);
                maxCorner[d] = std::max(maxCorner[d], worldPoint[d]);
            }
        }

        extents[primIndex] = std::pair<vec3f, vec3f>(minCorner, maxCorner);
    }
}

void getPrimTransforms(ConstBundlePrims& prims, std::vector<matrix4d>& transforms)
{
    // Originally, we obtained prims in a bundle from the Import node, and that bundle aggregated prim
    // transforms in a collection of common attributes.
    // Later, we switched to prims in a bundle from the ReadPrimsV2 node, and that bundle contains
    // prim transforms as an attribute on the prims themselves.
    //
    // So to maintain the behavior of old setups we'll first check for transforms in the commonAttrs,
    // where Import puts them, then for newer setups to work we'll next check for the transforms
    // on the prims themselves.

    static const auto tTransform = NameToken("transform");
    static const auto tWorldMatrix = NameToken("worldMatrix");

    const size_t primCount = prims.getPrimCount();

    ConstBundlePrim& commonAttrs = prims.getConstCommonAttrs();
    BundleAttrib const* transformAttr = commonAttrs.getConstAttr(tTransform);

    transforms.resize(primCount);

    if (transformAttr != nullptr && transformAttr->size() == primCount)
    {
        const matrix4d* transformData = transformAttr->getData<matrix4d>();
        std::copy(transformData, transformData + primCount, transforms.begin());
    }
    else
    {
        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            ConstBundlePrim* prim = prims.getConstPrim(primIndex);
            transformAttr = prim->getConstAttr(tWorldMatrix);
            if (transformAttr != nullptr)
            {
                const matrix4d* transformData = transformAttr->getData<matrix4d>();
                transforms[primIndex] = *transformData;
            }
            else
            {
                transforms[primIndex].SetIdentity();
            }
        }
    }
}

TimeInfo getTimeInfo(const GraphContextObj& context, ConstBundleHandle inputPrim)
{
    using omni::graph::core::ConstAttributeDataHandle;
    using omni::graph::core::getDataR;

    const auto* iAttributeData = context.iAttributeData;
    const auto* iBundle = context.iBundle;
    const auto* iContext = context.iContext;

    const NameToken* timeAttrNames = getTimeAttrNames();
    ConstAttributeDataHandle timeAttrHandles[s_timeAttrCount];
    iBundle->getAttributesByNameR(timeAttrHandles, context, inputPrim, timeAttrNames, s_timeAttrCount);

    bool playbackEvaluation = false;
    bool hasPlaybackEvaluation = false;
    if (timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_EVALUATION)].isValid())
    {
        Type type = iAttributeData->getType(context, timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_EVALUATION)]);
        if (type == s_BoolType)
        {
            hasPlaybackEvaluation = true;
            playbackEvaluation = *getDataR<bool>(context, timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_EVALUATION)]);
        }
    }
    double playbackStartFrame = 0;
    bool hasPlaybackStartFrame = false;
    if (playbackEvaluation)
    {
        if (timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_START_FRAME)].isValid())
        {
            Type type = iAttributeData->getType(context, timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_START_FRAME)]);
            if (type == s_IntType)
            {
                hasPlaybackStartFrame = true;
                playbackStartFrame =
                    *getDataR<int>(context, timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_START_FRAME)]);
            }
        }
    }
    double playbackEndFrame = -1;
    bool hasPlaybackEndFrame = false;
    if (playbackEvaluation)
    {
        if (timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_END_FRAME)].isValid())
        {
            Type type = iAttributeData->getType(context, timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_END_FRAME)]);
            if (type == s_IntType)
            {
                playbackEndFrame = *getDataR<int>(context, timeAttrHandles[size_t(TimeAttrIndex::PLAYBACK_END_FRAME)]);
                if (playbackEndFrame < 0)
                {
                    playbackEndFrame = -1;
                }
                else
                {
                    hasPlaybackEndFrame = true;
                }
            }
        }
    }

    bool hasTime = false;
    double time = 0;
    if (timeAttrHandles[size_t(TimeAttrIndex::TIME)].isValid())
    {
        Type type = iAttributeData->getType(context, timeAttrHandles[size_t(TimeAttrIndex::TIME)]);
        if (type == s_DoubleType)
        {
            hasTime = true;
            time = *getDataR<double>(context, timeAttrHandles[size_t(TimeAttrIndex::TIME)]);
        }
        else if (type == s_FloatType)
        {
            hasTime = true;
            time = *getDataR<float>(context, timeAttrHandles[size_t(TimeAttrIndex::TIME)]);
        }
    }

    // NOTE: This interface will only be acquired once, due to C++11 "magic statics".
    static omni::timeline::ITimeline* timeline = carb::getFramework()->tryAcquireInterface<omni::timeline::ITimeline>();

    bool hasElapsedTime = false;
    double elapsedTime = 0;
    if (timeAttrHandles[size_t(TimeAttrIndex::ELAPSED_TIME)].isValid() && playbackEvaluation)
    {
        Type type = iAttributeData->getType(context, timeAttrHandles[size_t(TimeAttrIndex::ELAPSED_TIME)]);
        if (type == s_DoubleType)
        {
            hasElapsedTime = true;
            elapsedTime = *getDataR<double>(context, timeAttrHandles[size_t(TimeAttrIndex::ELAPSED_TIME)]);
        }
        else if (type == s_FloatType)
        {
            hasElapsedTime = true;
            elapsedTime = *getDataR<float>(context, timeAttrHandles[size_t(TimeAttrIndex::ELAPSED_TIME)]);
        }
    }

    bool hasUsdTimecode = true;
    double timelineTime = timeline->getCurrentTime();
    double framesPerSecond = timeline->getTimeCodesPerSecond();
    double usdTimecode = timelineTime * framesPerSecond;

    if (!hasElapsedTime)
    {
        if (playbackEvaluation)
        {
            if (framesPerSecond != 0)
            {
                elapsedTime = 1.0 / framesPerSecond;
            }
        }
        else
        {
            elapsedTime = iContext->getElapsedTime(context);
        }
    }

    double prevUsdTimecode = 0;
    if (timeAttrHandles[size_t(TimeAttrIndex::PREV_USD_TIMECODE)].isValid() && playbackEvaluation)
    {
        Type type = iAttributeData->getType(context, timeAttrHandles[size_t(TimeAttrIndex::PREV_USD_TIMECODE)]);
        if (type == s_DoubleType)
        {
            prevUsdTimecode = *getDataR<double>(context, timeAttrHandles[size_t(TimeAttrIndex::PREV_USD_TIMECODE)]);
        }
        else if (type == s_FloatType)
        {
            prevUsdTimecode = *getDataR<float>(context, timeAttrHandles[size_t(TimeAttrIndex::PREV_USD_TIMECODE)]);
        }
    }

    // When in playback evaluation mode we want the nodes to evaluate only on whole frames and be in sync with
    // host app's global FPS rate and global timeline value.
    bool skipEvaluationStep = false;
    if (playbackEvaluation &&
        (usdTimecode <= playbackStartFrame || (hasPlaybackEndFrame && (usdTimecode > playbackEndFrame)) ||
         (int)prevUsdTimecode == (int)usdTimecode))
    {
        skipEvaluationStep = true;
    }

    TimeInfo result;
    result.time = time;
    result.elapsedTime = elapsedTime;
    result.usdTimecode = usdTimecode;
    result.playbackEvaluation = playbackEvaluation;
    result.playbackStartFrame = playbackStartFrame;
    result.playbackEndFrame = playbackEndFrame;
    result.hasTime = hasTime;
    result.hasElapsedTime = hasElapsedTime;
    result.hasUsdTimecode = hasUsdTimecode;
    result.hasPlaybackEvaluation = hasPlaybackEvaluation;
    result.hasPlaybackStartFrame = hasPlaybackStartFrame;
    result.hasPlaybackEndFrame = hasPlaybackEndFrame;
    result.skipEvaluationStep = skipEvaluationStep;
    result.framesPerSecond = framesPerSecond;
    return result;
}

TimeInfo getOrAddTimeInfo(const GraphContextObj& context,
                          BundleHandle outputPrim,
                          bool storeCurrUsdTimeCode,
                          bool storeElapsedTime)
{
    using omni::graph::core::AttributeDataHandle;
    using omni::graph::core::getDataW;

    const auto* iBundle = context.iBundle;

    TimeInfo result = getTimeInfo(context, ConstBundleHandle(outputPrim));

    const NameToken* timeAttrNames = getTimeAttrNames();

    if (!result.hasTime)
    {
        // Time is missing, so add it.
        AttributeDataHandle attrHandle =
            iBundle->addAttribute(context, outputPrim, timeAttrNames[size_t(TimeAttrIndex::TIME)], s_DoubleType);
        if (attrHandle.isValid())
        {
            *getDataW<double>(context, attrHandle) = result.time;
        }
    }

    if (!result.hasElapsedTime && storeElapsedTime)
    {
        AttributeDataHandle attrHandle =
            iBundle->addAttribute(context, outputPrim, timeAttrNames[size_t(TimeAttrIndex::ELAPSED_TIME)], s_DoubleType);
        if (attrHandle.isValid())
        {
            *getDataW<double>(context, attrHandle) = result.elapsedTime;
        }
    }

    if (!result.hasUsdTimecode || storeCurrUsdTimeCode)
    {
        AttributeDataHandle attrHandle =
            iBundle->addAttribute(context, outputPrim, timeAttrNames[size_t(TimeAttrIndex::USD_TIMECODE)], s_DoubleType);
        if (attrHandle.isValid())
        {
            *getDataW<double>(context, attrHandle) = result.usdTimecode;
        }

        if (storeCurrUsdTimeCode)
        {
            AttributeDataHandle attrHandle = iBundle->addAttribute(
                context, outputPrim, timeAttrNames[size_t(TimeAttrIndex::PREV_USD_TIMECODE)], s_DoubleType);
            if (attrHandle.isValid())
            {
                *getDataW<double>(context, attrHandle) = result.usdTimecode;
            }
        }
    }

    return result;
}

} // namespace genproc
} // namespace omni

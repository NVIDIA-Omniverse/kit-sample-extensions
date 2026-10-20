// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include <carb/settings/ISettings.h>

#include <omni/fabric/IFabric.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/scenevisualization/ISceneVisualization.h>

#include <OgnTriMeshVisualizerDatabase.h>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

using namespace omni::renderer;

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

class OgnTriMeshVisualizer
{
public:
    static void primsInBundleToTriangles(ConstBundlePrims& prims,
                                         std::vector<vec3f>& outputPoints,
                                         std::vector<int>& outputIndices,
                                         std::vector<vec3f>* outputNormals /*=nullptr*/,
                                         std::vector<int>* outputIndicesMapping /*=nullptr*/,
                                         std::vector<size_t>* outputFaceToPrim /*=nullptr*/,
                                         const bool verbose = false)
    {
        const size_t primCount = prims.getPrimCount();

        static const auto tMesh = NameToken("Mesh");
        static const auto tPoints = NameToken("points");
        static const auto tCounts = NameToken("faceVertexCounts");
        static const auto tIds = NameToken("faceVertexIndices");
        static const auto tNormals = NameToken("normals");
        static const auto tTransform = NameToken("transform");

        static const auto tInterpolation = NameToken("interpolation");
        static const auto tFaceVarying = NameToken("faceVarying");

        ConstBundlePrim& commonAttrs = prims.getConstCommonAttrs();
        BundleAttrib const* transformAttr = commonAttrs.getConstAttr(tTransform);
        const matrix4d* transformData = nullptr;
        if (transformAttr != nullptr && transformAttr->size() == prims.getPrimCount())
        {
            transformData = transformAttr->getData<matrix4d>();
        }

        size_t totalPointCount = 0;
        size_t totalIdsCount = 0;
        size_t totalTrisCount = 0;

        for (size_t primIndex = 0; primIndex < primCount; primIndex++)
        {
            ConstBundlePrim* prim = prims.getConstPrim(primIndex);

            if (verbose)
                std::cout << "triangulating prim " << prim->path().getText() << std::endl;

            matrix4d transform;
            if (transformData == nullptr)
            {
                transform.SetIdentity();
            }
            else
            {
                transform = transformData[primIndex];
            }

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
            bool normalsAreFaceVarying = (normalsAttr->interpolation() == tFaceVarying);

            if (verbose)
                std::cout << "num faces:" << faceCountsCount << std::endl;

            std::vector<vec3f> normals;
            if (outputNormals != nullptr)
            {
#if 0
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
#endif
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

                std::transform(normalsTriangulated.begin(), normalsTriangulated.end(), std::back_inserter(*outputNormals),
                               [&](vec3f normal)
                               {
                                   normal = transform.TransformDir(normal);
                                   return normal.GetNormalized();
                               });
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

    class NodeVisualizer : public INodeVisualizer::IDrawCallback
    {
    public:
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, const NodeObj& nodeObj) const override
        {

            using omni::math::linalg::vec3f;
            using omni::math::linalg::vec4f;

            const INode* const iNode = nodeObj.iNode;
            GraphObj graphObj = nodeObj.iNode->getGraph(nodeObj);
            GraphContextObj context = graphObj.iGraph->getDefaultGraphContext(graphObj);

            OgnTriMeshVisualizerDatabase db(context, nodeObj);

            if (!db.inputs.active())
                return;

            const int boldFace = db.inputs.boldFace();

            ConstBundlePrims primBundle(db.abi_context(), db.inputs.primBundle().abi_bundleHandle());

            std::vector<int> triFaceToPrimFace;
            std::vector<size_t> triFaceToPrimIndex;
            std::vector<vec3f> points;
            std::vector<int> indices;

            primsInBundleToTriangles(primBundle, points, indices,
                                     nullptr, // normals
                                     &triFaceToPrimFace, &triFaceToPrimIndex, db.inputs.verbose());


            carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
            const float lineWidth = settings->getAsFloat(omni::renderer::kSettingsLineWidth);

            const vec3f color(1.f, 1.f, 1.f);

            const std::vector<vec3f> colors = { vec3f(1, 0, 0), vec3f(0, 1, 0), vec3f(0, 0, 1),
                                                vec3f(1, 1, 0), vec3f(1, 0, 1), vec3f(0, 1, 1) };
            const vec3f colorWhite(1, 1, 1);

            for (size_t f = 0; f < indices.size() / 3; f++)
            {
                const size_t primIndex = triFaceToPrimIndex[f];
                const float width = (boldFace == f ? 10 * lineWidth : lineWidth);
                const vec3f& color = (boldFace == f ? colorWhite : colors[primIndex % colors.size()]);
                const vec3f& a = points[indices[3 * f + 0]];
                const vec3f& b = points[indices[3 * f + 1]];
                const vec3f& c = points[indices[3 * f + 2]];

                std::vector<vec3f> tri = { a, b, c, a };

                drawingInterface.DrawLineStrip(tri.data(), tri.size(), &color, 1, &width, 1);
            }
        }
    };

    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
        INodeVisualizer* nodeVisualizer = carb::getFramework()->tryAcquireInterface<INodeVisualizer>();
        nodeVisualizer->AddNodeDraw(nodeObj, &m_NodeVisualizer);
    }


    static void release(const NodeObj& nodeObj)
    {
        INodeVisualizer* nodeVisualizer = carb::getFramework()->tryAcquireInterface<INodeVisualizer>();
        INodeVisualizer::RegistrationHandle handle = nodeVisualizer->LookupRegistrationHandle(nodeObj, &m_NodeVisualizer);
        nodeVisualizer->RemoveNodeDraw(handle);
    }

    static bool compute(OgnTriMeshVisualizerDatabase& db)
    {
        return true;
    }

    static const NodeVisualizer m_NodeVisualizer;
};

const OgnTriMeshVisualizer::NodeVisualizer OgnTriMeshVisualizer::m_NodeVisualizer;

REGISTER_OGN_NODE()

// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "PhysXUtils.h"
#include "Scatter.h"
#include "Triangulate.h"
#include "Utils.h"

#include <carb/settings/ISettings.h>

#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/scenevisualization/ISceneVisualization.h>
#include <physx/include/cooking/PxCooking.h>
#include <physx/include/geometry/PxGeometryHit.h>
#include <physx/include/geometry/PxMeshQuery.h>
#include <physx/include/geometry/PxTriangle.h>
#include <pxr/base/gf/vec3f.h>

#include <OgnScatterPointsDatabase.h>
#include <algorithm>
#include <limits>
#include <random>

using namespace omni::renderer;
using omni::graph::core::BundleAttrib;
using omni::graph::core::BundlePrim;
using omni::graph::core::BundlePrims;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;
using omni::math::linalg::matrix4d;
using omni::math::linalg::safeCastToOmni;
using omni::math::linalg::safeCastToUSD;
using omni::math::linalg::vec2f;
using omni::math::linalg::vec3f;

using namespace omni::geometry::curves;

using namespace omni::genproc;

static const physx::PxTransform identityPose = physx::PxTransform(physx::PxIdentity);

static inline float nextRandomFloat(std::mt19937_64& r)
{
    // This is dividing by 2 to the 64, for the range to be in [0,1].
    return r() * (1.0f / 18446744073709551616.0f);
}

class OgnScatterPoints
{
public:
    class NodeVisualizer : public INodeVisualizer::IDrawCallback
    {
    public:
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, const NodeObj& nodeObj) const override
        {
            const INode* const iNode = nodeObj.iNode;
            GraphObj graphObj = nodeObj.iNode->getGraph(nodeObj);
            GraphContextObj graphContextObj = graphObj.iGraph->getDefaultGraphContext(graphObj);
            OgnScatterPointsDatabase db(graphContextObj, nodeObj);

            if (db.inputs.debugDraw())
            {
                carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
                const float pointWidth = settings->getAsFloat(omni::renderer::kSettingsPointWidth);
                // FIXME: we're using immediate drawing here, which currently ignores width anyway...
                const float lineWidth = settings->getAsFloat(omni::renderer::kSettingsLineWidth);
                const vec3f color(1.f, 1.f, 1.f);

                BundlePrims outputPrims(graphContextObj, db.outputs.bundle().abi_bundleHandle());
                BundlePrim& outputPrim = outputPrims.getCommonAttrs();

                BundleAttrib* outputPointsAttr = outputPrim.getAttr(db.tokens.points);
                if (outputPointsAttr)
                {
                    const size_t numPoints = outputPointsAttr->size();
                    const vec3f* points = outputPointsAttr->getData<vec3f>();

                    const vec3f* normals = nullptr;
                    BundleAttrib* outputNormalsAttr = outputPrim.getAttr(db.tokens.normals);
                    if (outputNormalsAttr)
                    {
                        normals = outputNormalsAttr->getData<vec3f>();
                    }

                    if (points && normals)
                    {
                        drawingInterface.DrawLines(points, numPoints, ISceneVisualization::DefaultVecConversion(),
                                                   normals, numPoints, ISceneVisualization::DefaultVecConversion(),
                                                   normals, numPoints, ISceneVisualization::ColorFromUnnormalized(),
                                                   &lineWidth, 1);
                    }
                    else if (points)
                    {
                        drawingInterface.DrawPoints(points, numPoints, &color, 1, &lineWidth, 1);
                    }
                }
            }
            if (db.inputs.debugDrawCurveTriangulation())
            {
                carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
                const float lineWidth = settings->getAsFloat(omni::renderer::kSettingsLineWidth);
                static const pxr::GfVec3f triangulationColor(0.f, 0.f, 1.f);
                BundlePrims cachedPrims(graphContextObj, db.state.cachedBundle().abi_bundleHandle());
                for (size_t i = 0; i < cachedPrims.getPrimCount(); ++i)
                {
                    BundlePrim* cachedPrim = cachedPrims.getPrim(i);
                    BundleAttrib* cachedTessPosAttr = cachedPrim->getAttr(db.tokens.curveTessellation);
                    BundleAttrib* cachedTrigDebugIndicesAttr = cachedPrim->getAttr(db.tokens.trigDebugIndices);
                    if (cachedTessPosAttr && cachedTrigDebugIndicesAttr)
                    {
                        const vec3f* pos = cachedTessPosAttr->getData<vec3f>();
                        const uint32_t* indices = cachedTrigDebugIndicesAttr->getData<uint32_t>();
                        const size_t count = cachedTrigDebugIndicesAttr->size();
                        drawingInterface.DrawIndexedLines(pos, indices, count, &triangulationColor, 1, &lineWidth, 1);
                    }
                }
            }
        }
    };
    static const NodeVisualizer m_NodeVisualizer;


    static void initialize(const GraphContextObj& context, const NodeObj& nodeObj)
    {
        INodeVisualizer* nodeVisualizer = carb::getFramework()->tryAcquireInterface<INodeVisualizer>();
        if (nodeVisualizer)
        {
            nodeVisualizer->AddNodeDraw(nodeObj, &m_NodeVisualizer);
        }
    }

    static void release(const NodeObj& nodeObj)
    {
        INodeVisualizer* nodeVisualizer = carb::getFramework()->tryAcquireInterface<INodeVisualizer>();
        if (nodeVisualizer)
        {
            INodeVisualizer::RegistrationHandle handle =
                nodeVisualizer->LookupRegistrationHandle(nodeObj, &m_NodeVisualizer);
            nodeVisualizer->RemoveNodeDraw(handle);
        }
    }

    static void triangulateCurves(OgnScatterPointsDatabase& db, const GraphContextObj& context)
    {
        ConstBundlePrims curvePrims(context, db.inputs.curvesBundle().abi_bundleHandle());
        const int curveTessellation = db.inputs.curveTessellation();
        if (!db.inputs.curvesBundle.changes().hasChanged() && curveTessellation == db.state.prevCurveTessellation())
        {
            return;
        }

        const size_t primCount = curvePrims.getPrimCount();
        ConstBundlePrim& curveCommonAttrs = curvePrims.getCommonAttrs();
        BundleAttrib const* curveTransformAttr = curveCommonAttrs.getConstAttr(db.tokens.transform);
        const matrix4d* curveTransformData = nullptr;
        if (curveTransformAttr != nullptr && curveTransformAttr->size() == primCount)
        {
            curveTransformData = curveTransformAttr->getData<matrix4d>();
        }

        BundlePrims cachedPrims(context, db.state.cachedBundle().abi_bundleHandle());
        cachedPrims.clearContents();
        cachedPrims.addPrims(primCount);

        for (size_t primIndex = 0; primIndex < primCount; ++primIndex)
        {
            ConstBundlePrim* prim = curvePrims.getConstPrim(primIndex);
            matrix4d curveTransform;
            if (curveTransformData == nullptr)
            {
                curveTransform.SetIdentity();
            }
            else
            {
                curveTransform = curveTransformData[primIndex];
            }
            BundleAttrib const* pointsInAttr = prim->getConstAttr(db.tokens.points);
            BundleAttrib const* curveVertexCountsAttr = prim->getConstAttr(db.tokens.curveVertexCounts);
            BundleAttrib const* curveBasisAttr = prim->getConstAttr(db.tokens.basis);
            BundleAttrib const* wrapTypeAttr = prim->getConstAttr(db.tokens.wrap);
            BundleAttrib const* zoneSignAttr = prim->getConstAttr(db.tokens.zoneSign);
            BundlePrim* cachedPrim = cachedPrims.getPrim(primIndex);
            cachedPrim->setPath(prim->path());

            // Note: it's ok if curveVertexCountsAttr does not exist, in the case of a single curve
            if (pointsInAttr == nullptr || curveBasisAttr == nullptr || wrapTypeAttr == nullptr)
            {
                CARB_LOG_WARN_ONCE("Scatter Points: prim does not have basis curve attributes. Skipping...");
                continue;
            }
            const size_t pointsInCount = pointsInAttr->size();
            if (pointsInCount == 0)
            {
                CARB_LOG_WARN_ONCE("Scatter Points: prim has no points. Skipping...");
                continue;
            }
            const vec3f* const points = pointsInAttr->getData<vec3f>();
            const int* curveVertexCounts =
                curveVertexCountsAttr == nullptr ? nullptr : curveVertexCountsAttr->getData<int>();
            const size_t curveCount = curveVertexCounts == nullptr ? 0 : curveVertexCountsAttr->size();
            const auto* basisToken = curveBasisAttr->getData<omni::graph::core::NameToken>();
            const auto* wrapToken = wrapTypeAttr->getData<omni::graph::core::NameToken>();

            if (points == nullptr || basisToken == nullptr || wrapToken == nullptr)
            {
                CARB_LOG_WARN_ONCE("Scatter Points: prim does not have valid basis curve data. Skipping...");
                continue;
            }

            eBasisCurveWrap curveWrapType;
            if (*wrapToken == db.tokens.nonperiodic)
            {
                curveWrapType = eBasisCurveWrap::NonPeriodic;
            }
            else if (*wrapToken == db.tokens.periodic)
            {
                curveWrapType = eBasisCurveWrap::Periodic;
            }
            else if (*wrapToken == db.tokens.pinned)
            {
                curveWrapType = eBasisCurveWrap::Pinned;
            }
            else
            {
                CARB_LOG_ERROR("Scatter Points: invalid curve wrap type.");
                continue;
            }

            eBasisCurveType curveBasisType;

            if (*basisToken == db.tokens.bspline)
            {
                curveBasisType = eBasisCurveType::BSpline;
            }
            else if (*basisToken == db.tokens.bezier)
            {
                curveBasisType = eBasisCurveType::Bezier;
            }
            else if (*basisToken == db.tokens.catmullRom)
            {
                curveBasisType = eBasisCurveType::CatmullRom;
            }
            else
            {
                CARB_LOG_ERROR("Scatter Points: invalid curve basis type.");
                continue;
            }

            const size_t estimatedCount = SplineCurve{ curveWrapType, curveBasisType }.getTessellationPointCount(
                pointsInCount, (size_t)curveTessellation);
            // Flattern tessellated points and triangulated indices arrays
            std::vector<vec3f> tessPositions;
            tessPositions.reserve(estimatedCount);
            std::vector<uint32_t> trigIndices;
            trigIndices.reserve(estimatedCount * 3);

            // iterate at least once, even if no curveVertexCounts attribute has been found.
            for (size_t curveIndex = 0, startIndex = 0, tessStartIndex = 0;
                 curveIndex < (curveCount == 0 ? 1 : curveCount); curveIndex++)
            {
                const size_t count = (curveCount == 0 ? pointsInCount : curveVertexCounts[curveIndex]);
                std::vector<vec3f> controlPoints(count);
                std::transform(points + startIndex, points + startIndex + count, controlPoints.begin(),
                               [&](const vec3f& x) { return curveTransform.Transform(x); });
                startIndex += count;

                SplineCurve curve(curveWrapType, curveBasisType);
                std::vector<vec3f> tessCurvePoints;
                curve.tessellate(controlPoints.data(), controlPoints.size(), tessCurvePoints, curveTessellation);
                const uint32_t tessCount = (uint32_t)tessCurvePoints.size();
                tessPositions.insert(tessPositions.end(), tessCurvePoints.begin(), tessCurvePoints.end());

                std::vector<uint32_t> curveTrig =
                    triangulatePolygon(tessCurvePoints.data(), tessCount, TriangleAreaWeightFunction<float>{});
                // Flattern triangulated indices
                for (size_t tIndex = 0, tCount = curveTrig.size(); tIndex < tCount; ++tIndex)
                {
                    trigIndices.push_back(curveTrig[tIndex] + (uint32_t)tessStartIndex);
                }
                tessStartIndex += tessCount;
            }

            static const Type trigType(BaseDataType::eInt, 1, 1, AttributeRole::eNone);
            const size_t trigIndicesCount = trigIndices.size();
            BundleAttrib* cachedTrigAttr = cachedPrim->addAttr(db.tokens.curveTriangulation, trigType, trigIndicesCount);
            int* cachedTrigIndices = cachedTrigAttr->getData<int>();
            memcpy(cachedTrigIndices, trigIndices.data(), trigIndicesCount * sizeof(int));

            static const Type tessPosType(BaseDataType::eFloat, 3, 1, AttributeRole::eNone);
            const size_t tessPosCount = tessPositions.size();
            BundleAttrib* cachedTessPosAttr = cachedPrim->addAttr(db.tokens.curveTessellation, tessPosType, tessPosCount);
            vec3f* cachedTessPos = cachedTessPosAttr->getData<vec3f>();
            memcpy(cachedTessPos, tessPositions.data(), tessPosCount * sizeof(vec3f));

            static const Type zoneSignType(BaseDataType::eToken, 1, 0, AttributeRole::eNone);
            if (zoneSignAttr)
            {
                BundleAttrib* cachedZoneSignAttr = cachedPrim->addAttr(db.tokens.zoneSign, zoneSignType, 1);
                NameToken* cachedZoneSign = cachedZoneSignAttr->getData<NameToken>();
                *cachedZoneSign = *zoneSignAttr->getData<NameToken>();
            }

            // Cache wire indices for debug display
            {
                static const Type trigDebugIndicesType(BaseDataType::eUInt, 1, 1, AttributeRole::eNone);
                struct Edge
                {
                    uint32_t v0;
                    uint32_t v1;
                    bool operator==(const Edge& other) const
                    {
                        return (v0 == other.v0 && v1 == other.v1);
                    }
                };
                struct EdgeHash
                {
                    std::size_t operator()(Edge const& e) const noexcept
                    {
                        std::size_t h1 = std::hash<uint32_t>{}(e.v0);
                        std::size_t h2 = std::hash<uint32_t>{}(e.v1);
                        return h1 ^ (h2 << 1);
                    }
                };
                std::unordered_set<Edge, EdgeHash> edges;

                std::vector<uint32_t> debugIndices;
                debugIndices.reserve(trigIndicesCount * 2);
                auto addEdge = [&edges, &debugIndices](const uint32_t v0, const uint32_t v1)
                {
                    Edge e;
                    e.v0 = std::min(v0, v1);
                    e.v1 = std::max(v0, v1);
                    if (edges.find(e) == edges.end())
                    {
                        edges.insert(e);
                        debugIndices.push_back(e.v0);
                        debugIndices.push_back(e.v1);
                    }
                };
                for (size_t i = 0; i < trigIndicesCount; i += 3)
                {
                    const uint32_t v0 = trigIndices[i];
                    const uint32_t v1 = trigIndices[i + 1];
                    const uint32_t v2 = trigIndices[i + 2];
                    addEdge(v0, v1);
                    addEdge(v1, v2);
                    addEdge(v2, v0);
                }
                BundleAttrib* cachedDebugAttr =
                    cachedPrim->addAttr(db.tokens.trigDebugIndices, trigDebugIndicesType, debugIndices.size());
                uint32_t* cachedDebug = cachedDebugAttr->getData<uint32_t>();
                memcpy(cachedDebug, debugIndices.data(), debugIndices.size() * sizeof(uint32_t));
            }
        }
    }

    static bool getRegionMeshes(OgnScatterPointsDatabase& db,
                                const GraphContextObj& context,
                                std::vector<UniquePhysXPtr<physx::PxTriangleMesh>>& curveMeshes,
                                std::vector<physx::PxTriangleMeshGeometry>& curveRegions)
    {
        BundlePrims cachedPrims(context, db.state.cachedBundle().abi_bundleHandle());
        const size_t cachedPrimCount = cachedPrims.getPrimCount();
        curveMeshes.reserve(cachedPrimCount);

        // Check zone sign, if any additive curve exists, subtractive curves is not needed
        size_t additiveCount = 0;
        std::vector<bool> zoneSigns(cachedPrimCount);
        for (size_t i = 0; i < cachedPrimCount; ++i)
        {
            BundlePrim* cachedPrim = cachedPrims.getPrim(i);
            BundleAttrib* cachedZoneSignAttr = cachedPrim->getAttr(db.tokens.zoneSign);
            if (cachedZoneSignAttr)
            {
                auto zoneSignToken = *cachedZoneSignAttr->getData<NameToken>();
                // A workaround for the token comparison
                zoneSigns[i] = (std::string(db.tokenToString(zoneSignToken)) == "additive");
            }
            else
            {
                zoneSigns[i] = true;
            }
            if (zoneSigns[i])
            {
                ++additiveCount;
            }
        }

        for (size_t i = 0; i < cachedPrimCount; ++i)
        {
            BundlePrim* cachedPrim = cachedPrims.getPrim(i);
            BundleAttrib* cachedTessPosAttr = cachedPrim->getAttr(db.tokens.curveTessellation);
            BundleAttrib* cachedTrigIndicesAttr = cachedPrim->getAttr(db.tokens.curveTriangulation);
            BundleAttrib* cachedZoneSignAttr = cachedPrim->getAttr(db.tokens.zoneSign);
            if (cachedTessPosAttr && cachedTrigIndicesAttr)
            {
                const vec3f* tessPos = cachedTessPosAttr->getData<vec3f>();
                const size_t posCount = cachedTessPosAttr->size();
                const int* trigIndices = cachedTrigIndicesAttr->getData<int>();
                const size_t indicesCount = cachedTrigIndicesAttr->size();
                curveMeshes.push_back({});
                if (zoneSigns[i])
                {
                    triPointsToPxTriangleMesh(tessPos, posCount, trigIndices, indicesCount, curveMeshes.back());
                    curveRegions.emplace_back(curveMeshes.back().get());
                }
                else if (additiveCount == 0)
                {
                    triPointsToPxTriangleMesh(tessPos, posCount, trigIndices, indicesCount, curveMeshes.back());
                    curveRegions.emplace_back(curveMeshes.back().get());
                }
            }
        }

        return (additiveCount > 0);
    }

    static void updateState(OgnScatterPointsDatabase& db)
    {
        db.state.prevActive() = db.inputs.active();
        db.state.prevExclusive() = db.inputs.exclusive();
        db.state.prevRotations() = db.inputs.rotations();
        db.state.prevRotation() = db.inputs.rotation();
        db.state.prevRotationRandom() = db.inputs.rotationRandom();
        db.state.prevScales() = db.inputs.scales();
        db.state.prevScale() = db.inputs.scale();
        db.state.prevScaleRandom() = db.inputs.scaleRandom();
        db.state.prevObjectIndices() = db.inputs.objectIndices();
        db.state.prevObjectIndex() = db.inputs.objectIndex();
        db.state.prevObjectIndexRandom() = db.inputs.objectIndexRandom();
        db.state.prevNormals() = db.inputs.normals();
        db.state.prevTangents() = db.inputs.tangents();
        db.state.prevBinormals() = db.inputs.binormals();
        db.state.prevPlaybackEvaluation() = db.inputs.playbackEvaluation();
        db.state.prevFilterUsingCamera() = db.inputs.filterUsingCamera();
        db.state.prevUseScatterGeometryAsOcclusionGeometry() = db.inputs.useScatterGeometryAsOcclusionGeometry();
        db.state.prevPlaybackStartFrame() = db.inputs.playbackStartFrame();
        db.state.prevUsdTimecode() = db.inputs.usdTimecode();
        db.state.prevTime() = db.inputs.time();
        db.state.prevRandomSeed() = db.inputs.randomSeed();
        db.state.prevScatterOnSurface() = db.inputs.scatterOnSurface();
        db.state.prevScatterInsideVolume() = db.inputs.scatterInsideVolume();
        db.state.prevScatterAcrossPoints() = db.inputs.scatterAcrossPoints();
        db.state.prevNumDesiredPoints() = db.inputs.numDesiredPoints();
        db.state.prevCurveTessellation() = db.inputs.curveTessellation();
    }

    static bool compute(OgnScatterPointsDatabase& db)
    {
        auto& nodeObj = db.abi_node();
        const GraphContextObj& context = db.abi_context();
        const IGraphContext* const iContext = context.iContext;

        bool inputsChanged =
            db.inputs.active() != db.state.prevActive() || db.inputs.exclusive() != db.state.prevExclusive() ||
            db.inputs.rotations() != db.state.prevRotations() || db.inputs.rotation() != db.state.prevRotation() ||
            db.inputs.rotationRandom() != db.state.prevRotationRandom() || db.inputs.scales() != db.state.prevScales() ||
            db.inputs.scale() != db.state.prevScale() || db.inputs.scaleRandom() != db.state.prevScaleRandom() ||
            db.inputs.objectIndices() != db.state.prevObjectIndices() ||
            db.inputs.objectIndex() != db.state.prevObjectIndex() ||
            db.inputs.objectIndexRandom() != db.state.prevObjectIndexRandom() ||
            db.inputs.normals() != db.state.prevNormals() || db.inputs.tangents() != db.state.prevTangents() ||
            db.inputs.binormals() != db.state.prevBinormals() ||
            db.inputs.playbackEvaluation() != db.state.prevPlaybackEvaluation() ||
            db.inputs.filterUsingCamera() != db.state.prevFilterUsingCamera() ||
            db.inputs.useScatterGeometryAsOcclusionGeometry() != db.state.prevUseScatterGeometryAsOcclusionGeometry() ||
            db.inputs.playbackStartFrame() != db.state.prevPlaybackStartFrame() ||
            db.inputs.usdTimecode() != db.state.prevUsdTimecode() || db.inputs.time() != db.state.prevTime() ||
            db.inputs.randomSeed() != db.state.prevRandomSeed() ||
            db.inputs.scatterOnSurface() != db.state.prevScatterOnSurface() ||
            db.inputs.scatterInsideVolume() != db.state.prevScatterInsideVolume() ||
            db.inputs.scatterAcrossPoints() != db.state.prevScatterAcrossPoints() ||
            db.inputs.numDesiredPoints() != db.state.prevNumDesiredPoints() ||
            db.inputs.curveTessellation() != db.state.prevCurveTessellation();

        ConstBundlePrims inputPrims(context, db.inputs.prim().abi_bundleHandle());
        inputsChanged = inputsChanged || db.inputs.prim.changes().hasChanged();

        ConstBundlePrims occlusionPrim(context, db.inputs.occlusionPrim().abi_bundleHandle());
        if (db.inputs.has_occlusionPrim())
        {
            inputsChanged = inputsChanged || db.inputs.occlusionPrim.changes().hasChanged();
        }

        ConstBundlePrims cameraPrim(context, db.inputs.cameraPrim().abi_bundleHandle());
        if (db.inputs.has_cameraPrim())
        {
            inputsChanged = inputsChanged || db.inputs.cameraPrim.changes().hasChanged();
        }

        ConstBundlePrims curvePrims(context, db.inputs.curvesBundle().abi_bundleHandle());
        if (db.inputs.has_curvesBundle())
        {
            inputsChanged = inputsChanged || db.inputs.curvesBundle.changes().hasChanged();
        }

        if (!inputsChanged)
        {
            return true;
        }

        if (!db.inputs.active())
        {
            // if we bail out, make sure we leave no trace of the previous frame (right?)
            //  (and does this release memory, or keep it reserved?)
            auto& projectedPointsArray = db.outputs.projectedPoints();
            projectedPointsArray.resize(0);

            BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
            outputPrims.clearContents();
            updateState(db);
            return true;
        }

        triangulateCurves(db, context);
        // update dirty track after reading the curve bundles
        updateState(db);

        std::vector<UniquePhysXPtr<physx::PxTriangleMesh>> curveMeshes;
        std::vector<physx::PxTriangleMeshGeometry> curveRegions;
        const bool isAdditiveRegions = getRegionMeshes(db, context, curveMeshes, curveRegions);

        pxr::UsdPrim thisPrim = getUsdPrimFromNode(context, nodeObj);
        if (!thisPrim.IsValid())
        {
            return false;
        }

        std::vector<vec3f> meshPoints;
        std::vector<int> triIndices;
        std::vector<vec3f> meshNormals;
        std::vector<vec2f> meshTexCoords;

        primsInBundleToTriangles(inputPrims, meshPoints, triIndices, &meshNormals, nullptr, nullptr, &meshTexCoords);

        if (meshPoints.size() == 0 || triIndices.size() == 0 || (triIndices.size() % 3) != 0)
        {
            return false;
        }

        if (triIndices.size() != meshNormals.size())
        {
            db.logError(
                "In the OgnScatterPoints node, there is a mismatch between "
                "triangle index count and triangle normal count.");
            return false;
        }

        pxr::UsdGeomCamera usdCamera;
        std::vector<vec3f> occlusionMeshPoints;
        std::vector<int> occlusionTriIndices;
        bool occludeUsingScatterGeometry = db.inputs.useScatterGeometryAsOcclusionGeometry();
        const bool filterUsingCamera = db.inputs.filterUsingCamera();
        const double currentUsdTimecode = db.inputs.usdTimecode();

        if (filterUsingCamera)
        {
            const auto stage = thisPrim.GetStage();
            const pxr::UsdRelationship cameraRelationship = thisPrim.GetRelationship(pxr::TfToken("inputs:cameraPrim"));
            if (cameraRelationship)
            {
                pxr::SdfPathVector cameraPaths;
                cameraRelationship.GetTargets(&cameraPaths);

                if (cameraPaths.size() > 1)
                {
                    CARB_LOG_WARN_ONCE(
                        "OgnScatterPoints: multiple prims connected to camera relationship; only the first Camera prim will be considered.");
                }
                for (size_t i = 0; i < cameraPaths.size(); i++)
                {
                    pxr::UsdPrim cameraPrim = stage->GetPrimAtPath(cameraPaths[0]);

                    if (cameraPrim.IsValid() && cameraPrim.IsA<pxr::UsdGeomCamera>())
                    {
                        usdCamera = pxr::UsdGeomCamera(cameraPrim);
                        break;
                    }
                }
            }
            if (!usdCamera.GetPrim().IsValid())
            {
                db.logError("Filter Using Camera specified, but no valid camera prim provided.");
                return false;
            }

            if (!occludeUsingScatterGeometry)
            {
                const pxr::UsdRelationship relationship = thisPrim.GetRelationship(pxr::TfToken("inputs:prim"));
                pxr::SdfPathVector scatterPaths;
                if (relationship)
                {
                    relationship.GetTargets(&scatterPaths);
                }
                const pxr::UsdRelationship occlusionRelationship =
                    thisPrim.GetRelationship(pxr::TfToken("inputs:occlusionPrim"));
                if (occlusionRelationship)
                {
                    pxr::SdfPathVector occlusionPaths;
                    occlusionRelationship.GetTargets(&occlusionPaths);

                    // Even if the option to use separate scatter and occlusion geometry is set, there's no
                    // reason to make duplicate physx meshes if the prims connected to both inputs are the same.
                    occludeUsingScatterGeometry =
                        occlusionPaths.empty() ||
                        (scatterPaths.size() == occlusionPaths.size() &&
                         std::equal(scatterPaths.begin(), scatterPaths.end(), occlusionPaths.begin()));

                    if (!occludeUsingScatterGeometry)
                    {
                        primsInBundleToTriangles(
                            inputPrims, occlusionMeshPoints, occlusionTriIndices, nullptr, nullptr, nullptr, nullptr);
                    }
                }
            }
        }

        const bool shouldScatterAcrossPoints = db.inputs.scatterAcrossPoints();
        const bool shouldScatterInsideVolume = db.inputs.scatterInsideVolume();
        const bool shouldScatterOnSurface = db.inputs.scatterOnSurface();
        int activeCategories =
            int(shouldScatterAcrossPoints) + int(shouldScatterInsideVolume) + int(shouldScatterOnSurface);

        if (activeCategories == 0)
        {
            return true;
        }

        // random setup
        const auto& pbe = db.inputs.playbackEvaluation();
        const auto& pbsf = db.inputs.playbackStartFrame();

        if (pbe && pbsf > currentUsdTimecode && !filterUsingCamera)
        {
            // Before or at the playback start frame,
            // and we don't need to worry about changes to camera prim
            return true;
        }

        double time = db.inputs.time();
        uint64_t timeBasedSeed = reinterpret_cast<uint64_t&>(time);

        std::mt19937_64 random;
        random.seed(db.inputs.randomSeed() ^ timeBasedSeed);

        UniquePhysXPtr<physx::PxTriangleMesh> triMesh;
        triPointsToPxTriangleMesh(meshPoints.data(), meshPoints.size(), triIndices.data(), triIndices.size(), triMesh);
        physx::PxTriangleMeshGeometry triMeshGeometry = physx::PxTriangleMeshGeometry(triMesh.get());

        // Filtering the triangle mesh with the curve regions helps sampling with too many attempts.
        // If the mesh has large triangles with all vertices outside the regions, this approach could be biased.
        const bool filteredMesh = !curveRegions.empty();
        std::vector<int> filteredTriIndices;
        // Map to the original triIndices
        std::vector<size_t> originalLookup;
        if (filteredMesh)
        {
            filterMeshWithRegions(meshPoints, triIndices, triMeshGeometry, curveRegions, isAdditiveRegions,
                                  filteredTriIndices, originalLookup);
            if (filteredTriIndices.empty())
            {
                CARB_LOG_WARN("OgnScatterPoints::compute: empty filtered mesh, scatter may fail");
            }
        }

        size_t numDesiredPoints = db.inputs.numDesiredPoints();
        std::vector<PointSample> pointSamples;
        pointSamples.reserve(numDesiredPoints);

        size_t numOnPoints = shouldScatterAcrossPoints ? (numDesiredPoints / activeCategories) : 0;
        if (shouldScatterAcrossPoints)
        {
            if (!filteredMesh)
            {
                randomAcrossPoints(meshPoints, triIndices, numOnPoints, random, pointSamples);
            }
            else if (!filteredTriIndices.empty())
            {
                randomAcrossPointsRegion(meshPoints, filteredTriIndices, originalLookup, triMeshGeometry, curveRegions,
                                         numOnPoints, random, isAdditiveRegions, pointSamples);
            }
            numOnPoints = pointSamples.size();
        }

        size_t numOnSurfaces = 0, numInVolume = 0, numShortfall = 0;
        if (shouldScatterOnSurface || shouldScatterInsideVolume)
        {
            std::vector<double> triangleAreas;

            if (shouldScatterOnSurface)
            {
                size_t desiredSurfaceScatteredPoints =
                    shouldScatterInsideVolume ? (numDesiredPoints / activeCategories) : (numDesiredPoints - numOnPoints);
                if (desiredSurfaceScatteredPoints != 0)
                {
                    if (!filteredMesh)
                    {
                        triangleAreaCDF(meshPoints, triIndices, triangleAreas);
                        randomTriangleSurfacePoints(
                            meshPoints, triIndices, triangleAreas, desiredSurfaceScatteredPoints, random, pointSamples);
                    }
                    else if (!filteredTriIndices.empty())
                    {
                        triangleAreaCDF(meshPoints, filteredTriIndices, triangleAreas);
                        randomTriangleSurfacePointsRegion(meshPoints, filteredTriIndices, originalLookup, triangleAreas,
                                                          triMeshGeometry, curveRegions, desiredSurfaceScatteredPoints,
                                                          random, isAdditiveRegions, pointSamples);
                    }
                    numOnSurfaces = pointSamples.size() - numOnPoints;
                }
            }

            if (shouldScatterInsideVolume)
            {
                size_t desiredVolumeScatteredPoints = numDesiredPoints - numOnSurfaces - numOnPoints;
                if (desiredVolumeScatteredPoints)
                {
                    if (!filteredMesh)
                    {
                        randomMeshVolumePoints(meshPoints, triIndices, triMeshGeometry, desiredVolumeScatteredPoints,
                                               random, pointSamples);
                    }
                    else
                    {
                        randomMeshVolumePointsRegion(meshPoints, triIndices, triMeshGeometry, curveRegions,
                                                     desiredVolumeScatteredPoints, random, pointSamples);
                    }
                    numInVolume = pointSamples.size() - numOnPoints - numOnSurfaces;
                }
            }

            // it is possible for an attempt to generate within volume to fail or be incomplete, due to small or
            // zero-volume meshes
            //  so make up the shortfall with surface scattering. volume scattering within a nearly-zero-volume mesh
            //  becomes indistinguishable from surface scattering anyway.
            size_t numShortfall = numDesiredPoints - pointSamples.size();
            if (numShortfall != 0)
            {
                if (!filteredMesh)
                {
                    if (triangleAreas.empty())
                    {
                        triangleAreaCDF(meshPoints, triIndices, triangleAreas);
                    }
                    randomTriangleSurfacePoints(
                        meshPoints, triIndices, triangleAreas, numShortfall, random, pointSamples);
                }
                else if (!filteredTriIndices.empty())
                {
                    if (triangleAreas.empty())
                    {
                        triangleAreaCDF(meshPoints, filteredTriIndices, triangleAreas);
                    }
                    randomTriangleSurfacePointsRegion(meshPoints, filteredTriIndices, originalLookup, triangleAreas,
                                                      triMeshGeometry, curveRegions, numShortfall, random,
                                                      isAdditiveRegions, pointSamples);
                }
            }
        }

        if (filterUsingCamera)
        {
            UniquePhysXPtr<physx::PxTriangleMesh> occlusionTriMesh;
            physx::PxTriangleMeshGeometry occlusionTriMeshGeometry;
            if (!occludeUsingScatterGeometry)
            {
                if (occlusionMeshPoints.size() == 0 || occlusionTriIndices.size() == 0)
                {
                    db.logError("In the OgnScatterPoints node, no occlusion geometry provided");
                    return false;
                }
                triPointsToPxTriangleMesh(occlusionMeshPoints.data(), occlusionMeshPoints.size(),
                                          occlusionTriIndices.data(), occlusionTriIndices.size(), occlusionTriMesh);
                occlusionTriMeshGeometry = physx::PxTriangleMeshGeometry(occlusionTriMesh.get());
            }

            const size_t samplesCount = pointSamples.size();
            std::vector<bool> keep(samplesCount, true);
            size_t keepCount = samplesCount;

            const pxr::GfCamera camera = usdCamera.GetCamera(currentUsdTimecode);
            const pxr::GfFrustum frustum = camera.GetFrustum();

            for (size_t i = 0; i < samplesCount; i++)
            {
                const vec3f sp = pointSamples[i].point;
                const pxr::GfVec3d p(safeCastToUSD(sp));
                // frustum test
                if (!frustum.Intersects(p))
                {
                    // TODO: what's up with the orthographic frustum?
                    keep[i] = false;
                    keepCount--;
                }
                // occlusion test
                else
                {
                    const pxr::GfRay ray = frustum.ComputeRay(p);
                    const vec3f o = safeCastToOmni(pxr::GfVec3f(ray.GetStartPoint()));
                    const vec3f d = safeCastToOmni(pxr::GfVec3f(ray.GetDirection()));
                    const float epsilon = 1e-3f;
                    vec3f hitPoint, hitNormal;
                    const physx::PxReal maxDistance = physx::PxReal((sp - o).GetLength() - epsilon);

                    bool intersects = getMeshIntersection(
                        o, d, occludeUsingScatterGeometry ? triMeshGeometry : occlusionTriMeshGeometry, maxDistance,
                        hitPoint, hitNormal);

                    if (intersects)
                    {
                        keep[i] = false;
                        keepCount--;
                    }
                }
            }

            std::vector<PointSample> keptSamples(keepCount);
            for (size_t i = 0, j = 0; i < samplesCount; i++)
            {
                if (keep[i])
                {
                    keptSamples[j] = pointSamples[i];
                    j++;
                }
            }
            pointSamples = std::move(keptSamples);
        }

        const bool generateNormals = db.inputs.normals();
        const bool generateTangents = db.inputs.tangents();
        const bool generateBinormals = db.inputs.binormals();

        std::vector<vec3f> outputPoints;
        std::vector<vec3f> outputNormals;
        std::vector<vec3f> outputTangents;
        std::vector<vec3f> outputBinormals;

        const size_t numOutputPoints = pointSamples.size();
        outputPoints.reserve(numOutputPoints);
        if (generateNormals)
        {
            outputNormals.reserve(numOutputPoints);
        }
        if (generateTangents)
        {
            outputTangents.reserve(numOutputPoints);
        }
        if (generateBinormals)
        {
            outputBinormals.reserve(numOutputPoints);
        }
        std::vector<vec3f>* outputNormalsPtr = generateNormals ? &outputNormals : nullptr;
        std::vector<vec3f>* outputTangentsPtr = generateTangents ? &outputTangents : nullptr;
        std::vector<vec3f>* outputBinormalsPtr = generateBinormals ? &outputBinormals : nullptr;

        generateFromSamples(pointSamples, triIndices, meshPoints, meshNormals, meshTexCoords, outputPoints,
                            outputNormalsPtr, outputTangentsPtr, outputBinormalsPtr);

        // If we have a camera, output screen-space points, regardless of whether filterUsingCamera is true
        if (usdCamera.GetPrim().IsValid())
        {
            auto& projectedPointsArray = db.outputs.projectedPoints();
            projectedPointsArray.resize(numOutputPoints);
            vec2f* projectedPoints = projectedPointsArray.data();

            const pxr::GfCamera camera = usdCamera.GetCamera(currentUsdTimecode);
            const pxr::GfFrustum frustum = camera.GetFrustum();

            matrix4d xform = safeCastToOmni(frustum.ComputeViewMatrix() * frustum.ComputeProjectionMatrix());

            for (size_t i = 0; i < numOutputPoints; i++)
            {
                const vec3f p = xform.Transform(outputPoints[i]);
                projectedPoints[i] = vec2f(p[0], p[1]);
            }
        }

        const size_t numInputPrims = inputPrims.getPrimCount();
        const bool exclusive = db.inputs.exclusive();
        const size_t numOutputPrims = exclusive ? (numInputPrims) : 0;

        if (exclusive)
        {
            db.outputs.bundle = db.inputs.prim;
            BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
            if (outputPrims.getPrimCount() != numOutputPrims)
            {
                outputPrims.clearContents();
                outputPrims.addPrims(numOutputPrims);
            }
            for (size_t i = 0; i < numOutputPrims; ++i)
            {
                BundlePrim* prim = outputPrims.getPrim(i);
                ConstBundlePrim* inputPrim = inputPrims.getPrim(i);
                prim->copyContentsFrom(*inputPrim);
                prim->setPath(inputPrim->path());
                prim->setType(inputPrim->type());
                prim->bumpDirtyID();
            }
        }

        BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
        BundlePrim& outputPrim = outputPrims.getCommonAttrs();
        // output points attribute
        {
            BundleAttrib* outputPointsAttr = outputPrim.addAttr(
                db.tokens.points, Type(BaseDataType::eFloat, 3, 1, AttributeRole::ePosition), numOutputPoints);
            vec3f* points = outputPointsAttr->getData<vec3f>();
            memcpy(points, outputPoints.data(), numOutputPoints * sizeof(vec3f));
        }

        if (db.inputs.rotations())
        {
            const auto& v3Rot = db.inputs.rotation();
            const auto& v3RotRnd = db.inputs.rotationRandom();

            BundleAttrib* outputRotationsAttr = outputPrim.addAttr(
                db.tokens.rotations, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eNone), numOutputPoints);
            vec3f* rotations = outputRotationsAttr->getData<vec3f>();
            for (size_t i = 0; i < numOutputPoints; ++i)
            {
                // FIXME: This rotation sampling is not uniform, and depends on the rotation order!!!
                float rotationRandomSamples[3];
                rotationRandomSamples[0] = nextRandomFloat(random);
                rotationRandomSamples[1] = nextRandomFloat(random);
                rotationRandomSamples[2] = nextRandomFloat(random);
                rotations[i][0] =
                    v3RotRnd[0] > 0.0001f ? v3Rot[0] + (rotationRandomSamples[0] - 0.5f) * v3RotRnd[0] : v3Rot[0];
                rotations[i][1] =
                    v3RotRnd[1] > 0.0001f ? v3Rot[1] + (rotationRandomSamples[1] - 0.5f) * v3RotRnd[1] : v3Rot[1];
                rotations[i][2] =
                    v3RotRnd[2] > 0.0001f ? v3Rot[2] + (rotationRandomSamples[2] - 0.5f) * v3RotRnd[2] : v3Rot[2];
            }
        }

        if (db.inputs.scales())
        {
            const auto& v3Scl = db.inputs.scale();
            const auto& fSclRnd = db.inputs.scaleRandom();

            BundleAttrib* outputScalesAttr = outputPrim.addAttr(
                db.tokens.scales, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eNone), numOutputPoints);
            vec3f* scales = outputScalesAttr->getData<vec3f>();
            for (size_t i = 0; i < numOutputPoints; ++i)
            {
                float scaleRandomSample = nextRandomFloat(random);
                if (fSclRnd <= -0.001f || fSclRnd >= 0.001f)
                {
                    float scl = (scaleRandomSample - 0.5f) * fSclRnd;
                    scales[i][0] = v3Scl[0] + scl;
                    scales[i][1] = v3Scl[1] + scl;
                    scales[i][2] = v3Scl[2] + scl;
                }
                else
                {
                    scales[i][0] = v3Scl[0];
                    scales[i][1] = v3Scl[1];
                    scales[i][2] = v3Scl[2];
                }
            }
        }

        if (db.inputs.objectIndices())
        {
            auto iObjIdx = db.inputs.objectIndex();
            if (iObjIdx < 0)
                iObjIdx = 0;

            auto iObjIdxRnd = db.inputs.objectIndexRandom();
            if (iObjIdxRnd < 0)
                iObjIdxRnd = 0;

            BundleAttrib* outputObjectIndicesAttr = outputPrim.addAttr(
                db.tokens.objectIndices, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone), numOutputPoints);
            int* objectIndices = outputObjectIndicesAttr->getData<int>();

            for (size_t i = 0; i < numOutputPoints; ++i)
            {
                uint64_t objectIndexSample = random();
                objectIndices[i] = iObjIdxRnd <= 1 ? iObjIdx : objectIndexSample % iObjIdxRnd;
            }
        }

        if (generateNormals)
        {
            BundleAttrib* outputNormalsAttr = outputPrim.addAttr(
                db.tokens.normals, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eNormal), numOutputPoints);
            vec3f* normals = outputNormalsAttr->getData<vec3f>();
            memcpy(normals, outputNormals.data(), numOutputPoints * sizeof(vec3f));
        }

        if (generateTangents)
        {
            BundleAttrib* outputTangentsAttr = outputPrim.addAttr(
                db.tokens.tangents, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eVector), numOutputPoints);
            vec3f* tangents = outputTangentsAttr->getData<vec3f>();
            memcpy(tangents, outputTangents.data(), numOutputPoints * sizeof(vec3f));
        }

        if (generateBinormals)
        {
            BundleAttrib* outputBinormalsAttr = outputPrim.addAttr(
                db.tokens.binormals, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eVector), numOutputPoints);
            vec3f* binormals = outputBinormalsAttr->getData<vec3f>();
            memcpy(binormals, outputBinormals.data(), numOutputPoints * sizeof(vec3f));
        }

        return true;
    }
};

const OgnScatterPoints::NodeVisualizer OgnScatterPoints::m_NodeVisualizer;

REGISTER_OGN_NODE()

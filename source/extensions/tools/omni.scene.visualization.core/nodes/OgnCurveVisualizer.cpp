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

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/scenevisualization/ISceneVisualization.h>

#include <OgnCurveVisualizerDatabase.h>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;
using namespace omni::geometry::curves;

using namespace omni::renderer;

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

#define MIN_TESSELLATION 1
#define MAX_TESSELLATION 200

class OgnCurveVisualizer
{
public:
    class NodeVisualizer : public INodeVisualizer::IDrawCallback
    {
    public:
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, const NodeObj& nodeObj) const override
        {
            using omni::math::linalg::vec3f;
            using omni::math::linalg::vec4f;
            using namespace omni::geometry::curves;

            const INode* const iNode = nodeObj.iNode;
            GraphObj graphObj = nodeObj.iNode->getGraph(nodeObj);
            GraphContextObj context = graphObj.iGraph->getDefaultGraphContext(graphObj);

            OgnCurveVisualizerDatabase db(context, nodeObj);

            if (!db.inputs.active())
                return;

            ConstBundlePrims prims(db.abi_context(), db.inputs.curveBundle().abi_bundleHandle());
            const size_t primCount = prims.getPrimCount();

            ConstBundlePrim& commonAttrs = prims.getConstCommonAttrs();
            BundleAttrib const* transformAttr = commonAttrs.getConstAttr(db.tokens.transform);
            const matrix4d* transformData = nullptr;
            if (transformAttr != nullptr && transformAttr->size() == primCount)
            {
                transformData = transformAttr->getData<matrix4d>();
            }

            carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
            const float lineWidth = settings->getAsFloat(omni::renderer::kSettingsLineWidth);
            const float pointWidth = settings->getAsFloat(omni::renderer::kSettingsPointWidth);

            auto tessellation = db.inputs.tessellation();
            if (tessellation < MIN_TESSELLATION)
                tessellation = MIN_TESSELLATION;
            else if (tessellation > MAX_TESSELLATION)
                tessellation = MAX_TESSELLATION;

            for (size_t primIndex = 0; primIndex < primCount; primIndex++)
            {
                matrix4d transform;
                if (transformData == nullptr)
                {
                    transform.SetIdentity();
                }
                else
                {
                    transform = transformData[primIndex];
                }

                ConstBundlePrim* prim = prims.getConstPrim(primIndex);

                BundleAttrib const* pointsInAttr = prim->getConstAttr(db.tokens.points);
                BundleAttrib const* curveVertexCountsAttr = prim->getConstAttr(db.tokens.curveVertexCounts);
                BundleAttrib const* curveBasisAttr = prim->getConstAttr(db.tokens.basis);
                BundleAttrib const* wrapTypeAttr = prim->getConstAttr(db.tokens.wrap);

                // Note: it's ok if curveVertexCountsAttr does not exist, in the case of a single curve
                if (pointsInAttr == nullptr || curveBasisAttr == nullptr || wrapTypeAttr == nullptr)
                {
                    CARB_LOG_WARN_ONCE("Curve Visualizer: prim does not have basis curve attributes. Skipping...");
                    continue;
                }

                const size_t pointsInCount = pointsInAttr->size();
                if (pointsInCount == 0)
                {
                    CARB_LOG_WARN_ONCE("Curve Visualizer: prim has no points. Skipping...");
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
                    CARB_LOG_WARN_ONCE("Curve Visualizer: prim does not have valid basis curve data. Skipping...");
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
                    CARB_LOG_WARN_ONCE("Curve Visualizer: prim has invalid curve wrap type. Skipping...");
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
                    CARB_LOG_WARN_ONCE("Curve Visualizer: prim has curve basis type. Skipping...");
                    continue;
                }

                const float& scale = db.inputs.scale();

                // iterate at least once, even if no curveVertexCounts attribute has been found.
                for (size_t curveIndex = 0, startIndex = 0; curveIndex < (curveCount == 0 ? 1 : curveCount); curveIndex++)
                {
                    const size_t count = (curveCount == 0 ? pointsInCount : curveVertexCounts[curveIndex]);
                    std::vector<vec3f> controlPoints;
                    std::transform(points + startIndex, points + startIndex + count, std::back_inserter(controlPoints),
                                   [&](const vec3f& x) { return transform.Transform(x); });
                    startIndex += count;

                    SplineCurve curve(curveWrapType, curveBasisType);

                    std::vector<vec3f> tessellatedPositions;
                    std::vector<vec3f> tessellatedTangents;

                    curve.tessellate(controlPoints.data(), controlPoints.size(), tessellatedPositions,
                                     size_t(tessellation), false,
                                     db.inputs.visualizeSampledTangents() ? &tessellatedTangents : nullptr);

                    for (size_t i = 0; i < tessellatedTangents.size(); i++)
                    {
                        tessellatedTangents[i] *= scale;
                    }

                    const vec4f controlColor(1.f, 0.f, 0.f, 1.f);
                    const vec4f curveColor(0.f, 1.f, 0.f, 1.f);
                    const vec4f tangentColor(0.f, 0.f, 1.f, 1.f);

                    if (db.inputs.visualizeCurves())
                    {
                        drawingInterface.DrawLineStrip(
                            tessellatedPositions.data(), tessellatedPositions.size(), &curveColor, 1, &lineWidth, 1);
                    }

                    if (db.inputs.visualizeTangents())
                    {
                        const size_t degree = 3; // XXX
                        if (controlPoints.size() >= degree)
                        {
                            for (size_t j = 0; j < controlPoints.size() - degree; j += degree)
                            {
                                const vec3f& x0 = controlPoints[j];
                                const vec3f v0 = controlPoints[j + 1] - x0;
                                const vec3f& x1 = controlPoints[j + 3];
                                const vec3f v1 = controlPoints[j + 2] - x1;

                                drawingInterface.DrawLines(&x0, 1, &v0, 1, &tangentColor, 1, &lineWidth, 1);
                                drawingInterface.DrawLines(&x1, 1, &v1, 1, &tangentColor, 1, &lineWidth, 1);
                            }
                        }
                    }

                    if (db.inputs.visualizeSampledTangents())
                    {
                        drawingInterface.DrawLines(tessellatedPositions.data(), tessellatedPositions.size(),
                                                   tessellatedTangents.data(), tessellatedTangents.size(),
                                                   &tangentColor, 1, &lineWidth, 1);
                    }

                    if (db.inputs.visualizeControlPoints())
                    {
                        drawingInterface.DrawPoints(
                            controlPoints.data(), controlPoints.size(), &controlColor, 1, &pointWidth, 1);
                    }

                    if (db.inputs.visualizeCurveSegments())
                    {
                        size_t samples = 10;
                        const size_t segmentCount = curve.getSegmentCount(controlPoints.size());
                        std::vector<vec3f> colorOptions = { vec3f(1, 0, 0), vec3f(0, 1, 0), vec3f(0, 0, 1) };
                        for (size_t segmentIndex = 0; segmentIndex < segmentCount; segmentIndex++)
                        {
                            const size_t segmentStartIndex = segmentIndex * curve.m_vstep;
                            std::vector<vec3f> points(samples);
                            for (size_t sample = 0; sample < samples; sample++)
                            {
                                const float u = (float)sample / (float)(samples - 1);
                                points[sample] = curve.evaluateSegment(
                                    controlPoints.data(), controlPoints.size(), segmentStartIndex, u);
                            }
                            const vec3f& color = colorOptions[segmentIndex % colorOptions.size()];
                            drawingInterface.DrawLineStrip(points.data(), points.size(), &color, 1, &lineWidth, 1);
                        }
                    }
                } // for each curve in prim
            } // for each prim in bundle
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

    static bool compute(OgnCurveVisualizerDatabase& db)
    {
        return true;
    }

    static const NodeVisualizer m_NodeVisualizer;
};

const OgnCurveVisualizer::NodeVisualizer OgnCurveVisualizer::m_NodeVisualizer;

REGISTER_OGN_NODE()

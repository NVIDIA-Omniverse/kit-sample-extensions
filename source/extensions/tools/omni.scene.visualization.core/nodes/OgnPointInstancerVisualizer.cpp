// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <carb/settings/ISettings.h>

#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/quat.h>
#include <omni/math/linalg/vec.h>
#include <omni/scenevisualization/ISceneVisualization.h>

#include <OgnPointInstancerVisualizerDatabase.h>

using omni::math::linalg::matrix4d;
using omni::math::linalg::quatd;
using omni::math::linalg::quath;
using omni::math::linalg::vec3d;
using omni::math::linalg::vec3f;

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;

using namespace omni::renderer;

bool boundingBoxIsEmpty(const std::pair<vec3f, vec3f>& bbox)
{
    bool insideOut = false;
    for (size_t d = 0; d < vec3f::dimension; d++)
    {
        if (bbox.first[d] >= bbox.second[d])
            insideOut = true;
    }
    return insideOut;
}

void getPrototypeData(const OgnPointInstancerVisualizerDatabase& db,
                      ConstBundlePrims& prototypePrims,
                      std::vector<matrix4d>& transforms,
                      std::vector<std::pair<vec3f, vec3f>>& bboxes)
{
    const size_t primCount = prototypePrims.getPrimCount();
    ConstBundlePrim& commonAttrs = prototypePrims.getConstCommonAttrs();
    BundleAttrib const* minCornerAttr = commonAttrs.getConstAttr(db.tokens.bboxMinCorner);
    BundleAttrib const* maxCornerAttr = commonAttrs.getConstAttr(db.tokens.bboxMaxCorner);
    BundleAttrib const* transformAttr = commonAttrs.getConstAttr(db.tokens.bboxTransform);
    const vec3d* minCornerData = nullptr;
    const vec3d* maxCornerData = nullptr;
    const matrix4d* transformData = nullptr;

    if (minCornerAttr != nullptr && minCornerAttr->size() == primCount)
    {
        minCornerData = minCornerAttr->getData<vec3d>();
    }
    if (maxCornerAttr != nullptr && maxCornerAttr->size() == primCount)
    {
        maxCornerData = maxCornerAttr->getData<vec3d>();
    }
    if (transformAttr != nullptr && transformAttr->size() == primCount)
    {
        transformData = transformAttr->getData<matrix4d>();
    }

    transforms.resize(primCount);
    bboxes.resize(primCount);

    for (size_t primIndex = 0; primIndex < primCount; primIndex++)
    {
        //// world -> object space transforms
        matrix4d transform;
        if (transformData == nullptr)
        {
            transform.SetIdentity();
        }
        else
        {
            transform = transformData[primIndex];
        }
        transforms[primIndex] = transform;

        //// object-space bounding box
        // default bbox is "infinitely inside-out"
        vec3f minPoint(std::numeric_limits<float>::max());
        vec3f maxPoint(std::numeric_limits<float>::lowest());
        if (minCornerData != nullptr && maxCornerData != nullptr)
        {
            minPoint = vec3f(minCornerData[primIndex]);
            maxPoint = vec3f(maxCornerData[primIndex]);
        }

        bboxes[primIndex] = std::pair<vec3f, vec3f>(minPoint, maxPoint);
    }
}

class OgnPointInstancerVisualizer
{
public:
    class NodeVisualizer : public INodeVisualizer::IDrawCallback
    {
    public:
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, const NodeObj& nodeObj) const override
        {
            const INode* const iNode = nodeObj.iNode;
            GraphObj graphObj = nodeObj.iNode->getGraph(nodeObj);
            GraphContextObj context = graphObj.iGraph->getDefaultGraphContext(graphObj);

            OgnPointInstancerVisualizerDatabase db(context, nodeObj);

            if (!db.inputs.active())
            {
                return;
            }

            carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
            const float lineWidth = settings->getAsFloat(omni::renderer::kSettingsLineWidth);
            const float pointWidth = settings->getAsFloat(omni::renderer::kSettingsPointWidth);

            ConstBundlePrims prims(db.abi_context(), db.inputs.pointInstancerBundle().abi_bundleHandle());
            const size_t primCount = prims.getPrimCount();

            ConstBundlePrims prototypePrims(db.abi_context(), db.inputs.prototypesBundle().abi_bundleHandle());
            const size_t prototypesCount = prototypePrims.getPrimCount();
            const bool hasPrototypes = prototypesCount != 0;

            std::vector<matrix4d> protoTransform;
            std::vector<std::pair<vec3f, vec3f>> protoExtent;
            getPrototypeData(db, prototypePrims, protoTransform, protoExtent);

            ConstBundlePrim& commonAttrs = prims.getConstCommonAttrs();
            BundleAttrib const* transformAttr = commonAttrs.getConstAttr(db.tokens.transform);
            const matrix4d* transformData = nullptr;
            if (transformAttr != nullptr && transformAttr->size() == primCount)
            {
                transformData = transformAttr->getData<matrix4d>();
            }

            const vec3f red(1.f, 0.f, 0.f);
            const vec3f green(0.f, 1.f, 0.f);
            const vec3f blue(0.f, 0.f, 1.f);
            const vec3f orange(1.f, 0.5f, 0.f);
            const vec3f unitX(1, 0, 0);
            const vec3f unitY(0, 1, 0);
            const vec3f unitZ(0, 0, 1);

            std::vector<vec3f> xdir;
            std::vector<vec3f> ydir;
            std::vector<vec3f> zdir;

            const float globalScale = db.inputs.scale();

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

                BundleAttrib const* positionsAttr = prim->getConstAttr(db.tokens.positions);
                BundleAttrib const* orientationsAttr = prim->getConstAttr(db.tokens.orientations);
                BundleAttrib const* scalesAttr = prim->getConstAttr(db.tokens.scales);
                BundleAttrib const* protoIndicesAttr = prim->getConstAttr(db.tokens.protoIndices);

                if (positionsAttr == nullptr || orientationsAttr == nullptr || scalesAttr == nullptr ||
                    protoIndicesAttr == nullptr)
                {
                    CARB_LOG_WARN_ONCE(
                        "PointInstancer Visualizer: prim does not have point instancer attributes. Skipping...");
                    continue;
                }

                const size_t positionsCount = positionsAttr->size();
                if (positionsCount == 0)
                {
                    CARB_LOG_WARN_ONCE("PointInstancer Visualizer: prim has no points. Skipping...");
                    continue;
                }

                const size_t orientationsCount = orientationsAttr->size();
                const size_t scalesCount = scalesAttr->size();
                const size_t protoIndicesCount = protoIndicesAttr->size();

                if (positionsCount != orientationsCount || positionsCount != scalesCount ||
                    positionsCount != protoIndicesCount)
                {
                    CARB_LOG_WARN_ONCE("PointInstancer Visualizer: mismatch in attribute counts. Skipping...");
                    continue;
                }

                const vec3f* const positions = positionsAttr->getData<vec3f>();
                const quath* const orientations = orientationsAttr->getData<quath>();
                const vec3f* const scales = scalesAttr->getData<vec3f>();
                const int* const protoIndices = protoIndicesAttr->getData<int>();

                if (positions == nullptr || orientations == nullptr || scales == nullptr || protoIndices == nullptr)
                {
                    CARB_LOG_WARN_ONCE("PointInstancer Visualizer: unrecognized attribute type. Skipping...");
                    continue;
                }

                xdir.resize(positionsCount);
                ydir.resize(positionsCount);
                zdir.resize(positionsCount);

                for (size_t i = 0; i < positionsCount; i++)
                {
                    matrix4d rotation;
                    rotation.SetRotate(quatd(orientations[i]));
                    matrix4d scale;
                    scale.SetScale(vec3d(globalScale * scales[i]));

                    matrix4d composed = scale * rotation * transform;

                    xdir[i] = composed.TransformDir(unitX);
                    ydir[i] = composed.TransformDir(unitY);
                    zdir[i] = composed.TransformDir(unitZ);
                }

                drawingInterface.DrawLines(positions, positionsCount, xdir.data(), xdir.size(), &red, 1, &lineWidth, 1);
                drawingInterface.DrawLines(positions, positionsCount, ydir.data(), ydir.size(), &green, 1, &lineWidth, 1);
                drawingInterface.DrawLines(positions, positionsCount, zdir.data(), zdir.size(), &blue, 1, &lineWidth, 1);

                if (hasPrototypes)
                {
                    for (size_t i = 0; i < positionsCount; i++)
                    {
                        const int protoIndex = protoIndices[i];
                        if (protoIndex >= prototypesCount)
                            continue;

                        const std::pair<vec3f, vec3f>& bbox = protoExtent[protoIndex];

                        if (boundingBoxIsEmpty(bbox))
                            continue;

                        matrix4d rotation;
                        rotation.SetRotate(quatd(orientations[i]));
                        matrix4d scale;
                        scale.SetScale(vec3d(scales[i]));
                        matrix4d translation;
                        translation.SetTranslate(vec3d(positions[i]));

                        matrix4d composed = scale * rotation * translation; // order??

                        vec3f x000 = bbox.first;
                        vec3f x111 = bbox.second;
                        vec3f x001 = vec3f(x000[0], x000[1], x111[2]);
                        vec3f x010 = vec3f(x000[0], x111[1], x000[2]);
                        vec3f x011 = vec3f(x000[0], x111[1], x111[2]);
                        vec3f x100 = vec3f(x111[0], x000[1], x000[2]);
                        vec3f x101 = vec3f(x111[0], x000[1], x111[2]);
                        vec3f x110 = vec3f(x111[0], x111[1], x000[2]);

                        matrix4d m = protoTransform[protoIndex] * composed;

                        x000 = m.Transform(x000);
                        x001 = m.Transform(x001);
                        x010 = m.Transform(x010);
                        x011 = m.Transform(x011);
                        x100 = m.Transform(x100);
                        x101 = m.Transform(x101);
                        x110 = m.Transform(x110);
                        x111 = m.Transform(x111);

                        std::vector<vec3f> rect0 = { x000, x001, x101, x100, x000 };
                        std::vector<vec3f> rect1 = { x010, x011, x111, x110, x010 };
                        std::vector<vec3f> rect2 = { x000, x010, x110, x100, x000 };
                        std::vector<vec3f> rect3 = { x001, x011, x111, x101, x001 };

                        drawingInterface.DrawLineStrip(rect0.data(), rect0.size(), &orange, 1, &lineWidth, 1);
                        drawingInterface.DrawLineStrip(rect1.data(), rect1.size(), &orange, 1, &lineWidth, 1);
                        drawingInterface.DrawLineStrip(rect2.data(), rect2.size(), &orange, 1, &lineWidth, 1);
                        drawingInterface.DrawLineStrip(rect3.data(), rect3.size(), &orange, 1, &lineWidth, 1);
                    }
                }
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

    static bool compute(OgnPointInstancerVisualizerDatabase& db)
    {
        return true;
    }

    static const NodeVisualizer m_NodeVisualizer;
};

const OgnPointInstancerVisualizer::NodeVisualizer OgnPointInstancerVisualizer::m_NodeVisualizer;

REGISTER_OGN_NODE()

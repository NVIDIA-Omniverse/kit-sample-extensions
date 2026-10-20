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

#include <OgnPointVisualizerDatabase.h>
#include <cstdlib>
#include <unordered_map>

using namespace omni::renderer;

using omni::graph::core::BundleAttrib;
using omni::graph::core::ConstBundlePrim;
using omni::graph::core::ConstBundlePrims;
using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;

class OgnPointVisualizer
{
public:
    class NodeVisualizer : public INodeVisualizer::IDrawCallback
    {
    public:
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, const NodeObj& nodeObj) const override
        {

            // Want some randomness, but the same randomness every Draw
            srand(0);

            const INode* const iNode = nodeObj.iNode;
            GraphObj graphObj = nodeObj.iNode->getGraph(nodeObj);
            GraphContextObj context = graphObj.iGraph->getDefaultGraphContext(graphObj);

            OgnPointVisualizerDatabase db(context, nodeObj);

            if (!db.inputs.active())
                return;

            carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
            const float lineWidth = settings->getAsFloat(omni::renderer::kSettingsLineWidth);

            const float& pointSize = db.inputs.pointSize();
            const float& aimScale = db.inputs.aimScale();
            const auto& pointsIn = db.inputs.points();
            const auto& aimsIn = db.inputs.aims();
            const auto& tagsIn = db.inputs.tags();

            const vec3f color(1.f, 1.f, 1.f);

            if (auto points = pointsIn.get<float[3]>())
            {

                const vec3f point = (const vec3f)(*points);

                drawingInterface.DrawPoints(&point, 1, &color, 1, &pointSize, 1);
                if (auto aims = aimsIn.get<float[3]>())
                {
                    const vec3f aim = (const vec3f)(*aims);
                    const vec3f scaledAim = aimScale * aim;
                    drawingInterface.DrawLines(&point, 1, &scaledAim, 1, &color, 1, &lineWidth, 1);
                }
            }
            else if (auto points = pointsIn.get<float[][3]>())
            {
                const size_t pointsCount = points.size();
                std::vector<vec3f> colors;
                if (auto tags = tagsIn.get<OgnToken[]>())
                {
                    if (tags.size() == pointsCount)
                    {
                        colors.resize(tags.size());
                        std::unordered_map<NameToken, vec3f> tagToColor;
                        for (size_t i = 0; i < tags.size(); i++)
                        {
                            NameToken tag = (*tags)[i];
                            auto iter = tagToColor.find(tag);
                            if (iter == tagToColor.end())
                            {
                                vec3f randomColor(float(rand() % 256) / 255.f, float(rand() % 256) / 255.f,
                                                  float(rand() % 256) / 255.f);
                                tagToColor[tag] = randomColor;
                                colors[i] = randomColor;
                            }
                            else
                            {
                                colors[i] = iter->second;
                            }
                        }
                    }
                }

                if (colors.size() == 0)
                {
                    colors.push_back(color);
                }


                const vec3f* pointsData = (const vec3f*)points->data();
                drawingInterface.DrawPoints(pointsData, pointsCount, colors.data(), colors.size(), &pointSize, 1);

                if (auto aims = aimsIn.get<float[][3]>())
                {
                    if (aims.size() == pointsCount)
                    {
                        const vec3f* aimsData = (const vec3f*)aims->data();
                        std::vector<vec3f> scaledAims;
                        std::transform(aimsData, aimsData + pointsCount, std::back_inserter(scaledAims),
                                       [&](const vec3f& v) { return aimScale * v; });
                        drawingInterface.DrawLines(pointsData, pointsCount, scaledAims.data(), pointsCount,
                                                   colors.data(), colors.size(), &lineWidth, 1);
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

    static bool compute(OgnPointVisualizerDatabase& db)
    {
        return true;
    }

    static const NodeVisualizer m_NodeVisualizer;
};

const OgnPointVisualizer::NodeVisualizer OgnPointVisualizer::m_NodeVisualizer;

REGISTER_OGN_NODE()

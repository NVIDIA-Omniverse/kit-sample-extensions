// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "NodeVisualizerImpl.h"

#include <cstring>

namespace omni
{
namespace renderer
{

void NodeVisualizerImpl::onStartup()
{
    m_InternalState = new InternalState;

    // none of this is safe to do in the constructor/destructor because framework init hasn't completed yet
    StageUpdateBase::Startup();
    m_InternalState->m_SceneVisualization =
        carb::getFramework()->tryAcquireInterface<omni::renderer::ISceneVisualization>();
}

void NodeVisualizerImpl::onShutdown()
{
    CARB_ASSERT(m_InternalState != nullptr);
    CARB_ASSERT(m_InternalState->m_DrawMap.empty());

    carb::getFramework()->releaseInterface(m_InternalState->m_SceneVisualization);
    m_InternalState->m_SceneVisualization = nullptr;
    StageUpdateBase::Shutdown();

    delete m_InternalState;
}

INodeVisualizer::RegistrationHandle NodeVisualizerImpl::AddNodeDraw(const omni::graph::core::NodeObj& nodeObj,
                                                                    const IDrawCallback* drawCallback)
{
    DrawData drawData;
    drawData.nodeObj = nodeObj;
    drawData.drawCallback = drawCallback;

    // hack, OG frequently doesn't fill out nodeContextHandle. fix it up here if needed :(
    if (drawData.nodeObj.nodeContextHandle == omni::graph::core::NodeContextHandle(0))
    {
        const char* primPathText = drawData.nodeObj.iNode->getPrimPath(nodeObj);
        // Kit 111: OmniGraph interns paths itself (TargetPath, same 8-byte id as the former fabric::Path); a Fabric
        // path needs Fabric's IPath interface, which is not loaded with the OVStage usdrt provider.
        const omni::graph::core::TargetPath primPath(primPathText);
        uint64_t pathId = 0;
        static_assert(sizeof(primPath) == sizeof(pathId), "TargetPath is an 8-byte id");
        std::memcpy(&pathId, &primPath, sizeof(pathId));
        drawData.nodeObj.nodeContextHandle = omni::graph::core::NodeContextHandle(pathId);
    }

    RegistrationHandle thisDrawMapHandle = m_InternalState->m_NextDrawMapHandle++;
    m_InternalState->m_DrawMap[thisDrawMapHandle] = drawData;
    return thisDrawMapHandle;
}

void NodeVisualizerImpl::ForceNodeDirty(RegistrationHandle handle)
{
    // this is currently a NOP, nodes are re-evaluated every frame so
    // dirty states are not tracked.
}

const INodeVisualizer::IDrawCallback* NodeVisualizerImpl::RemoveNodeDraw(RegistrationHandle handle)
{
    DrawMap::iterator it = m_InternalState->m_DrawMap.find(handle);
    bool found = (it != m_InternalState->m_DrawMap.end());
    CARB_ASSERT(found);

    const IDrawCallback* drawCallback = nullptr;
    if (found)
    {
        drawCallback = it->second.drawCallback;
        m_InternalState->m_DrawMap.erase(it);
    }

    return drawCallback;
}

INodeVisualizer::RegistrationHandle NodeVisualizerImpl::LookupRegistrationHandle(const omni::graph::core::NodeObj& nodeObj,
                                                                                 const IDrawCallback* drawCallback)
{
    for (DrawMap::value_type val : m_InternalState->m_DrawMap)
    {
        const DrawData& drawData = val.second;

        // we purposely avoid looking at nodeObj.nodeContextHandle, because OG will change it if it can detect that a
        //  a node was moved to a new path vs removed. this is not supported here, and should be caught in RemovePrim,
        //  but for a caller to react we need to be tolerant of a different nodeContextHandle
        if (drawData.nodeObj.iNode == nodeObj.iNode && drawData.nodeObj.nodeHandle == nodeObj.nodeHandle &&
            drawData.drawCallback == drawCallback)
        {
            RegistrationHandle registrationHandle = val.first;
            return registrationHandle;
        }
    }
    return INVALID_REGISTRATION_HANDLE;
}


// StageUpdateBase overrides
// TODO: we should just be able to register for an immediate draw callback, much easier
void NodeVisualizerImpl::Update(float currentTime, float elapsedSecs, const omni::kit::StageUpdateSettings* updateSettings)
{
    for (DrawMap::value_type& val : m_InternalState->m_DrawMap)
    {
        // need to reconstruct the NodeObj
        DrawData& drawData = val.second;
        if (drawData.nodeObj.nodeHandle && drawData.nodeObj.iNode)
        {
            //
            struct DrawNode : ISceneVisualization::IDrawCallback
            {
                DrawNode(DrawData& drawData) : m_DrawDataRef(drawData)
                {
                }
                DrawData& m_DrawDataRef;
                virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface) const override
                {
                    m_DrawDataRef.drawCallback->Draw(drawingInterface, m_DrawDataRef.nodeObj);
                }
            };

            DrawNode drawNode(drawData);
            m_InternalState->m_SceneVisualization->DrawImmediate(drawNode);
        }
    }
}


} // namespace renderer
} // namespace omni

// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include "StageUpdateBase.h"

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/scenevisualization/ISceneVisualization.h>

#include <unordered_map>

namespace omni
{
namespace renderer
{

class NodeVisualizerImpl : public INodeVisualizer, public StageUpdateBase
{
public:
    void onStartup();
    void onShutdown();
    virtual RegistrationHandle AddNodeDraw(const omni::graph::core::NodeObj& nodeObj,
                                           const IDrawCallback* drawCallback) override;
    virtual void ForceNodeDirty(RegistrationHandle handle) override;
    virtual const IDrawCallback* RemoveNodeDraw(RegistrationHandle handle) override;
    virtual RegistrationHandle LookupRegistrationHandle(const omni::graph::core::NodeObj& nodeObj,
                                                        const IDrawCallback* drawCallback) override;
    // StageUpdateBase overrides
    virtual void Update(float currentTime, float elapsedSecs, const omni::kit::StageUpdateSettings* updateSettings) override;

    struct DrawData
    {
        const IDrawCallback* drawCallback = nullptr;
        omni::graph::core::NodeObj nodeObj;
    };
    typedef std::unordered_map<RegistrationHandle, DrawData> DrawMap;

    // same reason as Impl above, need to keep this all
    struct InternalState
    {
        DrawMap m_DrawMap;
        size_t m_NextDrawMapHandle = 1;

        ISceneVisualization* m_SceneVisualization = nullptr;
    };
    InternalState* m_InternalState = nullptr;
};

} // namespace renderer
} // namespace omni

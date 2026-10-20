// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#define CARB_EXPORTS

// clang-format off
#include "UsdPCH.h"
// clang-format on
#include "UsdrtBeforeOmniGraph.h"


#include "NodeVisualizerImpl.h"
#include "PrimVisualizerImpl.h"
#include "SceneDeclutterImpl.h"
#include "SceneVisualizationImpl.h"
#include "StageUpdateBase.h"

#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>
#include <carb/PluginUtils.h>
#include <carb/settings/ISettings.h>

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/graph/core/ComputeGraph.h>
#include <omni/graph/core/OgnHelpers.h>
#include <omni/kit/IApp.h>
#include <omni/kit/IStageUpdate.h>
#include <omni/renderer/IDebugDraw.h>
#include <omni/scenevisualization/ISceneVisualization.h>
#include <omni/usd/Selection.h>
#include <omni/usd/UsdContext.h>

#include <unordered_map>


const struct carb::PluginImplDesc kPluginImpl = { "omni.scene.visualization.core.plugin", "Scene Visualization",
                                                  "NVIDIA", carb::PluginHotReload::eDisabled, "dev" };

DECLARE_OGN_NODES()

namespace omni
{
namespace renderer
{


// one IExt per plugin to rule all of them...or something like that.
class ExtensionImpl final : public omni::ext::IExt
{
public:
    // called by extension framework
    void onStartup(const char*) final
    {
        StartupInterface<ISceneVisualization, SceneVisualizationImpl>();
        StartupInterface<IPrimVisualizer, PrimVisualizerImpl>();
        StartupInterface<INodeVisualizer, NodeVisualizerImpl>();
        StartupInterface<ISceneDeclutter, SceneDeclutterImpl>();

        INITIALIZE_OGN_NODES()
    }

    void onShutdown() final
    {
        RELEASE_OGN_NODES();

        ShutdownInterface<ISceneDeclutter, SceneDeclutterImpl>();
        ShutdownInterface<IPrimVisualizer, PrimVisualizerImpl>();
        ShutdownInterface<INodeVisualizer, NodeVisualizerImpl>();
        ShutdownInterface<ISceneVisualization, SceneVisualizationImpl>();
    }

private:
    template <typename InterfaceType, typename ImplType>
    void StartupInterface()
    {
        InterfaceType* intf = carb::getCachedInterface<InterfaceType>();
        ImplType* impl = static_cast<ImplType*>(intf);
        impl->onStartup();
    }

    template <typename InterfaceType, typename ImplType>
    void ShutdownInterface()
    {
        InterfaceType* intf = carb::getCachedInterface<InterfaceType>();
        ImplType* impl = static_cast<ImplType*>(intf);
        impl->onShutdown();
    }
};

}
}


using namespace omni::renderer;
void fillInterface(SceneVisualizationImpl& iface)
{
}

void fillInterface(PrimVisualizerImpl& iface)
{
}

void fillInterface(NodeVisualizerImpl& iface)
{
}

void fillInterface(SceneDeclutterImpl& iface)
{
}

void fillInterface(ExtensionImpl& iface)
{
}

CARB_PLUGIN_IMPL(kPluginImpl, ExtensionImpl, SceneVisualizationImpl, PrimVisualizerImpl, SceneDeclutterImpl, NodeVisualizerImpl)
CARB_PLUGIN_IMPL_DEPS(omni::kit::IStageUpdate,
                      omni::renderer::IDebugDraw,
                      omni::graph::core::ComputeGraph,
                      carb::dictionary::IDictionary,
                      carb::settings::ISettings)

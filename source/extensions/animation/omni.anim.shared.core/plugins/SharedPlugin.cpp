// Copyright (c) 2020-2023, NVIDIA CORPORATION. All rights reserved.
//
// NVIDIA CORPORATION and its licensors retain all intellectual property
// and proprietary rights in and to this software, related documentation
// and any modifications thereto. Any use, reproduction, disclosure or
// distribution of this software and related documentation without an express
// license agreement from NVIDIA CORPORATION is strictly prohibited.
//

#pragma once

#define CARB_EXPORTS

#include <omni/usd/UsdContextIncludes.h>
#include <carb/PluginUtils.h>
#include <carb/eventdispatcher/IEventDispatcher.h>
#include <carb/logging/Log.h>
#include <omni/usd/UsdContext.h>
#include "StageContext.h"
#include <array>

#include <omni/ext/IExt.h>
#include <omni/graph/core/OgnHelpers.h>

DECLARE_OGN_NODES();
namespace omni::anim::shared::stage
{
namespace { StageContext context; }
StageContext& getStageContext() { return context; }
}


class AnimSharedtExt : public omni::ext::IExt
{
public:
    void onStartup(const char* extId)
    {
        INITIALIZE_OGN_NODES()
        auto* context = omni::usd::UsdContext::getContext();
        auto* events = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
        if (!context || !events) return;
        auto opened = [context](const auto&) {
            try { omni::anim::shared::stage::getStageContext().attach(context->getStage()); }
            catch (const std::exception& error) { CARB_LOG_ERROR("Shared ovstage population failed: %s", error.what()); }
        };
        m_stageEvents = {
            events->observeEvent(carb::RStringKey("omni.anim.shared.core.opened"), carb::eventdispatcher::kDefaultOrder,
                                 context->stageEventName(omni::usd::StageEventType::eOpened), opened),
            events->observeEvent(carb::RStringKey("omni.anim.shared.core.closing"), carb::eventdispatcher::kDefaultOrder,
                                 context->stageEventName(omni::usd::StageEventType::eClosing), [](const auto&) {
                                     omni::anim::shared::stage::getStageContext().detach();
                                 })
        };
        try { omni::anim::shared::stage::getStageContext().attach(context->getStage()); }
        catch (const std::exception& error) { CARB_LOG_ERROR("Shared ovstage population failed: %s", error.what()); }
    }

    void onShutdown()
    {
        RELEASE_OGN_NODES()
        m_stageEvents = {};
        omni::anim::shared::stage::getStageContext().detach();
    }
private:
    std::array<carb::eventdispatcher::ObserverGuard, 2> m_stageEvents;
};

const struct carb::PluginImplDesc kPluginImpl = { "omni.anim.shared.core.plugin",
                                                  "Shared basic codes of animation extension", "NVIDIA",
                                                  carb::PluginHotReload::eEnabled, "dev" };
CARB_PLUGIN_IMPL(kPluginImpl, AnimSharedtExt)
CARB_PLUGIN_IMPL_DEPS(omni::graph::core::IGraphRegistry, carb::eventdispatcher::IEventDispatcher)

void fillInterface(AnimSharedtExt& iface)
{
}

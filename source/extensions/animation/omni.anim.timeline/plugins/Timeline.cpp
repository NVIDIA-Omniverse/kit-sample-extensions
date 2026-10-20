// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

#define CARB_EXPORTS

#include "ITimeline.h"

#include <carb/Framework.h>
#include <carb/PluginUtils.h>
#include <carb/tasking/ITasking.h>

#include <omni/graph/core/OgnHelpers.h>
#include <omni/graph/core/iComputeGraph.h>

#include <IAnimCurve.h>


const struct carb::PluginImplDesc kPluginImpl = { "omni.anim.timeline.plugin", "Timeline Node Extension", "NVIDIA",
                                                  carb::PluginHotReload::eEnabled, "dev" };

CARB_PLUGIN_IMPL(kPluginImpl, omni::anim::ITimeline)
CARB_PLUGIN_IMPL_DEPS(omni::graph::core::IGraphRegistry, carb::tasking::ITasking, omni::anim::IAnimCurve)
DECLARE_OGN_NODES()

// carbonite interface for this plugin (may contain multiple compute nodes)
void fillInterface(omni::anim::ITimeline& iface)
{
    iface = {};
}

CARB_EXPORT void carbOnPluginStartup(){ INITIALIZE_OGN_NODES() }

CARB_EXPORT void carbOnPluginShutdown()
{
    RELEASE_OGN_NODES();
}

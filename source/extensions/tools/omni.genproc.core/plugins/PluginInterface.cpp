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

#include "IGenproc.h"

#include <carb/Framework.h>
#include <carb/PluginUtils.h>
#include <carb/Types.h>
#include <carb/assets/IAssets.h>
#include <carb/datasource/IDataSource.h>
#include <carb/imaging/IImaging.h>

#include <omni/graph/core/OgnHelpers.h>
#include <omni/graph/core/iComputeGraph.h>
#include <omni/ramp/IRamp.h>


const struct carb::PluginImplDesc pluginDesc = { "omni.genproc.core.plugin", "Gen Proc.", "NVIDIA",
                                                 carb::PluginHotReload::eEnabled, "dev" };

CARB_PLUGIN_IMPL(pluginDesc, omni::genproc::IGenproc)
CARB_PLUGIN_IMPL_DEPS(carb::assets::IAssets,
                      carb::datasource::IDataSource,
                      carb::imaging::IImaging,
                      omni::graph::core::IGraphRegistry,
                      omni::ramp::IRamp)
DECLARE_OGN_NODES()

void fillInterface(omni::genproc::IGenproc& iface)
{
    iface = {};
}

// compute node plugin interface defined
using omni::graph::core::IGraphRegistry;
using omni::graph::core::INodeType;

// TODO: Remove all of these, and their corresponding calls to registerNodeType and unregisterNodeType below
//       as soon as the nodes are converted to the .ogn format.

CARB_EXPORT void carbOnPluginStartup(){ INITIALIZE_OGN_NODES() }

CARB_EXPORT void carbOnPluginShutdown()
{
    RELEASE_OGN_NODES()
}

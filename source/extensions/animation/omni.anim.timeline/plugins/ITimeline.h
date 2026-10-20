// SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <carb/Interface.h>

namespace omni
{
namespace anim
{

/**
 * Minimal interface.
 *
 * It doesn't have any functions, but just implementing it and acquiring will load your plugin, trigger call of
 * carbOnPluginStartup() and carbOnPluginShutdown() methods and allow you to use other Carbonite plugins. That by itself
 * can get you quite far and useful as basic building block for Kit extensions. One can define their own interface with
 * own python python bindings when needed and abandon that one.
 */
struct ITimeline
{
    CARB_PLUGIN_INTERFACE("omni::anim::timeline", 1, 0);
};
}
}

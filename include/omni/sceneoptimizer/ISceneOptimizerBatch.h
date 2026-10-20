// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

// C-types only
#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>

namespace omni::scene::optimizer
{

class ISceneOptimizerBatch
{
public:
    CARB_PLUGIN_INTERFACE("omni::scene_optimizer::ISceneOptimizerBatch", 1, 0);

    virtual void onStartup(const char* extId) noexcept = 0;

    virtual void onShutdown() noexcept = 0;
};

} // namespace omni::scene::optimizer

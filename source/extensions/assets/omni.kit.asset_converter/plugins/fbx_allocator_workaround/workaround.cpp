// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// Kit 111 (Linux) workaround until the pinned usd-convert-asset installs its own FBX SDK allocator handlers
// (usd-convert-asset-internal#6). fbx_allocator.h/.cpp are copied unchanged from that change.
#include "fbx_allocator.h"

extern "C" __attribute__((visibility("default"))) void omniKitAssetConverterInstallFbxAllocatorHandlers()
{
    InstallFbxAllocatorHandlers();
}

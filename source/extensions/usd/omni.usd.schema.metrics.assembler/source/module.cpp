// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <pxr/base/tf/pyModule.h>
#include <pxr/base/tf/registryManager.h>
#include <pxr/base/tf/scriptModuleLoader.h>
#include <pxr/base/tf/token.h>
#include <pxr/pxr.h>

PXR_NAMESPACE_USING_DIRECTIVE

TF_WRAP_MODULE
{
}

TF_REGISTRY_FUNCTION(TfScriptModuleLoader)
{
    // List of direct dependencies for this library.
    const std::vector<TfToken> reqs = { TfToken("sdf"), TfToken("tf"), TfToken("usd"), TfToken("vt") };
    TfScriptModuleLoader::GetInstance().RegisterLibrary(
        TfToken("metricsAssembler"), TfToken("omni.MetricsAssembler"), reqs);
}

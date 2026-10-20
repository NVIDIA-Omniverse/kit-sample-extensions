// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "metricsAssemblerResolver.h"

#include <pxr/usd/ar/defineResolver.h>
#include <pxr/usd/ar/inMemoryAsset.h>

PXR_NAMESPACE_USING_DIRECTIVE

std::string MetricsAssemblerResolver::_CreateIdentifier(const std::string& assetPath,
                                                        const PXR_NS::ArResolvedPath& anchorAssetPath) const
{
    // we just return the assetPath as-is
    return assetPath;
}
std::string MetricsAssemblerResolver::_CreateIdentifierForNewAsset(const std::string& assetPath,
                                                                   const PXR_NS::ArResolvedPath& anchorAssetPath) const
{
    return _CreateIdentifier(assetPath, anchorAssetPath);
}
PXR_NS::ArResolvedPath MetricsAssemblerResolver::_Resolve(const std::string& assetPath) const
{
    if (assetPath.empty())
    {
        return {};
    }

    // we just return the assetPath as-is
    return PXR_NS::ArResolvedPath(assetPath);
}
PXR_NS::ArResolvedPath MetricsAssemblerResolver::_ResolveForNewAsset(const std::string& assetPath) const
{
    return _Resolve(assetPath);
}
std::shared_ptr<PXR_NS::ArAsset> MetricsAssemblerResolver::_OpenAsset(const PXR_NS::ArResolvedPath& resolvedPath) const
{
    // probably don't need to allocate a new char[] everytime this is called
    auto buffer = std::shared_ptr<const char>(new char[1], std::default_delete<const char[]>());
    return PXR_NS::ArInMemoryAsset::FromBuffer(std::move(buffer), 1);
}
std::shared_ptr<PXR_NS::ArWritableAsset> MetricsAssemblerResolver::_OpenAssetForWrite(
    const PXR_NS::ArResolvedPath& resolvedPath, ArResolver::WriteMode writeMode) const
{
    return {};
}

AR_DEFINE_RESOLVER(MetricsAssemblerResolver, PXR_NS::ArResolver);

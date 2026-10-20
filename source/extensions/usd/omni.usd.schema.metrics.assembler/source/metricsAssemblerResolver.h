// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <pxr/usd/ar/asset.h>
#include <pxr/usd/ar/resolvedPath.h>
#include <pxr/usd/ar/resolver.h>
#include <pxr/usd/ar/writableAsset.h>

class MetricsAssemblerResolver final : public PXR_NS::ArResolver
{
public:
    MetricsAssemblerResolver() = default;
    virtual ~MetricsAssemblerResolver() = default;

protected:
    std::string _CreateIdentifier(const std::string& assetPath,
                                  const PXR_NS::ArResolvedPath& anchorAssetPath) const override;
    std::string _CreateIdentifierForNewAsset(const std::string& assetPath,
                                             const PXR_NS::ArResolvedPath& anchorAssetPath) const override;
    PXR_NS::ArResolvedPath _Resolve(const std::string& assetPath) const override;
    PXR_NS::ArResolvedPath _ResolveForNewAsset(const std::string& assetPath) const override;

    std::shared_ptr<PXR_NS::ArAsset> _OpenAsset(const PXR_NS::ArResolvedPath& resolvedPath) const override;
    std::shared_ptr<PXR_NS::ArWritableAsset> _OpenAssetForWrite(const PXR_NS::ArResolvedPath& resolvedPath,
                                                                WriteMode writeMode) const override;
};

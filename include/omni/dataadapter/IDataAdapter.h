// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

namespace omni
{

namespace data
{

namespace adapter
{

struct ArrayData
{
    char** paths;
    size_t count;
};

class IDataAdapter
{
public:
    CARB_PLUGIN_INTERFACE("omni::data_adapter::IDataAdapter", 1, 0);

    virtual void onStartup(const char* extId) noexcept = 0;

    virtual void onShutdown() noexcept = 0;

    virtual void deletePrims(long int usdStageId, const char** primPaths, size_t primPathsSize) noexcept = 0;

    virtual ArrayData pathResolver(long int usdStageId,
                                   const char** paths,
                                   size_t pathsSize,
                                   bool considerHierarchy = false) noexcept = 0;

    virtual ArrayData merge(long int usdStageId,
                            const char** meshPrimPaths,
                            size_t meshPrimPathsSize,
                            bool considerMaterials,
                            bool materialAlbedoAsVertexColors,
                            int originalGeomOption,
                            const char* rootPath = "",
                            int mergePoint = 0) noexcept = 0;

    virtual void optimizeSkelRoots(long int usdStageId) noexcept = 0;

    virtual void pivot(long int usdStageId,
                       const char** meshPrimPaths = nullptr,
                       size_t meshPrimPathsSize = 0) noexcept = 0;

    virtual void exportHierarchy(long int usdStageId,
                                 bool includeEndPrim,
                                 const char* startPath,
                                 const char* filePath,
                                 bool considerConnections = true,
                                 bool considerRelationships = true,
                                 const char* endPath = "") noexcept = 0;

    virtual void deduplicateGeometry(long int usdStageId,
                                     const char** meshPrimPaths,
                                     size_t meshPrimPathsSize,
                                     int duplicateMethod = 3,
                                     bool considerDeepTransforms = false) noexcept = 0;

    virtual bool jsonParser(long int usdStageId, const char* filePath) noexcept = 0;

    virtual bool computeExtents(long int usdStageId, const char** meshPrimPaths, size_t meshPrimPathsSize) noexcept = 0;

    virtual void optimizeMaterials(long int usdStageId,
                                   const char** primPaths,
                                   size_t primPathsSize,
                                   int optimizeMode) noexcept = 0;

    virtual void printStats(long int usdStageId) noexcept = 0;

    virtual void pruneLeaves(long int usdStageId, int pruneMode) noexcept = 0;
};

} // namespace adapter

} // namespace data

} // namespace omni

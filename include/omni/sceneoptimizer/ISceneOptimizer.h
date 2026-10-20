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

// Usd Optimize
#include <usd_optimize/core/Defs.h>

// C-types only
#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>

namespace omni::scene::optimizer
{


struct StringArray
{
    char** strings;
    size_t count;
};


extern "C" inline void so_string_array_free(StringArray* stringArray)
{
    for (size_t i = 0; i < stringArray->count; ++i)
    {
        delete[] stringArray->strings[i];
    }

    delete[] stringArray->strings;

    stringArray->strings = nullptr;
    stringArray->count = 0;
}


class ISceneOptimizer
{
public:
    CARB_PLUGIN_INTERFACE("omni::scene_optimizer::ISceneOptimizer", 1, 0);

    virtual void deletePrims(ExecutionContext* context, const char** primPaths, size_t primPathsSize) noexcept = 0;

    virtual StringArray pathResolver(ExecutionContext* context,
                                     const char** paths,
                                     size_t pathsSize,
                                     bool considerHierarchy = false) noexcept = 0;

    virtual bool jsonParser(ExecutionContext* context, const char* filePath) noexcept = 0;

    /// Get the list of operation names that are currently registered.
    virtual StringArray getOperations() noexcept = 0;

    /// Get the display name of the specified operation.
    virtual const char* getOperationDisplayName(const char* operationName) noexcept = 0;

    /// Get the display group of the specified operation.
    virtual const char* getOperationDisplayGroup(const char* operationName) noexcept = 0;

    /// Get the description of the specified operation.
    virtual const char* getOperationDescription(const char* operationName) noexcept = 0;

    /// Return whether this operation should be visible, for the purposes of a UI.
    virtual bool getOperationVisible(const char* operationName) noexcept = 0;

    /// Return whether this operation supports analysis mode.
    virtual bool getOperationSupportsAnalysis(const char* operationName) noexcept = 0;

    /// Get a serialized JSON string describing the arguments an operation supports.
    virtual const char* getOperationArguments(const char* operationName) noexcept = 0;

    /// Get the author of an operation.
    virtual const char* getOperationAuthor(const char* operationName) noexcept = 0;

    /// Get the semantic version of an operation.
    virtual UsdOptimizePluginVersion getOperationVersion(const char* operationName) noexcept = 0;

    /// Execute the specified operation.
    virtual OperationResult executeOperation(const char* operationName,
                                             ExecutionContext* context,
                                             const char* args) noexcept = 0;

    /// Loads plugins contained in a directory
    virtual void loadPluginsFromPath(const char* path) = 0;

    /// Load the plugins that ship with scene optimizer and from any paths defined in the USD_OPTIMIZE_PLUGIN_PATH
    /// environment variable
    virtual void loadPlugins() = 0;

    /// Deregister an operation
    virtual void deregisterOperation(const char* name) = 0;

    /// Update a Scene Optimizer JSON configuration.
    ///
    /// Given a serialized JSON string representing a Scene Optimizer configuration, ensure any
    /// operations or attributes that have been renamed since the config was created are updated
    /// to their current naming.
    ///
    /// Note that any invalid data (missing operation key, invalid operation etc.) will not
    /// be included in the result.
    virtual const char* mapConfig(const char* args) = 0;

    /// Batch process a USD stage. Takes an input stage, output path, and JSON configuration path.
    virtual void batchProcessFile(const char* input, const char* output, const char* config) noexcept = 0;
};

} // namespace omni::scene::optimizer

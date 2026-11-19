// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#define CARB_EXPORTS

// Scene Optimizer
#include "PluginStats.h"

#include <omni/sceneoptimizer/ISceneOptimizer.h>

// Usd Optimize
#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/ParseJson.h>
#include <usd_optimize/core/RemovePrims.h>
#include <usd_optimize/core/ResolveSdfPaths.h>
#include <usd_optimize/core/Utils.h>

// Carbonite
#include <carb/Defines.h>
#include <carb/PluginUtils.h>
#include <carb/stats/Stats.h>

// USD
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdUtils/stageCache.h>

PXR_NAMESPACE_USING_DIRECTIVE

constexpr carb::PluginImplDesc pluginDesc = { "omni.scene.optimizer.core.plugin",
                                              "Scene Optimizer.",
                                              "NVIDIA",
                                              carb::PluginHotReload::eDisabled,
                                              "dev" };

CARB_EXPORT void carbOnPluginStartup()
{
    // Initialize scene optimizer core
    auto& core = usd_optimize::UsdOptimizeCore::getInstance();
    if (!core.isInitialized())
    {
        core.loadPlugins();
    }
}


CARB_EXPORT void carbOnPluginShutdown()
{
}

namespace omni::scene::optimizer
{

// Core types (ExecutionContext, OperationResult, Operation*, etc.) are provided by the usd_optimize
// library; pull them in so the unqualified references below resolve.
using namespace usd_optimize;


static std::vector<std::string> getStrings(const char** strings, size_t size)
{
    std::vector<std::string> result;
    result.reserve(size);

    for (size_t i = 0; i < size; ++i)
    {
        result.emplace_back(strings[i]);
    }

    return result;
}


class SceneOptimizerImpl final : public omni::scene::optimizer::ISceneOptimizer
{
private:
    std::shared_ptr<StatsHandler> m_statsHandler;

public:
    SceneOptimizerImpl()
        : m_statsHandler(std::make_shared<StatsHandler>())
    {
    }

protected:
    void deletePrims(ExecutionContext* context, const char** primPaths, size_t primPathsSize) noexcept override
    {
        UsdStageWeakPtr usdStage =
            (UsdStageWeakPtr)(UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(context->usdStageId)));
        _deletePrims(usdStage, getStrings(primPaths, primPathsSize));
    }

    StringArray pathResolver(ExecutionContext* context,
                             const char** paths,
                             size_t pathsSize,
                             bool considerHierarchy) noexcept override
    {
        UsdStageWeakPtr usdStage =
            (UsdStageWeakPtr)(UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(context->usdStageId)));

        std::vector<UsdPrim> prims = _resolveExpressionsToPrims(usdStage, getStrings(paths, pathsSize));
        SdfPathVector _paths = _convertToSdfPaths(prims);

        size_t count = _paths.size();

        StringArray data;
        data.strings = new char*[count];
        data.count = count;

        for (size_t i = 0; i < count; ++i)
        {
            const std::string& _path = _paths[i].GetAsString();
            size_t cnt = _path.length() + 1;

            data.strings[i] = new char[cnt];
            strncpy(data.strings[i], _path.c_str(), cnt - 1);
            data.strings[i][cnt - 1] = '\0';
        }

        return data;
    }


    bool jsonParser(ExecutionContext* context, const char* filePath) noexcept override
    {
        UsdStageWeakPtr usdStage =
            (UsdStageWeakPtr)(UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(context->usdStageId)));

        bool status = _parseJson(usdStage, filePath, context);
        return status;
    }


    StringArray getOperations() noexcept override
    {
        auto& core = usd_optimize::UsdOptimizeCore::getInstance();
        const auto& operations = core.getOperations();

        size_t count = operations.size();

        StringArray data{};
        data.strings = new char*[count];
        data.count = count;

        size_t index = 0;
        for (const auto& name : operations)
        {
            data.strings[index] = new char[name.length() + 1];
            strncpy(data.strings[index], name.c_str(), name.length());
            data.strings[index][name.length()] = '\0';
            ++index;
        }

        return data;
    }


    const char* getOperationDisplayName(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return nullptr;
        }

        return getCStr(operation->getDisplayName());
    }


    const char* getOperationDisplayGroup(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return nullptr;
        }

        return getCStr(operation->getDisplayGroup());
    }


    const char* getOperationDescription(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return nullptr;
        }

        return getCStr(operation->getDescription());
    }


    const char* getOperationArguments(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        // Verify operation exists
        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return nullptr;
        }

        // Create a JSON array and append the JSON object for each argument
        JsArray args;
        for (const Argument* argument : operation->getArgs())
        {
            args.push_back(argument->toJson());
        }

        // Return a new char* from the serialized data
        return getCStr(JsWriteToString(args));
    }


    const char* getOperationAuthor(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return nullptr;
        }

        return getCStr(operation->getAuthor());
    }


    UsdOptimizePluginVersion getOperationVersion(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return UsdOptimizePluginVersion{ -1, -1, -1 };
        }

        return operation->getVersion();
    }


    bool getOperationVisible(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return false;
        }

        return operation->getVisible();
    }


    bool getOperationSupportsAnalysis(const char* operationName) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        const OperationUPtr operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return false;
        }

        return operation->getSupportsAnalysis();
    }


    OperationResult executeOperation(const char* operationName, ExecutionContext* context, const char* args) noexcept override
    {
        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        JsValue _args;

        // Deserialize. We expect the args to be a serialized JSON Object/Dict.
        if (args != nullptr && strnlen(args, 1024))
        {
            _args = JsParseString(args);
        }

        // Empty string, no args, invalid object, etc.
        if (!_args.IsObject())
        {
            // Not an object, create an empty object as a placeholder.
            _args = JsObject();
        }

        const OperationUPtr& operation = core.getOperation(operationName);
        if (operation == nullptr)
        {
            return { false, getCStr("Operation not found"), nullptr };
        }

        // Execute
        const OperationResult result = operation->execute(context, _args.GetJsObject());

        // Some operations may make changes (for example, removeAttributes) that do not currently
        // get picked up by iStageUpdate. We can force an extra stat trigger here to ensure that
        // the stats will be updated in those cases. Special-case to ignore printStats as that doesn't
        // change the stage, and will be executed from the UI twice for every set of operations.
        if (result.success && strcmp(operationName, "printStats") != 0)
        {
            m_statsHandler->triggerUpdate();
        }

        return result;
    }


    void loadPluginsFromPath(const char* path) override
    {
        auto& core = usd_optimize::UsdOptimizeCore::getInstance();
        core.loadPluginsFromPath(path);
    }


    void loadPlugins() override
    {
        auto& core = usd_optimize::UsdOptimizeCore::getInstance();
        core.loadPlugins();
    }


    void deregisterOperation(const char* name) override
    {
        auto& core = usd_optimize::UsdOptimizeCore::getInstance();
        core.deregisterOperation(name);
    }


    const char* mapConfig(const char* args) noexcept override
    {

        const auto& core = usd_optimize::UsdOptimizeCore::getInstance();

        JsValue _config;

        // Deserialize. We expect the args to be a serialized JSON array of objects.
        if (args != nullptr && strnlen(args, 1024))
        {
            _config = JsParseString(args);
        }

        // Empty string, no args, invalid array, etc.
        if (!_config.IsArray())
        {
            // Not an array - just return the original data, for better or worse.
            // Note we return a copy, so that either success or failure both mean
            // a new string.
            return args == nullptr ? getCStr("") : getCStr(args);
        }

        JsArray mapped = core.mapConfig(_config.GetJsArray());
        return getCStr(JsWriteToString(mapped));
    }


    void batchProcessFile(const char* input, const char* output, const char* config) noexcept override
    {
        // Open the stage
        const UsdStageRefPtr& usdStage = UsdStage::Open(input);

        // Prepare stats operation for before/after stats
        auto& core = usd_optimize::UsdOptimizeCore::getInstance();
        OperationUPtr statsOp = core.getOperation("printStats");

        // Create context
        ExecutionContext context;
        context.usdStageId = UsdUtilsStageCache::Get().Insert(usdStage).ToLongInt();

        // Before stats
        if (statsOp)
        {
            statsOp->execute(&context, JsObject{});
        }

        _parseJson(usdStage, config, &context);

        // After stats
        if (statsOp)
        {
            statsOp->execute(&context, JsObject{});
        }

        // Write result
        if (strcmp(input, output) == 0)
        {
            usdStage->Save();
        }
        else
        {
            usdStage->Export(output);
        }
    }
};

} // namespace omni::scene::optimizer

CARB_PLUGIN_IMPL(pluginDesc, omni::scene::optimizer::SceneOptimizerImpl)
CARB_ISTATS_GLOBALS()

// LCOV_EXCL_START
void fillInterface(omni::scene::optimizer::SceneOptimizerImpl& iface)
{
    iface = {};

    // Register for the stats interface
    carb::stats::registerStatsInterfaceForClient();
}
// LCOV_EXCL_STOP

// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Scene Optimizer Core (external usd_optimize package)
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/PybindUtils.h>

// Scene Optimizer Interface
#include <omni/sceneoptimizer/ISceneOptimizer.h>

// Carb
#include <carb/BindingsPythonUtils.h>

// USD
#include <pxr/base/js/json.h>
#include <pxr/base/js/value.h>

CARB_BINDINGS("omni.scene.optimizer.core.python")

namespace
{


#define VEC_TO_CVEC(IN, OUT)                                                                                           \
    std::vector<const char*> OUT;                                                                                      \
    OUT.reserve(IN.size());                                                                                            \
    for (const auto& val : IN)                                                                                         \
    {                                                                                                                  \
        OUT.push_back(val.c_str());                                                                                    \
    }


py::list _getList(const omni::scene::optimizer::StringArray& array)
{
    py::list pyList;
    for (size_t i = 0; i < array.count; ++i)
    {
        pyList.append(array.strings[i]);
    }

    return pyList;
}


PYBIND11_MODULE(_omni_scene_optimizer_core, m)
{
    using namespace carb;
    using namespace omni::scene::optimizer;
    // Core types (ExecutionContext, OperationResult, _getExecutionContextFromPyWrapper) are provided
    // by the usd_optimize library.
    using namespace usd_optimize;

    m.doc() = "pybind11 scene::optimizer bindings";


    defineInterfaceClass<omni::scene::optimizer::ISceneOptimizer>(m,
                                                                  "ISceneOptimizer",
                                                                  "acquire_interface",
                                                                  "release_interface")

        .def(
            "delete_prims",
            [](omni::scene::optimizer::ISceneOptimizer* _this, py::object context, const std::vector<std::string>& paths)
            {
                // Convert std::string to char**
                VEC_TO_CVEC(paths, cpaths)

                // Call bound function
                _this->deletePrims(_getExecutionContextFromPyWrapper(context), cpaths.data(), cpaths.size());
            },
            R"(Delete prims at specified paths)")

        .def(
            "path_resolver",
            [](omni::scene::optimizer::ISceneOptimizer* _this,
               py::object context,
               const std::vector<std::string>& paths,
               bool considerHierarchy)
            {
                // Convert std::string to char**
                VEC_TO_CVEC(paths, cpaths)

                // Call bound function
                StringArray data =
                    _this->pathResolver(_getExecutionContextFromPyWrapper(context), cpaths.data(), cpaths.size());

                py::list pyPaths = _getList(data);
                so_string_array_free(&data);

                return pyPaths;
            },
            R"(Parses input paths, regex expressions, and considers hierarchies to find all prims in a scene that conform to the given arguments)")

        .def(
            "json_parser",
            [](omni::scene::optimizer::ISceneOptimizer* _this, py::object context, const char* str)
            { return _this->jsonParser(_getExecutionContextFromPyWrapper(context), str); },
            R"(Parse a JSON configuration file or string that contains a sequence of operations to run.)")

        .def(
            "get_operations",
            [](omni::scene::optimizer::ISceneOptimizer* _this)
            {
                StringArray data = _this->getOperations();

                // Convert strings to python list
                py::list pyPaths = _getList(data);
                so_string_array_free(&data);

                return pyPaths;
            },
            R"(Returns a list of the registered operation names)")

        .def(
            "get_operation_display_name",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            {
                const char* displayName = _this->getOperationDisplayName(name.c_str());

                std::string result(displayName);
                free(const_cast<char*>(displayName));

                return result;
            },
            R"(Returns the display name of the specified operation)")

        .def(
            "get_operation_display_group",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            {
                const char* displayGroup = _this->getOperationDisplayGroup(name.c_str());

                std::string result(displayGroup);
                free(const_cast<char*>(displayGroup));

                return result;
            },
            R"(Returns the display group of the specified operation)")

        .def(
            "get_operation_author",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            {
                const char* author = _this->getOperationAuthor(name.c_str());

                std::string result(author);
                free(const_cast<char*>(author));

                return result;
            },
            R"(Returns the author of the specified operation)")

        .def(
            "get_operation_version",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            { return _this->getOperationVersion(name.c_str()); },
            R"(Returns the semantic version of the specified operation)")

        .def(
            "get_operation_description",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            {
                const char* description = _this->getOperationDescription(name.c_str());

                std::string result(description);
                free(const_cast<char*>(description));

                return result;
            },
            R"(Returns the description of the specified operation)")

        .def(
            "get_operation_visible",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            { return _this->getOperationVisible(name.c_str()); },
            R"(Returns whether or not this operation should be displayed in a UI)")

        .def(
            "get_operation_supports_analysis",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            { return _this->getOperationSupportsAnalysis(name.c_str()); },
            R"(Returns whether or not this operation supports analysis mode)")

        .def(
            "get_operation_arguments",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            {
                const char* argString = _this->getOperationArguments(name.c_str());

                PXR_NS::JsValue args;
                if (strnlen(argString, 1024))
                {
                    args = PXR_NS::JsParseString(argString);
                }

                // Clear up string
                free(const_cast<char*>(argString));

                py::list result{};

                // The args come back as an array of arguments.
                if (!args.IsNull() && args.IsArray())
                {
                    // Convert JSON structure to python objects
                    const PXR_NS::JsArray& _args = args.GetJsArray();

                    for (const PXR_NS::JsValue& value : _args)
                    {
                        // Args should be an object/dict.
                        if (value.IsObject())
                        {
                            // Convert the JsValue to a py dict and append
                            result.append(_jsonObjectToPybindDict(value.GetJsObject()));
                        }
                    }
                }

                return result;
            },
            R"(Returns a list of the arguments for the specified operation)")

        .def(
            "execute_operation",
            [](omni::scene::optimizer::ISceneOptimizer* _this,
               const std::string& name,
               py::object context,
               const std::string& args)
            {
                // Execute operation.
                OperationResult result =
                    _this->executeOperation(name.c_str(), _getExecutionContextFromPyWrapper(context), args.c_str());

                // convert result to a python tuple
                py::tuple _result = _operationResultToPybindTuple(result);

                // Free the operation result
                usd_optimize_operation_result_free(&result);

                return _result;
            },
            R"(Execute the specified operation. Returns a tuple of success, optional error, and optional arbitrary data.)")

        .def(
            "load_plugins_from_path",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& path)
            { _this->loadPluginsFromPath(path.c_str()); },
            R"(Loads plugins contained in a directory)")

        .def(
            "load_plugins",
            [](omni::scene::optimizer::ISceneOptimizer* _this) { _this->loadPlugins(); },
            R"(Load the plugins that ship with scene optimizer and from any paths defined in the USD_OPTIMIZE_PLUGIN_PATH environment variable)")

        .def(
            "deregister_operation",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& name)
            { _this->deregisterOperation(name.c_str()); },
            R"(Deregister an operation)")

        .def(
            "map_config",
            [](omni::scene::optimizer::ISceneOptimizer* _this, const std::string& config)
            {
                const char* mappedConfig = _this->mapConfig(config.c_str());

                std::string result(mappedConfig);
                free(const_cast<char*>(mappedConfig));

                return result;
            },
            R"(Map a JSON configuration to ensure operation/argument names are up to date)");
}

}

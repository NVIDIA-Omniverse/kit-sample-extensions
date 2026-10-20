// SPDX-FileCopyrightText: Copyright (c) 2018-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "../plugins/UsdHeaders.h"

#include <carb/BindingsPythonUtils.h>

#include <omni/usd/IMetricsAssembler.h>

#include <unordered_map>

CARB_BINDINGS("omni.metricsassembler.python")

namespace
{
using namespace omni::usd;

#define ADD_SETTING(attr_name, path) m.attr(attr_name) = py::str(path);


static void resolveStartGlobal(long stageId, void* userData);
static void resolveEndGlobal(long stageId, void* userData);

static bool resolvePrimGlobal(const pxr::UsdPrim& usdPrim,
                              const UnitsInfo& stageUnits,
                              const UnitsInfo& resolveUnits,
                              void* userData);

static bool resolveAttributeGlobal(const pxr::UsdPrim& usdPrim,
                                   pxr::UsdAttribute& attribute,
                                   const UnitsInfo& stageUnits,
                                   const UnitsInfo& resolveUnits,
                                   int& metersExponent,
                                   int& kilogramsExponent,
                                   void* userData);

using ResolveStartFn = std::function<void(long stageId)>;
using ResolveEndFn = std::function<void(long stageId)>;
using ResolvePrimFn =
    std::function<bool(const char* usdPrimPath, const UnitsInfo& stageUnits, const UnitsInfo& resolveUnits)>;
using ResolveAttributeFn = std::function<py::tuple(const char* usdPrimPath,
                                                   const char* attributeName,
                                                   const UnitsInfo& stageUnits,
                                                   const UnitsInfo& resolveUnits,
                                                   int& metersExponent,
                                                   int& kilogramsExponent)>;

struct CallbackInfo
{
    ResolveStartFn resolveStartFn;
    ResolveEndFn resolveEndFn;
    ResolvePrimFn resolvePrimFn;
    ResolveAttributeFn resolveAttributeFn;
    size_t registryId;
};
using SubscriberMap = std::unordered_map<size_t, CallbackInfo>;

struct MarshalCallbacks
{
    size_t subscribeCallback(const omni::usd::IMetricsAssembler* assetResolver,
                             const ResolveStartFn& resolveStart,
                             const ResolveEndFn& resolveEnd,
                             const ResolvePrimFn& resolvePrim,
                             const ResolveAttributeFn& resolveAttr,
                             const std::vector<std::string>& attributeTokenNames)
    {
        IMetricsAssemblerCallback cb;
        cb.resolveStartFn = resolveStartGlobal;
        cb.resolveEndFn = resolveEndGlobal;
        cb.resolvePrimFn = resolvePrimGlobal;
        cb.resolveAttributeFn = resolveAttributeGlobal;
        cb.userData = (void*)++currentId;

        std::vector<pxr::TfToken> tokenVector;
        if (!attributeTokenNames.empty())
        {
            for (const std::string& tokenName : attributeTokenNames)
            {
                tokenVector.push_back(pxr::TfToken(tokenName));
            }
        }
        size_t id = assetResolver->registerCustomCallback(cb, &tokenVector);
        mRegistryMap[currentId] = { resolveStart, resolveEnd, resolvePrim, resolveAttr, id };
        return currentId;
    }

    void unsubscribeCallback(const omni::usd::IMetricsAssembler* assetResolver, size_t id)
    {
        SubscriberMap::iterator fit = mRegistryMap.find(id);
        if (fit != mRegistryMap.end())
        {
            assetResolver->unregisterCustomCallback(fit->second.registryId);
            mRegistryMap.erase(fit);
        }
    }

    const CallbackInfo* getCallbackInfo(size_t id)
    {
        SubscriberMap::iterator fit = mRegistryMap.find(id);
        if (fit != mRegistryMap.end())
        {
            return &fit->second;
        }
        return nullptr;
    }

public:
    size_t currentId;
    SubscriberMap mRegistryMap;
};

static MarshalCallbacks gMarshalCallbacks;

void resolveStartGlobal(long stageId, void* userData)
{
    const CallbackInfo* cbInfo = gMarshalCallbacks.getCallbackInfo((size_t)userData);
    if (cbInfo && cbInfo->resolveStartFn)
    {
        cbInfo->resolveStartFn(stageId);
    }
}

void resolveEndGlobal(long stageId, void* userData)
{
    const CallbackInfo* cbInfo = gMarshalCallbacks.getCallbackInfo((size_t)userData);
    if (cbInfo && cbInfo->resolveEndFn)
    {
        cbInfo->resolveEndFn(stageId);
    }
}

bool resolvePrimGlobal(const pxr::UsdPrim& usdPrim, const UnitsInfo& stageUnits, const UnitsInfo& resolveUnits, void* userData)
{
    const CallbackInfo* cbInfo = gMarshalCallbacks.getCallbackInfo((size_t)userData);
    if (cbInfo && cbInfo->resolvePrimFn)
    {
        return cbInfo->resolvePrimFn(usdPrim.GetPrimPath().GetText(), stageUnits, resolveUnits);
    }
    return true;
}

bool resolveAttributeGlobal(const pxr::UsdPrim& usdPrim,
                            pxr::UsdAttribute& attribute,
                            const UnitsInfo& stageUnits,
                            const UnitsInfo& resolveUnits,
                            int& metersExponent,
                            int& kilogramsExponent,
                            void* userData)
{
    const CallbackInfo* cbInfo = gMarshalCallbacks.getCallbackInfo((size_t)userData);
    if (cbInfo && cbInfo->resolveAttributeFn)
    {
        const py::tuple outPar =
            cbInfo->resolveAttributeFn(usdPrim.GetPrimPath().GetText(), attribute.GetName().GetText(), stageUnits,
                                       resolveUnits, metersExponent, kilogramsExponent);
        const bool retVal = (!outPar.is_none() && outPar.size()) ? outPar[0].cast<bool>() : true;
        const int newMPU = (!outPar.is_none() && outPar.size() > 1) ? outPar[1].cast<int>() : metersExponent;
        const int newKGPU = (!outPar.is_none() && outPar.size() > 2) ? outPar[2].cast<int>() : kilogramsExponent;
        metersExponent = newMPU;
        kilogramsExponent = newKGPU;
        return retVal;
    }
    return true;
}

PYBIND11_MODULE(_metricsAssembler, m)
{
    using namespace carb;

    m.doc() = "pybind11 omni.usd.metrics.assembler bindings";

    ADD_SETTING("SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE", kMetricsAssemblerOperationMode);
    ADD_SETTING(
        "SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED", kMetricsAssemblerParamsChangeListenerEnabled);
    ADD_SETTING("SETTINGS_METRICS_ASSEMBLER_SHOW_UNITS_OVERLAY", kMetricsAssemblerShowUnitsOverlay); // OBSOLETE
    ADD_SETTING("SETTINGS_METRICS_ASSEMBLER_CONFORM_TO_XFORM_COMMON_API", kMetricsAssemblerConformToXformCommonAPI);

    py::class_<omni::usd::UnitsInfo>(m, "UnitsInfo", R"(
            Units info.
        )")
        .def(py::init())
        .def_readwrite("meters_per_unit", &omni::usd::UnitsInfo::metersPerUnit, R"(Meters Per Unit.)")
        .def_readwrite("kilograms_per_unit", &omni::usd::UnitsInfo::kilogramsPerUnit, R"(Kilograms Per Unit.)")
        .def_property(
            "up_axis",
            [](const UnitsInfo* self) {
                const pxr::TfToken upAxis = self->upAxis;
                return upAxis.GetText();
            },
            [](UnitsInfo* self, const char* upAxisStr) { self->upAxis = pxr::TfToken(upAxisStr); }, R"(Up axis.)")
        .def("__str__", [](const UnitsInfo& info) {
            std::string asStr = "MPU: ";
            asStr.append(std::to_string(info.metersPerUnit));
            asStr.append(" KGPU: ");
            asStr.append(std::to_string(info.kilogramsPerUnit));
            asStr.append(" upAxis: ");
            asStr.append(info.upAxis.GetText());
            return asStr;
        });

    m.doc() = R"(
        This module contains python bindings to the C++ omni::usd IMetricsAssembler interface.
    )";

    const char* docString;

    auto assetResolverIface = defineInterfaceClass<omni::usd::IMetricsAssembler>(
        m, "MetricsAssembler", "acquire_metrics_assembler_interface", "release_metrics_assembler_interface");
    m.def("release_metrics_assembler_interface_scripting", [](omni::usd::IMetricsAssembler* iface) {
        carb::getFramework()->releaseInterfaceWithClient("carb.scripting-python.plugin", iface); // OM-60917
    });

    docString = R"(
        Check units divergency on given stage.
    )";
    assetResolverIface.def("check_stage", wrapInterfaceFunction(&IMetricsAssembler::checkStage), docString);

    docString = R"(
        Check units divergency on given two layers. The inputs are layer indentifiers.

        Returns:
            Return a dictionary with info::

                'ret_val': bool - whether layers are divergent
                'units_info0': UnitsInfo - layer0 units
                'units_info1': UnitsInfo - layer1 units
    )";
    assetResolverIface.def(
        "check_layers",
        [](const IMetricsAssembler* self, const char* layer0Id, const char* layer1Id, long stageId) {
            UnitsInfo info0;
            UnitsInfo info1;
            const bool retVal = self->checkLayers(layer0Id, layer1Id, stageId, &info0, &info1);

            py::dict outInfo;
            outInfo["ret_val"] = retVal;
            outInfo["units_info0"] = info0;
            outInfo["units_info1"] = info1;
            return outInfo;
        },
        docString, py::arg("layer0Identifier"), py::arg("layer1Identifier"), py::arg("stage_id"));

    docString = R"(
        Resolve given stage.
    )";
    assetResolverIface.def("resolve_stage", wrapInterfaceFunction(&IMetricsAssembler::resolveStage), docString);

    docString = R"(
        Resolve given stage hierarchy from given path.
    )";
    assetResolverIface.def(
        "resolve_hierarchy",
        [](const IMetricsAssembler* self, long stageId, const char* primPath) {
            return self->resolveHierarchy(stageId, pxr::SdfPath(primPath));
        },
        docString, py::arg("stage_id"), py::arg("prim_path"));

    docString = R"(
        Set resolve layer.
    )";
    assetResolverIface.def("set_resolve_layer", wrapInterfaceFunction(&IMetricsAssembler::setResolveLayer), docString);

    docString = R"(
        Register custom resolve rule.

        The applied rule works like this:
        resolvedValue = value * (MPU/stageMPU)^metersExponent * (KGPU/stageKGPU)^kilogramsExponent
    )";
    assetResolverIface.def(
        "register_custom_resolve_rule",
        [](const IMetricsAssembler* self, const char* attributeName, int metersExponent, int kilogramsExponent) {
            return self->registerCustomResolveRule(pxr::TfToken(attributeName), metersExponent, kilogramsExponent);
        },
        docString, py::arg("attribute_name"), py::arg("meters_exponent"), py::arg("kilograms_exponent"));

    docString = R"(
        Unregister custom resolve rule.
    )";
    assetResolverIface.def("unregister_custom_resolve_rule",
                           wrapInterfaceFunction(&IMetricsAssembler::unregisterCustomResolveRule), docString);

    docString = R"(
        Register custom callback.

        Resolve_start_fn: long stageId

        Resolve_end_fn: long stageId

        Resolve_prim_fn: const char* usdPrimPath, const UnitsInfo& stageUnits, const UnitsInfo& resolveUnits,
                int& metersExponent, int& kilogramsExponent

        Resolve_attribute_fn: const char* usdPrimPath, const char* attributeName, const UnitsInfo& stageUnits, const UnitsInfo& resolveUnits,
                int& metersExponent, int& kilogramsExponent

        Attribute_tokens: list of attribute tokens that will filter the resolve_attribute_fn, only attributes with these token names will
                fire the callback. If None all attributes will be send to the custom resolve function, note that this will have performance impact
    )";
    assetResolverIface.def(
        "register_custom_callback",
        [](const IMetricsAssembler* self, ResolveStartFn resolve_start_fn, ResolveEndFn resolve_end_fn,
           ResolvePrimFn resolve_prim_fn, ResolveAttributeFn resolve_attribute_fn,
           const std::vector<std::string>& attribute_tokens) {
            return gMarshalCallbacks.subscribeCallback(
                self, resolve_start_fn, resolve_end_fn, resolve_prim_fn, resolve_attribute_fn, attribute_tokens);
        },
        docString, py::arg("resolve_start_fn"), py::arg("resolve_end_fn"), py::arg("resolve_prim_fn"),
        py::arg("resolve_attribute_fn"), py::arg("attribute_tokens") = std::vector<const char*>());

    docString = R"(
        Unregister custom callback.
    )";
    assetResolverIface.def(
        "unregister_custom_callback",
        [](const IMetricsAssembler* self, size_t id) { gMarshalCallbacks.unsubscribeCallback(self, id); }, docString,
        py::arg("registry_id"));

    docString = R"(
       Change stage units
    
       note This operation is destructive and will happen with the current active target layer
            Additionally the xformOpCommonAPI is used for the xformOp stack transformation.

       stageId USD stage id.
       newUnits New desired units for the stage
       return True if operation was succesfull.
    )";
    assetResolverIface.def("change_stage_units", wrapInterfaceFunction(&IMetricsAssembler::changeStageUnits), docString);
}
} // namespace

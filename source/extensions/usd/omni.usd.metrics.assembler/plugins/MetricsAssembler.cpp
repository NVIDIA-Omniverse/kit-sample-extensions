// SPDX-FileCopyrightText: Copyright (c) 2018-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// This include must come first
// clang-format off
#include "UsdHeaders.h"
// clang-format on

#define CARB_EXPORTS


#include "UsdResolve.h"

#include <carb/Framework.h>
#include <carb/PluginUtils.h>
#include <carb/settings/ISettings.h>

#include <omni/usd/IMetricsAssembler.h>

using namespace pxr;
using namespace carb;
using namespace omni::usd;

const struct carb::PluginImplDesc kPluginImpl = { "omni.usd.metrics.assembler.plugin", "USD", "NVIDIA",
                                                  carb::PluginHotReload::eDisabled, "dev" };
CARB_PLUGIN_IMPL(kPluginImpl, omni::usd::IMetricsAssembler)
CARB_PLUGIN_IMPL_DEPS(carb::settings::ISettings)

static UsdResolve* gUsdResolve = nullptr;

CARB_EXPORT void carbOnPluginStartup()
{
    gUsdResolve = new UsdResolve();
    carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
    // set default to dialog mode
    settings->setDefaultInt(kMetricsAssemblerOperationMode, 3);

    settings->setDefaultBool(kMetricsAssemblerParamsChangeListenerEnabled, true);

    settings->setDefaultBool(kMetricsAssemblerShowUnitsOverlay, true); // OBSOLETE

    settings->setDefaultBool(kMetricsAssemblerConformToXformCommonAPI, false);
}

CARB_EXPORT void carbOnPluginShutdown()
{
    if (gUsdResolve)
    {
        delete gUsdResolve;
        gUsdResolve = nullptr;
    }
}


bool checkStage(long stageId)
{
    if (gUsdResolve)
    {
        return gUsdResolve->checkStage(stageId);
    }
    return true;
}

bool checkLayers(const char* layer0, const char* layer1, long stageId, UnitsInfo* layerInfo0, UnitsInfo* layerInfo1)
{
    if (gUsdResolve)
    {
        return gUsdResolve->checkLayers(layer0, layer1, stageId, layerInfo0, layerInfo1);
    }
    return true;
}

bool resolveStage(long stageId)
{
    if (gUsdResolve)
    {
        return gUsdResolve->resolveStage(stageId);
    }
    return true;
}

bool resolveHierarchy(long stageId, const pxr::SdfPath& primPath)
{
    if (gUsdResolve)
    {
        return gUsdResolve->resolveHierarchy(stageId, primPath);
    }
    return true;
}

size_t registerCustomCallback(IMetricsAssemblerCallback& customCallback,
                              const std::vector<pxr::TfToken>* attributeResolveFnTokens)
{
    if (gUsdResolve)
    {
        return gUsdResolve->registerCustomCallback(customCallback, attributeResolveFnTokens);
    }
    return kInvalidRegistryId;
}

void unregisterCustomCallback(size_t id)
{
    if (gUsdResolve)
    {
        gUsdResolve->unregisterCustomCallback(id);
    }
}

size_t registerCustomResolveRule(pxr::TfToken attributeName, int metersExponent, int kilogramsExponent)
{
    if (gUsdResolve)
    {
        return gUsdResolve->registerCustomResolveRule(attributeName, metersExponent, kilogramsExponent);
    }
    return kInvalidRegistryId;
}

void unregisterCustomResolveRule(size_t id)
{
    if (gUsdResolve)
    {
        gUsdResolve->unregisterCustomResolveRule(id);
    }
}

void setResolveLayer(const char* layer)
{
    if (gUsdResolve)
    {
        gUsdResolve->setResolveLayer(layer);
    }
}

bool changeStageUnits(long stageId, const UnitsInfo& newUnits)
{
    if (gUsdResolve)
    {
        return gUsdResolve->changeStageUnits(stageId, newUnits);
    }
    return false;
}

void fillInterface(omni::usd::IMetricsAssembler& iface)
{
    iface.checkStage = checkStage;
    iface.checkLayers = checkLayers;
    iface.resolveStage = resolveStage;
    iface.resolveHierarchy = resolveHierarchy;

    iface.setResolveLayer = setResolveLayer;

    iface.registerCustomCallback = registerCustomCallback;
    iface.unregisterCustomCallback = unregisterCustomCallback;

    iface.registerCustomResolveRule = registerCustomResolveRule;
    iface.unregisterCustomResolveRule = unregisterCustomResolveRule;

    iface.changeStageUnits = changeStageUnits;
}

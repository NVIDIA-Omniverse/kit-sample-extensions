// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "UsdPCH.h"
// clang-format on

#define CARB_EXPORTS

#ifdef _MSC_VER
#    pragma warning(disable : 4996)
#endif

#include "CurveManipulatorContext.h"

#include <carb/PluginUtils.h>
#include <carb/events/IEvents.h>
#include <carb/settings/ISettings.h>

#include <omni/curvecreator/ICurveCreator.h>
#include <omni/curvemanipulator/ICurveManipulator.h>
#include <omni/kit/IApp.h>
#include <omni/kit/IStageUpdate.h>
#include <omni/renderer/IDebugDraw.h>


#define EXTENSION_NAME "omni.curve.manipulator"

using namespace carb;
using namespace omni::curvemanipulator;

const struct PluginImplDesc kPluginImpl = { EXTENSION_NAME, "Omniverse Curve Manipulator.", "NVIDIA",
                                            PluginHotReload::eEnabled, "dev" };

CARB_PLUGIN_IMPL_DEPS(events::IEvents,
                      logging::ILogging,
                      settings::ISettings,
                      omni::curvecreator::ICurveCreator,
                      omni::kit::IApp,
                      omni::renderer::IDebugDraw)

// Strange memory corruption if CurveManipulator directly implements ICurveManipulator, hmmm...
class CurveManipulatorInterfaceImpl final : public ICurveManipulator
{
public:
    CurveManipulatorContext* createContext(const char* usdContextName = "") override
    {
        return new CurveManipulatorContext(usdContextName);
    }

    void destroyContext(CurveManipulatorContext* context) override
    {
        delete context;
    }

    void enableCurveEditingMode(CurveManipulatorContext* context,
                                const char** paths,
                                size_t count,
                                CurveEditingModeType mode) override
    {
        context->enableCurveEditingMode(paths, count, mode);
    }

    bool isInCurveEditingMode(const CurveManipulatorContext* context) const override
    {
        return context->isInCurveEditingMode();
    }

    void disableCurveEditingMode(CurveManipulatorContext* context) override
    {
        context->disableCurveEditingMode();
    }

    size_t getEditingCurvePathsCount(const CurveManipulatorContext* context) const override
    {
        return context->getEditingCurvePathsCount();
    }

    void getEditingCurvePaths(const CurveManipulatorContext* context, const char** primPaths) const override
    {
        context->getEditingCurvePaths(primPaths);
    }

    carb::events::IEventStream* getCurvesEventStream(CurveManipulatorContext* context) override
    {
        return context->getCurvesEventStream();
    }

    CurveEditingModeType getCurveEditingMode(const CurveManipulatorContext* context) const override
    {
        return context->getCurveEditingMode();
    }

    void setAddingCurveToBasisCurves(CurveManipulatorContext* context, bool value)
    {
        context->setAddingCurveToBasisCurves(value);
    }

    void setCurveEditingMode(CurveManipulatorContext* context, CurveEditingModeType mode) override
    {
        context->setCurveEditingMode(mode);
    }

    void onRaycast(CurveManipulatorContext* context,
                   const carb::Float3& origin,
                   const carb::Float3& dir,
                   bool input,
                   bool end,
                   const char* cameraPath,
                   const carb::Float4& rect,
                   const double* viewProjMatrix,
                   const carb::Double3* snapWorldPos) override
    {
        context->onRaycast(origin, dir, input, end, cameraPath, rect, viewProjMatrix, snapWorldPos);
    }
};

CARB_PLUGIN_IMPL(kPluginImpl, CurveManipulatorInterfaceImpl)

void fillInterface(CurveManipulatorInterfaceImpl& iface)
{
}

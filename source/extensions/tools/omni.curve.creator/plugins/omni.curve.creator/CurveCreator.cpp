// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#define CARB_EXPORTS

#include "CurveCreatorContext.h"

#include <carb/PluginUtils.h>

#include <omni/curvecreator/ICurveCreator.h>
#include <omni/kit/IApp.h>
#include <omni/renderer/IDebugDraw.h>

#include <memory>

using namespace carb;

#define EXTENSION_NAME "omni.curve.creator"

const struct PluginImplDesc kPluginImpl = { EXTENSION_NAME, "Omniverse Curve Creator.", "NVIDIA",
                                            PluginHotReload::eEnabled, "dev" };

CARB_PLUGIN_IMPL_DEPS(logging::ILogging, settings::ISettings, omni::kit::IApp, omni::renderer::IDebugDraw)

namespace omni
{
namespace curvecreator
{
class CurveCreatorInterfaceImpl final : public ICurveCreator
{
public:
    CurveCreatorContext* createContext(const carb::Float4& plane /*= { 0, 1, 0, 0 }*/,
                                       float spacing /*= 50*/,
                                       CurveInterpolateTypes type /*= CurveInterpolateTypes::eLinear*/,
                                       OnCreatedFn onCreatedFn /*= nullptr*/,
                                       void* userData /*= nullptr*/) override
    {
        return new CurveCreatorContext(plane, spacing, type, onCreatedFn, userData);
    }

    void destroyContext(CurveCreatorContext* context) override
    {
        delete context;
    }

    void startCurveCreation(CurveCreatorContext* context) override
    {
        context->startCurveCreation();
    }

    void stopCurveCreation(CurveCreatorContext* context) override
    {
        context->stopCurveCreation();
    }

    void setOnCreatedFn(CurveCreatorContext* context, OnCreatedFn onCreatedFn, void* userData) override
    {
        context->setOnCreatedFn(onCreatedFn, userData);
    }

    void setDesiredPlane(CurveCreatorContext* context, const carb::Float4& plane) override
    {
        context->setDesiredPlane(plane);
    }

    void setCvSpacing(CurveCreatorContext* context, float spacing) override
    {
        context->setCvSpacing(spacing);
    }

    void setCurveInterpolateType(CurveCreatorContext* context, CurveInterpolateTypes type) override
    {
        context->setCurveInterpolateType(type);
    }

    void onRaycast(CurveCreatorContext* context,
                   const carb::Float3& orig,
                   const carb::Float3& dir,
                   bool input,
                   const carb::Double3* snapWorldPos) override
    {
        context->onRaycast(orig, dir, input, snapWorldPos);
    }
};
}
}

CARB_PLUGIN_IMPL(kPluginImpl, omni::curvecreator::CurveCreatorInterfaceImpl)

void fillInterface(omni::curvecreator::CurveCreatorInterfaceImpl& iface)
{
}

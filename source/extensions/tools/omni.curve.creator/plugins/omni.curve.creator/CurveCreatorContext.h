// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <carb/eventdispatcher/IEventDispatcher.h>
#include <carb/settings/SettingsUtils.h>

#include <omni/curvecreator/CurveCreatorTypes.h>
#include <omni/curvecreator/ICurveCreator.h>
#include <omni/math/linalg/vec.h>

#include <vector>

using omni::math::linalg::vec3f;
using omni::math::linalg::vec4f;

namespace omni
{
namespace kit
{
struct IViewport;
struct StageUpdateNode;
class IViewportWindow;
}

namespace renderer
{
struct IDebugDraw;
}

namespace curvecreator
{

/**
 * Refer to public API documentation in ICurveCreator.h.
 */
class CurveCreatorContext
{
public:
    CurveCreatorContext(
        const carb::Float4& plane, float spacing, CurveInterpolateTypes type, OnCreatedFn onCreatedFn, void* userData);

    ~CurveCreatorContext();

    void startCurveCreation();

    void stopCurveCreation();

    void setOnCreatedFn(OnCreatedFn onCreatedFn, void* userData)
    {
        m_onCreatedFn = onCreatedFn;
        m_userData = userData;
    }

    void setDesiredPlane(const carb::Float4& plane)
    {
        m_desiredPlane = *reinterpret_cast<const vec4f*>(&plane);
    }

    void setCvSpacing(float spacing)
    {
        m_spacing = spacing;
    }

    void setCurveInterpolateType(CurveInterpolateTypes type)
    {
        m_type = type;
    }

    void onRaycast(const carb::Float3& orig, const carb::Float3& dir, bool input, const carb::Double3* snapWorldPos);

private:
    void onUpdate();

    void updateRendering();

    bool getIntersectionPointOnPlaneOrMesh(const vec3f& origin,
                                           const vec3f& direction,
                                           vec3f& intersection,
                                           const carb::Double3* snapWorldPos) const;

    bool getIntersectionPointOnDesiredCurvePlane(const vec3f& origin, const vec3f& direction, vec3f& intersection) const;

#if SUPPORT_VP1
    omni::kit::IViewportWindow* getHoveredViewportWindow() const;

    bool shouldSnapToSurface() const;

    void onRaycast(const float* orig, const float* dir, bool input);

    omni::kit::IViewport* m_viewport = nullptr;
    omni::kit::StageUpdateNode* m_stageUpdateNode = nullptr;

    carb::settings::ThreadSafeLocalCache<bool> m_snapEnabled;
    carb::settings::ThreadSafeLocalCache<bool> m_snapToSurface;
    bool m_needRequestPicking = false;
#endif

    vec4f m_desiredPlane = { 0, 1, 0, 0 };
    float m_spacing = 50;
    CurveInterpolateTypes m_type = CurveInterpolateTypes::eLinear;
    OnCreatedFn m_onCreatedFn = nullptr;
    void* m_userData = nullptr;

    carb::settings::ISettings* m_settings = nullptr;
    carb::eventdispatcher::ObserverGuard m_updateEvtSub;

    // for viz
    omni::renderer::IDebugDraw* m_debugDraw = nullptr;

    bool m_wasInput = false;

    std::vector<vec3f> m_creatorStroke;

    bool m_creating = false;
};
}
}

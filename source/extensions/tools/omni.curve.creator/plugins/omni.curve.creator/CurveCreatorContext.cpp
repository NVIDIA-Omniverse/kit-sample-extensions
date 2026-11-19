// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "CurveCreatorContext.h"

#include <omni/curvecreator/ICurveCreator.h>
#include <omni/kit/IApp.h>
#include <omni/kit/IStageUpdate.h>
#include <omni/kit/SettingsUtils.h>
#include <omni/kit/IViewport.h>
#include <omni/math/linalg/matrix.h>
#include <omni/math/linalg/vec.h>
#include <omni/renderer/IDebugDraw.h>

using namespace carb;
using namespace omni::curvecreator;
using omni::math::linalg::GfIsClose;
using omni::math::linalg::matrix4d;

static constexpr char kSnapEnabledSetting[] = "/app/viewport/snapEnabled";
static constexpr char kSnapToSurfaceSetting[] = PERSISTENT_SETTINGS_PREFIX "/app/viewport/snapToSurface";

namespace omni
{
namespace curvecreator
{

CurveCreatorContext::CurveCreatorContext(
    const carb::Float4& plane, float spacing, CurveInterpolateTypes type, OnCreatedFn onCreatedFn, void* userData)
    : m_desiredPlane(*reinterpret_cast<const vec4f*>(&plane)),
      m_spacing(spacing),
      m_type(type),
      m_onCreatedFn(onCreatedFn),
      m_userData(userData)
{
    m_settings = carb::getCachedInterface<carb::settings::ISettings>();
    m_debugDraw = carb::getCachedInterface<omni::renderer::IDebugDraw>();

    auto ed = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
    m_updateEvtSub = ed->observeEvent(carb::RStringKey("omni.curve.creator/update"),
        carb::eventdispatcher::kDefaultOrder, omni::kit::kGlobalEventUpdate,
        [this](const carb::eventdispatcher::Event&) { onUpdate(); });

#if SUPPORT_VP1
    // Make VP1 optional, and move to VP2 eventually
    m_viewport = carb::getFramework()->tryAcquireInterface<omni::kit::IViewport>();

    m_snapEnabled.startTracking(kSnapEnabledSetting);
    m_snapToSurface.startTracking(kSnapToSurfaceSetting);

    // For VP1 only
    auto onRayCast = [](const float* orig, const float* dir, bool input, void* userData)
    {
        CurveCreatorContext* _this = reinterpret_cast<CurveCreatorContext*>(userData);
        _this->onRaycast(orig, dir, input);
    };

    omni::kit::StageUpdateNodeDesc desc = { 0 };
    desc.displayName = "CurveCreator";
    desc.onRaycast = onRayCast;
    desc.userData = this;

    omni::kit::StageUpdatePtr iStageUpdate =
        carb::getFramework()->tryAcquireInterface<omni::kit::IStageUpdate>()->getStageUpdate();
    m_stageUpdateNode = iStageUpdate->createStageUpdateNode(desc);
#endif
}

CurveCreatorContext::~CurveCreatorContext()
{
    m_updateEvtSub.reset();

#if SUPPORT_VP1
    m_snapEnabled.stopTracking();
    m_snapToSurface.stopTracking();

    if (m_stageUpdateNode)
    {
        omni::kit::StageUpdatePtr iStageUpdate =
            carb::getFramework()->tryAcquireInterface<omni::kit::IStageUpdate>()->getStageUpdate();
        iStageUpdate->destroyStageUpdateNode(m_stageUpdateNode);
        m_stageUpdateNode = nullptr;
    }
#endif
}

void CurveCreatorContext::startCurveCreation()
{
    m_creating = true;
}

void CurveCreatorContext::stopCurveCreation()
{
    m_creating = false;
}

void CurveCreatorContext::onUpdate()
{
    updateRendering();

#if SUPPORT_VP1
    if (m_needRequestPicking)
    {
        auto viewportWindow = getHoveredViewportWindow();
        if (viewportWindow)
        {
            viewportWindow->requestPicking();
        }
        m_needRequestPicking = false;
    }
#endif
}

void CurveCreatorContext::updateRendering()
{
    if (!m_creatorStroke.empty())
    {
        std::vector<omni::renderer::SimplexPoint> linesVec;
        linesVec.reserve(m_creatorStroke.size() * 2);
        for (size_t i = 0; i < m_creatorStroke.size() - 1; i++)
        {
            linesVec.push_back({ *reinterpret_cast<carb::Float3*>(&m_creatorStroke[i]), 0xFFFFFFFF, 2 });
            linesVec.push_back({ *reinterpret_cast<carb::Float3*>(&m_creatorStroke[i + 1]), 0xFFFFFFFF, 2 });
        }

        m_debugDraw->drawLines(linesVec.data(), (uint32_t)(linesVec.size() / 2));
    }
}

bool CurveCreatorContext::getIntersectionPointOnPlaneOrMesh(const vec3f& origin,
                                                            const vec3f& direction,
                                                            vec3f& intersection,
                                                            const carb::Double3* snapWorldPos) const
{
    bool hasIntersection = false;
    if (snapWorldPos)
    {
        intersection[0] = (float)snapWorldPos->x;
        intersection[1] = (float)snapWorldPos->y;
        intersection[2] = (float)snapWorldPos->z;
        hasIntersection = true;
    }
    else
    {
        if (getIntersectionPointOnDesiredCurvePlane(origin, direction, intersection))
        {
            hasIntersection = true;
        }
    }
    return hasIntersection;
}

bool CurveCreatorContext::getIntersectionPointOnDesiredCurvePlane(const vec3f& origin,
                                                                  const vec3f& direction,
                                                                  vec3f& intersection) const
{
    const vec3f* planeNormal = reinterpret_cast<const vec3f*>(&m_desiredPlane);
    vec3f pointOnPlane = *planeNormal * m_desiredPlane[3];

    float t = (pointOnPlane - origin) * *planeNormal / (direction * *planeNormal);

    if (t >= 0)
    {
        intersection = origin + t * direction;
        return true;
    }

    return false;
}

#if SUPPORT_VP1
omni::kit::IViewportWindow* CurveCreatorContext::getHoveredViewportWindow() const
{
    if (!m_viewport)
    {
        return nullptr;
    }

    omni::kit::IViewportWindow* hoveredViewport = nullptr;
    size_t viewportCount = m_viewport->getViewportWindowInstanceCount();
    std::vector<omni::kit::ExtensionWindowHandle> vpHandles(viewportCount);
    m_viewport->getViewportWindowInstances(vpHandles.data(), viewportCount);

    for (const auto& handle : vpHandles)
    {
        omni::kit::IViewportWindow* vp = m_viewport->getViewportWindow(handle);
        if (vp && vp->isContentRegionHovered())
        {
            hoveredViewport = vp;
            break;
        }
    }

    return hoveredViewport;
}

bool CurveCreatorContext::shouldSnapToSurface() const
{
    return m_viewport && m_snapEnabled.get() && m_snapToSurface.get();
}

// This onRaycast is only used by VP1/StageUpdate
void CurveCreatorContext::onRaycast(const float* orig, const float* dir, bool input)
{
    if (!orig || !dir)
    {
        return;
    }

    if (!m_creating)
    {
        return;
    }

    auto viewportWindow = getHoveredViewportWindow();
    if (viewportWindow)
    {

        carb::Double3 snapWorldPos;
        bool hasSnapWorldPos = false;

        if (shouldSnapToSurface())
        {
            m_needRequestPicking = true;
            hasSnapWorldPos = viewportWindow->getPickedWorldPos(snapWorldPos);
        }

        const carb::Float3* origin = reinterpret_cast<const carb::Float3*>(orig);
        const carb::Float3* direction = reinterpret_cast<const carb::Float3*>(dir);

        onRaycast(*origin, *direction, input, hasSnapWorldPos ? &snapWorldPos : nullptr);
    }
}
#endif

void CurveCreatorContext::onRaycast(const carb::Float3& orig,
                                    const carb::Float3& dir,
                                    bool input,
                                    const carb::Double3* snapWorldPos)
{
    vec3f origin(orig.x, orig.y, orig.z);
    vec3f direction(dir.x, dir.y, dir.z);

    direction.Normalize();

    if (input)
    {
        vec3f intersection;
        if (getIntersectionPointOnPlaneOrMesh(origin, direction, intersection, snapWorldPos))
        {
            if (m_creatorStroke.empty())
            {
                m_creatorStroke.emplace_back(intersection[0], intersection[1], intersection[2]);
            }
            else
            {
                float epsilon = 1.e-4f;
                const auto& lastStamp = m_creatorStroke.back();
                if ((intersection - lastStamp).GetLengthSq() >= epsilon * epsilon)
                {
                    m_creatorStroke.emplace_back(intersection[0], intersection[1], intersection[2]);
                }
            }
        }
    }
    else if (m_wasInput)
    {
        if (!m_creatorStroke.empty())
        {
            std::vector<vec3f> resampled;

            resampled.reserve(m_creatorStroke.size()); // How much to reserve??
            resampled.push_back(m_creatorStroke[0]);

            // resample the stroke at m_spacing interval
            for (size_t i = 0; i < m_creatorStroke.size() - 1;)
            {
                const auto& lastResampled = resampled.back();

                const auto& segStart = m_creatorStroke[i];
                const auto& segEnd = m_creatorStroke[i + 1];

                auto segDir = segEnd - segStart;
                float segLen = segDir.Normalize();

                // only test intersection if the endpoint is outside of sphere
                if ((segEnd - lastResampled).GetLengthSq() >= m_spacing * m_spacing)
                {
                    // find the intersecting point between line segment and sphere with radius of spacing
                    // Solve the equations for t
                    // - point on Line: p = segStart + segDir * t
                    // - point on Sphere: || p - lastResampled || ^ 2 = spacing * spacing
                    auto startToLastSample = segStart - lastResampled;

                    float a = segDir * segDir;
                    float b = 2.f * startToLastSample * segDir;
                    float c = startToLastSample * startToLastSample - m_spacing * m_spacing;

                    float discriminant = b * b - 4 * a * c;
                    if (discriminant >= 0.f)
                    {
                        float sqrtDiscriminant = sqrt(discriminant);
                        float t = (-b + sqrtDiscriminant) / (2.f * a); // always use the bigger one, otherwise it might
                                                                       // find backward
                        if (t >= 0 && t <= segLen)
                        {
                            auto point = segStart + t * segDir;
                            resampled.push_back(point);
                            continue; // skip i++
                        }
                    }
                }

                i++;
            }

            // Add the last point from stroke, even if the spacing is lesser than settings.
            if (resampled.size() == 0 || !GfIsClose(resampled.back(), m_creatorStroke.back(), 1e-6))
            {
                resampled.push_back(m_creatorStroke.back());
            }

            // Insert tangents if cubic
            if (resampled.size() >= 2 && m_type == CurveInterpolateTypes::eCubic)
            {
                // TODO replace with a more mathematically correct curve fitting algorithm

                std::vector<vec3f> resampledWithTangents;
                resampledWithTangents.reserve(resampled.size() * 3 - 2);
                const float kFactor = 0.125f;

                for (size_t i = 0; i < resampled.size(); i++)
                {
                    vec3f tgt(0, 0, 0);

                    if (i > 0 && i < resampled.size() - 1)
                    {
                        tgt = resampled[i + 1] - resampled[i - 1];

                        resampledWithTangents.push_back(resampled[i] - tgt * kFactor);
                        resampledWithTangents.push_back(resampled[i]);
                        resampledWithTangents.push_back(resampled[i] + tgt * kFactor);
                    }

                    else if (i == 0)
                    {
                        tgt = (resampled[i + 1] - resampled[i]);
                        resampledWithTangents.push_back(resampled[i]);
                        resampledWithTangents.push_back(resampled[i] + tgt * 2.f * kFactor);
                    }

                    else if (i + 1 == resampled.size())
                    {
                        tgt = (resampled[i] - resampled[i - 1]);
                        resampledWithTangents.push_back(resampled[i] - tgt * 2.f * kFactor);
                        resampledWithTangents.push_back(resampled[i]);
                    }
                }
                resampled = std::move(resampledWithTangents);
            }

            if (m_onCreatedFn)
            {
                m_onCreatedFn(
                    reinterpret_cast<const carb::Float3*>(resampled.data()), resampled.size(), m_type, m_userData);
            }

            m_creatorStroke.clear();
        }
    }

    m_wasInput = input;
}

}
}

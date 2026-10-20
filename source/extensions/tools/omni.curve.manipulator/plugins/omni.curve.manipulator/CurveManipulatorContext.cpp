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

#include "CurveManipulatorContext.h"

#ifdef _MSC_VER
#    pragma warning(disable : 4996)
#endif

#include <carb/PluginUtils.h>
#include <carb/dictionary/DictionaryUtils.h>
#include <carb/extras/StringUtils.h>
#include <carb/settings/ISettings.h>

#include <omni/curvecreator/ICurveCreator.h>
#include <omni/curvemanipulator/ICurveManipulator.h>
#include <omni/kit/IApp.h>
#include <omni/kit/IStageUpdate.h>
#include <omni/kit/PythonInterOpHelper.h>
#include <omni/kit/IViewport.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/renderer/IDebugDraw.h>
#include <omni/usd/Selection.h>
#include <omni/usd/UsdContext.h>
#include <omni/usd/UsdUtils.h>

#include <array>
#include <bitset>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <unordered_set>


using namespace carb;

using namespace omni::curvemanipulator;
using namespace omni::usd;

using omni::math::linalg::matrix4d;
using omni::math::linalg::matrix4f;
using omni::math::linalg::safeCastToOmni;
using omni::math::linalg::vec2f;
using omni::math::linalg::vec3f;

using namespace omni::geometry::curves;

static constexpr char kViewportOutlineColorPath[] = PERSISTENT_SETTINGS_PREFIX "/app/viewport/outline/color";
static const double kTolerance = 1e-4;

static constexpr char kSnapEnabledSetting[] = "/app/viewport/snapEnabled";
static constexpr char kSnapToSurfaceSetting[] = PERSISTENT_SETTINGS_PREFIX "/app/viewport/snapToSurface";

static constexpr char kPencilToolInterpolateModeSetting[] =
    PERSISTENT_SETTINGS_PREFIX "/exts/omni.curve.manipulator/pencilToolInterpolateMode";
static constexpr char kPencilToolSpacingSetting[] =
    PERSISTENT_SETTINGS_PREFIX "/exts/omni.curve.manipulator/pencilToolSpacing";


namespace carb
{
namespace dictionary
{
namespace v1
{
template <>
inline Item* IDictionary::makeAtPathS<std::vector<const char*>*, true>(dictionary::Item* baseItem,
                                                                       cpp::string_view path,
                                                                       std::vector<const char*>* value)
{
    dictionary::Item* item = baseItem;
    if (!path.empty() && path[0] != '\0')
    {
        item = makeDictionaryAtPathS(baseItem, path);
    }

    setArray(item, value->data(), value->size());
    return item;
}
}
}
}

namespace omni
{
namespace curvemanipulator
{

bool static validateTopology(const TfToken& type, const TfToken& wrap, const TfToken& basis, size_t curveVertexCount)
{
    if (type == UsdGeomTokens->linear)
    {
        if (wrap == UsdGeomTokens->nonperiodic)
        {
            return curveVertexCount >= 2;
        }
        else if (wrap == UsdGeomTokens->periodic)
        {
            return curveVertexCount >= 3;
        }
        else
        {
            return false;
        }
    }
    else if (type == UsdGeomTokens->cubic)
    {
        uint8_t vstep = 0;
        if (basis == UsdGeomTokens->bezier)
        {
            vstep = 3;
        }
        else if (basis == UsdGeomTokens->catmullRom || basis == UsdGeomTokens->bspline)
        {
            vstep = 1;
        }
        else
        {
            return false;
        }

        if (wrap == UsdGeomTokens->nonperiodic)
        {
            return curveVertexCount >= 4 && (curveVertexCount - 4) % vstep == 0;
        }
        else if (wrap == UsdGeomTokens->periodic)
        {
            return curveVertexCount % vstep == 0;
        }
        else if (wrap == UsdGeomTokens->pinned)
        {
            return curveVertexCount >= 2;
        }
        else
        {
            return false;
        }
    }

    return false;
}

CurveManipulatorContext::CurveManipulatorContext(const char* usdContextName /*= ""*/)
{
    m_eventStream = events::getCachedEventsInterface()->createEventStream();

    m_usdContext = UsdContext::getContext(usdContextName);
    m_settings = carb::getCachedInterface<carb::settings::ISettings>();
    m_debugDraw = carb::getCachedInterface<omni::renderer::IDebugDraw>();

    m_updateEvtSub = carb::events::createSubscriptionToPop(
        carb::getCachedInterface<omni::kit::IApp>()->getUpdateEventStream(),
        [this](carb::events::IEvent* e) { onUpdate(); }, carb::events::kDefaultOrder, "Curve Manipulator");

    m_stageEvtSub = carb::events::createSubscriptionToPop(
        m_usdContext->getStageEventStream().get(),
        [this](carb::events::IEvent* e)
        {
            auto stageEventType = static_cast<StageEventType>(e->type);
            if (stageEventType == StageEventType::eOpened)
            {
                onStageOpened();
            }
            else if (stageEventType == StageEventType::eClosing)
            {
                onStageClosing();
            }
        },
        carb::events::kDefaultOrder, "Curve Manipulator");

#if SUPPORT_VP1
    // Make VP1 optional, and move to VP2 eventually
    m_viewport = carb::getFramework()->tryAcquireInterface<omni::kit::IViewport>();

    m_snapEnabled.startTracking(kSnapEnabledSetting);
    m_snapToSurface.startTracking(kSnapToSurfaceSetting);

    // For VP1 only
    omni::kit::StageUpdatePtr iStageUpdate =
        carb::getFramework()->tryAcquireInterface<omni::kit::IStageUpdate>()->getStageUpdate();

    auto onRayCast = [](const float* orig, const float* dir, bool input, void* userData)
    {
        CurveManipulatorContext* _this = reinterpret_cast<CurveManipulatorContext*>(userData);
        _this->onRaycast(orig, dir, input);
    };

    omni::kit::StageUpdateNodeDesc desc = { 0 };
    desc.displayName = "CurveManipulator";
    desc.onRaycast = onRayCast;
    desc.userData = this;
    desc.order = -1; // called before CurveCreator to set parameters

    m_stageUpdateNode = iStageUpdate->createStageUpdateNode(desc);
#endif

    m_settings->setDefault(kPencilToolInterpolateModeSetting, "cubic");
    m_settings->setDefault(kPencilToolSpacingSetting, 50.f);

    m_curveCreator = getCachedInterface<omni::curvecreator::ICurveCreator>();
    m_curveCreatorContext = m_curveCreator->createContext();

    m_curveCreator->setOnCreatedFn(
        m_curveCreatorContext,
        [](const carb::Float3* points, size_t count, CurveInterpolateTypes type, void* userdata)
        {
            CurveManipulatorContext* _this = reinterpret_cast<CurveManipulatorContext*>(userdata);
            _this->onCurveCreated(points, count, type);
        },
        this);

    m_pencilToolInterpolateModeSubId = m_settings->subscribeToNodeChangeEvents(
        kPencilToolInterpolateModeSetting,
        [](const dictionary::Item* changedItem, dictionary::ChangeEventType eventType, void* userData)
        {
            auto _this = reinterpret_cast<CurveManipulatorContext*>(userData);
            auto dict = getCachedInterface<dictionary::IDictionary>();
            auto interpolateModeStr = dictionary::detail::getStringView(dict, changedItem);

            _this->m_curveCreator->setCurveInterpolateType(
                _this->m_curveCreatorContext,
                interpolateModeStr == "cubic" ? CurveInterpolateTypes::eCubic : CurveInterpolateTypes::eLinear);
        },
        this);
    std::string interpolateModeStr = m_settings->getStringBuffer(kPencilToolInterpolateModeSetting);
    m_curveCreator->setCurveInterpolateType(m_curveCreatorContext, interpolateModeStr == "cubic" ?
                                                                       CurveInterpolateTypes::eCubic :
                                                                       CurveInterpolateTypes::eLinear);

    m_pencilToolSpacingSubId = m_settings->subscribeToNodeChangeEvents(
        kPencilToolSpacingSetting,
        [](const dictionary::Item* changedItem, dictionary::ChangeEventType eventType, void* userData)
        {
            auto _this = reinterpret_cast<CurveManipulatorContext*>(userData);
            float spacing = getCachedInterface<dictionary::IDictionary>()->getAsFloat(changedItem);

            _this->m_curveCreator->setCvSpacing(_this->m_curveCreatorContext, spacing);
        },
        this);
    m_curveCreator->setCvSpacing(m_curveCreatorContext, m_settings->getAsFloat(kPencilToolSpacingSetting));

    if (m_usdContext->getStageState() == StageState::eOpened)
    {
        onStageOpened();
    }
}

CurveManipulatorContext::~CurveManipulatorContext()
{
    onStageClosing();

    m_curveCreator->destroyContext(m_curveCreatorContext);
    m_curveCreatorContext = nullptr;

    m_settings->unsubscribeToChangeEvents(m_pencilToolInterpolateModeSubId);
    m_settings->unsubscribeToChangeEvents(m_pencilToolSpacingSubId);
    m_updateEvtSub = nullptr;
    m_stageEvtSub = nullptr;

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

    m_eventStream = nullptr;
}

void CurveManipulatorContext::enableCurveEditingMode(const char** paths, size_t count, CurveEditingModeType mode)
{
    bool wasInEditingMode = !m_curves.empty();

    std::vector<const char*> enabledPaths;
    enabledPaths.reserve(count);

    for (size_t i = 0; i < count; i++)
    {
        SdfPath path = SdfPath(paths[i]);
        auto basisCurves = UsdGeomBasisCurves::Get(m_stage, path);
        if (basisCurves)
        {
            m_curves[path] = std::make_unique<CurvesPrimData>(basisCurves);
            enabledPaths.push_back(paths[i]);
        }
    }

    m_editingMode = mode;

    if (m_editingMode == CurveEditingModeType::eDraw)
    {
        m_curveCreator->startCurveCreation(m_curveCreatorContext);
    }

    m_eventStream->push((uint64_t)CurvesEventType::eBeginCurveEdit, std::make_pair("mode", (int32_t)mode),
                        std::make_pair("paths", &enabledPaths));
}

bool CurveManipulatorContext::isInCurveEditingMode() const
{
    return !m_curves.empty();
}

size_t CurveManipulatorContext::getEditingCurvePathsCount() const
{
    return m_curves.size();
}

void CurveManipulatorContext::getEditingCurvePaths(const char** primPaths) const
{
    size_t i = 0;
    for (const auto& entry : m_curves)
    {
        primPaths[i++] = entry.first.GetText();
    }
}

void CurveManipulatorContext::disableCurveEditingMode()
{
    if (m_editingMode == CurveEditingModeType::eDraw)
    {
        m_curveCreator->stopCurveCreation(m_curveCreatorContext);
    }

    m_hasSampledPoint = false;
    m_curves.clear();
    m_eventStream->push((uint64_t)CurvesEventType::eEndCurveEdit);
}

carb::events::IEventStream* CurveManipulatorContext::getCurvesEventStream()
{
    return m_eventStream.get();
}

CurveEditingModeType CurveManipulatorContext::getCurveEditingMode() const
{
    return m_editingMode;
}

void CurveManipulatorContext::setAddingCurveToBasisCurves(bool value)
{
    m_addingCurveToBasisCurves = value;
}

void CurveManipulatorContext::setCurveEditingMode(CurveEditingModeType mode)
{
    if (mode != m_editingMode)
    {
        if (m_editingMode == CurveEditingModeType::eDraw)
        {
            m_curveCreator->stopCurveCreation(m_curveCreatorContext);
        }
        m_editingMode = mode;
        if (m_editingMode == CurveEditingModeType::eDraw)
        {
            m_curveCreator->startCurveCreation(m_curveCreatorContext);
        }
        m_eventStream->push((uint64_t)CurvesEventType::eCurveEditModeChanged, std::make_pair("mode", (int32_t)mode));
    }
}


void CurveManipulatorContext::onStageOpened()
{
    m_stage = m_usdContext->getStage();
    m_isAddingCv = false;
}

void CurveManipulatorContext::onStageClosing()
{
    m_stage = nullptr;
    if (isInCurveEditingMode())
    {
        disableCurveEditingMode();
    }
}

void CurveManipulatorContext::onUpdate()
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
    m_raycastFromVP1 = false;
#endif
    m_eventStream->pump();
}

void CurveManipulatorContext::updateRendering()
{
    if (!m_stage)
    {
        return;
    }

    if (!m_debugDraw)
    {
        return;
    }

    static const uint32_t kColorWhite = 0xFFFFFFFF;
    static const uint32_t kColorRed = 0xFFFF0000;
    static const uint32_t kColorGray = 0xFF808080;
    static const float kPointSize = 10.f;

    UsdGeomXformCache xformCache;

    if (m_hasSampledPoint)
    {
        // just draw both for normal z and reversed z to handle both cases
        m_debugDraw->drawPoint(*reinterpret_cast<carb::Float3*>(&m_sampledPointWorldPosition), kColorRed, kPointSize);
        m_debugDraw->drawPoint(
            *reinterpret_cast<carb::Float3*>(&m_sampledPointWorldPositionReversedZ), kColorRed, kPointSize);

#if SUPPORT_VP1
        // always clear m_hasSampledPoint if from VP1, VP1 set m_hasSampledPoint every frame during raycast
        if (m_raycastFromVP1)
        {
            m_hasSampledPoint = false;
        }
#endif
    }

    if (m_isAddingCv)
    {
        auto basisCurves = getAddingCvCurves();
        if (basisCurves.GetPrim().IsValid())
        {
            TfToken basis;
            basisCurves.GetBasisAttr().Get(&basis);

            TfToken type;
            basisCurves.GetTypeAttr().Get(&type);

            // Only draw tangents for cubic bezier
            if (basis == UsdGeomTokens->bezier && type == UsdGeomTokens->cubic)
            {
                GfMatrix4d worldXform = UsdUtils::getWorldTransformMatrix(basisCurves.GetPrim());
                auto pointsAttr = basisCurves.GetPointsAttr();
                VtVec3fArray points;
                pointsAttr.Get(&points);

                VtIntArray curveVertexCounts;
                basisCurves.GetCurveVertexCountsAttr().Get(&curveVertexCounts);

                if (!curveVertexCounts.empty())
                {
                    size_t lastCurveVertexCount = curveVertexCounts.back();
                    if (lastCurveVertexCount >= 2)
                    {
                        TfToken wrap;
                        basisCurves.GetWrapAttr().Get(&wrap);

                        size_t offset = 0;
                        // no need to draw tangent if periodic and vert count > 2
                        if (wrap != UsdGeomTokens->periodic || lastCurveVertexCount <= 2)
                        {
                            const auto& lastCv = *(points.rbegin() + offset);
                            const auto& lastTangent = *(points.rbegin() + 1 + offset);

                            GfVec3f startPos;
                            GfVec3f endPos;

                            if (m_addingCurveToBasisCurves || lastCurveVertexCount == 2)
                            {
                                // tangent and cv are reversed for the first pair
                                startPos = GfVec3f(worldXform.Transform(lastTangent));
                                endPos = GfVec3f(worldXform.Transform(lastTangent - lastTangent + lastCv));
                            }
                            else
                            {
                                startPos = GfVec3f(worldXform.Transform(lastCv));
                                endPos = GfVec3f(worldXform.Transform(lastCv + lastCv - lastTangent));
                            }

                            m_debugDraw->drawLine(*reinterpret_cast<carb::Float3*>(&startPos), kColorGray,
                                                  *reinterpret_cast<carb::Float3*>(&endPos), kColorGray);
                        }
                    }
                }
            }
        }
        else
        {
            CARB_LOG_WARN("Manipulating invalid prim");
        }
    }
}

bool CurveManipulatorContext::getClosestPointOnCurves(const vec3f& origin,
                                                      const vec3f& direction,
                                                      const matrix4d& viewProjMtx,
                                                      const carb::Float4& viewportRect,
                                                      vec3f& closestPosition,
                                                      SdfPath& closestCurvesPath,
                                                      size_t& closestCurvetIndex,
                                                      size_t& closestSegmentStartIndex,
                                                      float& closestSegmentT,
                                                      const float pixelDistance /* = 50.f*/)
{
    float closestDistanceSqr = std::numeric_limits<float>::max();

    m_hasSampledPoint = false;

    if (m_curves.empty())
    {
        return false;
    }

    float rectWidth = viewportRect.z - viewportRect.x;
    float rectHeight = viewportRect.w - viewportRect.y;

    for (auto& entry : m_curves)
    {
        CARB_PROFILE_ZONE(1, "Find nearest point to mouse ray among all curves");

        const SdfPath& primPath = entry.first;
        auto& curvePrimData = entry.second;
        UsdGeomBasisCurves& basisCurvesPrim = curvePrimData->basisCurvesPrim;

        matrix4d curveToWorldMtx = safeCastToOmni(UsdUtils::getWorldTransformMatrix(basisCurvesPrim.GetPrim()));
        matrix4d worldToCurveMtx = curveToWorldMtx.GetInverse();

        vec3f curveSpaceOrigin = worldToCurveMtx.Transform(origin);
        // need to normalize again if the matrix has non-1 scaling
        vec3f curveSpaceDir = worldToCurveMtx.TransformDir(direction).GetNormalized();

        VtIntArray curveVertexCounts;
        basisCurvesPrim.GetCurveVertexCountsAttr().Get(&curveVertexCounts);

        TfToken type;
        basisCurvesPrim.GetTypeAttr().Get(&type);

        VtArray<GfVec3f> pointsUSD;
        basisCurvesPrim.GetPointsAttr().Get(&pointsUSD);

        TfToken wrap;
        basisCurvesPrim.GetWrapAttr().Get(&wrap);

        TfToken basis;
        basisCurvesPrim.GetBasisAttr().Get(&basis);

        std::vector<vec3f> points(safeCastToOmni(pointsUSD.data()), safeCastToOmni(pointsUSD.data() + pointsUSD.size()));

        const size_t kStepPerSegment = 10;

        size_t startIdx = 0;
        for (size_t i = 0; i < curveVertexCounts.size(); i++)
        {
            const size_t count = curveVertexCounts[i];
            // can only insert CV on a valid curve.
            if (!validateTopology(type, wrap, basis, count))
            {
                continue;
            }

            std::vector<vec3f> controlPoints(points.begin() + startIdx, points.begin() + startIdx + count);

            if (type == UsdGeomTokens->linear)
            {
                // repeat the last point
                if (wrap == UsdGeomTokens->periodic)
                {
                    controlPoints.push_back(controlPoints.front());
                }

                matrix4f ndcToScreen;
                ndcToScreen.SetScale(vec3f(rectWidth * 0.5f, rectHeight * 0.5f, 0.5f));
                ndcToScreen.SetTranslateOnly(vec3f(rectWidth * 0.5f, rectHeight * 0.5f, 0.5f));

                // Need to project the points into screen space to find the closes point on line segment.
                // It is visually more accurate than doing in other space.
                matrix4f curveToScreenSpaceMatrix = matrix4f(curveToWorldMtx * viewProjMtx) * ndcToScreen;
                vec3f rayOriginScreen3f = curveToScreenSpaceMatrix.Transform(origin);

                vec2f rayOriginScreen(rayOriginScreen3f[0], rayOriginScreen3f[1]);

                // Find the closest distance to each linear line segment from the view of ray dir.
                vec2f closestPositionThisCurve;
                float distanceSqrMinThisCurve = std::numeric_limits<float>::max();
                size_t closestSegmentStartIndexThisCurve;
                float closestSegmentTThisCurve;
                for (size_t j = 0; j + 1 < controlPoints.size(); j++)
                {
                    vec3f pStart3 = curveToScreenSpaceMatrix.Transform(controlPoints[j]);
                    vec2f pStart(pStart3[0], pStart3[1]);

                    vec3f pEnd3 = curveToScreenSpaceMatrix.Transform(controlPoints[j + 1]);
                    vec2f pEnd(pEnd3[0], pEnd3[1]);

                    vec2f lineDir = pEnd - pStart;
                    float lineLen = lineDir.Normalize();

                    vec2f startToRay = rayOriginScreen - pStart;
                    float projectedLenOnLine = startToRay * lineDir;

                    if (projectedLenOnLine >= 0 && projectedLenOnLine < lineLen)
                    {
                        vec2f startToProjected = lineDir * projectedLenOnLine;

                        float distanceSq = (startToProjected - startToRay).GetLengthSq();

                        if (distanceSq < distanceSqrMinThisCurve)
                        {
                            distanceSqrMinThisCurve = distanceSq;
                            closestPositionThisCurve = pStart + startToProjected;
                            closestSegmentStartIndexThisCurve = j;
                            closestSegmentTThisCurve = projectedLenOnLine / lineLen;
                        }
                    }
                }

                if (distanceSqrMinThisCurve < closestDistanceSqr &&
                    distanceSqrMinThisCurve < pixelDistance * pixelDistance)
                {
                    closestDistanceSqr = distanceSqrMinThisCurve;
                    closestPosition = controlPoints[closestSegmentStartIndexThisCurve] +
                                      closestSegmentTThisCurve * (controlPoints[closestSegmentStartIndexThisCurve + 1] -
                                                                  controlPoints[closestSegmentStartIndexThisCurve]);
                    closestCurvesPath = basisCurvesPrim.GetPath();
                    closestCurvetIndex = i;
                    closestSegmentStartIndex = closestSegmentStartIndexThisCurve;
                    closestSegmentT = closestSegmentTThisCurve;

                    m_hasSampledPoint = true;
                }
            }
            else
            {
                // TODO make a proper closest point on cubic curve function
                std::map<float, std::vector<size_t>> distanceToIndicesMap; // ordered
                std::vector<vec3f> positions3d;

                // recreate it every time so that if any of curve attributes changed it can catch it.
                auto splineCurve = curvePrimData->createSplineCurve();
                splineCurve.tessellate(controlPoints.data(), controlPoints.size(), positions3d, kStepPerSegment, true);

                if (positions3d.size() == 0)
                {
                    continue;
                }

                bool thisCurveCloser = false;
                for (size_t j = 0; j < positions3d.size(); j++)
                {
                    vec3f originToTessellatedPoint = positions3d[j] - curveSpaceOrigin;
                    float projectedLengthOnRayDir = originToTessellatedPoint * curveSpaceDir;
                    float distanceSqr =
                        (positions3d[j] - (curveSpaceOrigin + curveSpaceDir * projectedLengthOnRayDir)).GetLengthSq();

                    distanceToIndicesMap[distanceSqr].push_back(j);
                }

                if (distanceToIndicesMap.empty())
                {
                    continue;
                }

                const auto& closestPointsEntry = distanceToIndicesMap.begin();

                // If there's already another curve that is closer, do not further sample on this curve.
                // There could be a chance if the sample step is not small enough we miss a closer point though..
                if (closestPointsEntry->first >= closestDistanceSqr)
                {
                    continue;
                }
                else
                {
                    closestDistanceSqr = closestPointsEntry->first;
                    closestPosition = positions3d[closestPointsEntry->second[0]];
                }


                size_t samplePerSegment = kStepPerSegment + 1; // + 1 from includeFinalSample
                float step = 1.f / kStepPerSegment;

                for (const size_t closestPointIndex : closestPointsEntry->second)
                {
                    CARB_PROFILE_ZONE(1, "Find nearest point to mouse ray");

                    size_t segmentIndex = closestPointIndex / samplePerSegment;
                    float t = (closestPointIndex % samplePerSegment) / (float)(samplePerSegment - 1);
                    size_t segmentStartIndex = segmentIndex * 3;

                    float startT = std::max(0.f, t - step);
                    float endT = std::min(1.f, t + step);
                    float midT = t;

                    size_t iteration = 0;
                    bool noPrecisionLeft = false; // t doesn't have enough precision to further divide. Happens on curve
                                                  // with very long segments
                    while (true)
                    {
                        auto sampleAndCalcDistanceSqr = [&splineCurve, &controlPoints, segmentStartIndex,
                                                         &curveSpaceOrigin, &curveSpaceDir](vec3f& sampledPoint, float t)
                        {
                            sampledPoint = splineCurve.evaluateSegment(
                                controlPoints.data(), controlPoints.size(), segmentStartIndex, t);

                            vec3f originToTessellatedPoint = sampledPoint - curveSpaceOrigin;
                            float projectedLengthOnRayDir = originToTessellatedPoint * curveSpaceDir;

                            return (sampledPoint - (curveSpaceOrigin + curveSpaceDir * projectedLengthOnRayDir))
                                .GetLengthSq();
                        };

                        vec3f closestPositionLo;
                        float midLoT = (startT + midT) / 2.f;
                        float distanceSqrLoT = sampleAndCalcDistanceSqr(closestPositionLo, midLoT);

                        vec3f closestPositionHi;
                        float midHiT = (midT + endT) / 2.f;
                        float distanceSqrHiT = sampleAndCalcDistanceSqr(closestPositionHi, midHiT);

                        if (distanceSqrLoT < closestDistanceSqr)
                        {
                            closestDistanceSqr = distanceSqrLoT;
                            closestPosition = closestPositionLo;
                            endT = midT;
                            midT = midLoT;
                        }
                        else if (distanceSqrHiT < closestDistanceSqr)
                        {
                            closestDistanceSqr = distanceSqrHiT;
                            closestPosition = closestPositionHi;
                            startT = midT;
                            midT = midHiT;
                        }
                        else
                        {
                            if (startT == midLoT && endT == midHiT)
                            {
                                noPrecisionLeft = true;
                            }
                            else
                            {
                                startT = midLoT;
                                endT = midHiT;
                            }
                        }

                        // If the bound is small enough, consider the point on curve is found.
                        if ((closestPositionLo - closestPositionHi).GetLengthSq() < 1e-6 || noPrecisionLeft)
                        {
                            t = midT;
                            closestCurvesPath = basisCurvesPrim.GetPath();
                            closestCurvetIndex = i;
                            closestSegmentStartIndex = segmentStartIndex;
                            closestSegmentT = t;

                            // Compare distance on screen space so curves afar can still be sampled easily
                            vec3f closestPositionWorld =
                                curveToWorldMtx.Transform(*reinterpret_cast<vec3f*>(&closestPosition));

                            // approximate closest pos on ray to curve
                            vec3f rayPos = origin + direction * ((closestPositionWorld - origin) * direction);
                            vec3f rayClipPos = viewProjMtx.Transform(rayPos);
                            vec3f closestClipPos = viewProjMtx.Transform(closestPositionWorld);

                            vec3f diff = rayClipPos - closestClipPos;
                            diff[0] *= rectWidth;
                            diff[1] *= rectHeight;
                            diff[2] = 0;

                            // If within N pixels
                            if (diff.GetLengthSq() < pixelDistance * pixelDistance)
                            {
                                m_hasSampledPoint = true;
                            }

                            CARB_LOG_VERBOSE("found curve t=%f in %llu iterations", t, iteration);
                            break;
                        }

                        if (iteration >= 40 || noPrecisionLeft)
                        {
                            CARB_LOG_WARN("Unable to find closest point with %llu iterations, quitting...", iteration);
                            break;
                        }

                        iteration++;
                    }
                }
            }

            startIdx += curveVertexCounts[i];
        }
    }

    return m_hasSampledPoint;
}

bool CurveManipulatorContext::getIntersectionPointOnPlaneOrMesh(const vec3f& origin,
                                                                const vec3f& direction,
                                                                const std::string& activeCameraPath,
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
        if (getIntersectionPointOnDesiredCurvePlane(origin, direction, activeCameraPath, intersection))
        {
            hasIntersection = true;
        }
    }
    return hasIntersection;
}

bool CurveManipulatorContext::getDesiredCurvePlaneBaseOnCamera(vec3f& planeNormal, const std::string& activeCameraPath) const
{
    static const std::string kPerspCamPath = "/OmniverseKit_Persp";
    static const std::string kFrontCamPath = "/OmniverseKit_Front";
    static const std::string kTopCamPath = "/OmniverseKit_Top";
    static const std::string kRightCamPath = "/OmniverseKit_Right";

    bool zUp = UsdGeomGetStageUpAxis(m_stage) == UsdGeomTokens->z;

    if (activeCameraPath == kFrontCamPath)
    {
        planeNormal = zUp ? vec3f::XAxis() : vec3f::ZAxis();
    }
    else if (activeCameraPath == kTopCamPath)
    {
        planeNormal = zUp ? vec3f::ZAxis() : vec3f::YAxis();
    }
    else if (activeCameraPath == kRightCamPath)
    {
        planeNormal = zUp ? vec3f::YAxis() : vec3f::XAxis();
    }
    else
    {
        // perspective and all other user created cameras
        planeNormal = zUp ? vec3f::ZAxis() : vec3f::YAxis();
    }

    return true;
}

bool CurveManipulatorContext::getIntersectionPointOnDesiredCurvePlane(const vec3f& origin,
                                                                      const vec3f& direction,
                                                                      const std::string& activeCameraPath,
                                                                      vec3f& intersection) const
{
    vec3f pointOnPlane(0.f);
    vec3f planeNormal;

    if (getDesiredCurvePlaneBaseOnCamera(planeNormal, activeCameraPath))
    {
        float t = (pointOnPlane - origin) * planeNormal / (direction * planeNormal);

        if (t >= 0)
        {
            intersection = origin + t * direction;
            return true;
        }
    }

    return false;
}

#if SUPPORT_VP1
omni::kit::IViewportWindow* CurveManipulatorContext::getHoveredViewportWindow() const
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

bool CurveManipulatorContext::shouldSnapToSurface() const
{
    return m_viewport && m_snapEnabled.get() && m_snapToSurface.get();
}

// This onRaycast is used by Viewport 1/StageUpdate only
void CurveManipulatorContext::onRaycast(const float* orig, const float* dir, bool input)
{
    if (!orig || !dir)
    {
        return;
    }

    if (m_curves.empty())
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

        const char* activeCameraPath = viewportWindow->getActiveCamera();
        UsdGeomCamera cameraPrim = UsdGeomCamera::Get(m_stage, SdfPath(activeCameraPath));
        GfCamera camera = cameraPrim.GetCamera(UsdTimeCode::Default());
        GfFrustum frustum = camera.GetFrustum();
        GfMatrix4d viewProjMtx = frustum.ComputeViewMatrix() * frustum.ComputeProjectionMatrix();
        carb::Float4 viewportRect = viewportWindow->getViewportRect();

        m_raycastFromVP1 = true;
        onRaycast(*origin, *direction, input, false, activeCameraPath, viewportRect, viewProjMtx.GetArray(),
                  hasSnapWorldPos ? &snapWorldPos : nullptr);
    }
}
#endif

void CurveManipulatorContext::onRaycast(const carb::Float3& orig,
                                        const carb::Float3& dir,
                                        bool input,
                                        bool end,
                                        const char* cameraPath,
                                        const carb::Float4& rect,
                                        const double* viewProjMatrix,
                                        const carb::Double3* snapWorldPos)
{
    if (m_curves.empty())
    {
        return;
    }

    vec3f origin(orig.x, orig.y, orig.z);
    vec3f direction(dir.x, dir.y, dir.z);
    const matrix4d viewProjMtx = *reinterpret_cast<const matrix4d*>(viewProjMatrix);

    direction.Normalize();

    if (m_editingMode == CurveEditingModeType::eDraw)
    {
        // TODO move m_editingMode == CurveEditingModeType::eDrag into ICurveCreator as well
        vec3f planeNormal;
        if (getDesiredCurvePlaneBaseOnCamera(planeNormal, cameraPath))
        {
            // TODO do this only when bound camera or up axis changed since last frame?
            m_curveCreator->setDesiredPlane(m_curveCreatorContext, { planeNormal[0], planeNormal[1], planeNormal[2], 0 });
        }

        m_curveCreator->onRaycast(m_curveCreatorContext, orig, dir, input, snapWorldPos);
    }
    else if (m_editingMode == CurveEditingModeType::eDrag)
    {
        if (!m_isAddingCv)
        {
            vec3f closestPosition;
            SdfPath closestCurvesPath;
            size_t closestCurvetIndex;
            size_t closestSegmentStartIndex;
            float closestSegmentT;
            getClosestPointOnCurves(origin, direction, viewProjMtx, rect, closestPosition, closestCurvesPath,
                                    closestCurvetIndex, closestSegmentStartIndex, closestSegmentT);

            if (m_hasSampledPoint)
            {
                CARB_LOG_VERBOSE("Closes sampled point is segment %llu, t %f", closestSegmentStartIndex, closestSegmentT);

                vec3f* curveSpaceClosestPoint = reinterpret_cast<vec3f*>(&closestPosition);
                auto closestWorldPos = safeCastToOmni(UsdUtils::getWorldTransformMatrix(
                                                          m_curves[closestCurvesPath]->basisCurvesPrim.GetPrim()))
                                           .Transform(*curveSpaceClosestPoint);

                auto projViewMtx = viewProjMtx.GetInverse();
                auto closestWorldPosNDC = viewProjMtx.Transform(closestWorldPos);
                closestWorldPosNDC[2] = -0.999f; // move the points to near plane so it's not occluded by curve render.
                m_sampledPointWorldPosition = projViewMtx.Transform(closestWorldPosNDC);
                closestWorldPosNDC[2] = 0.999f; // for reversed-z projection
                m_sampledPointWorldPositionReversedZ = projViewMtx.Transform(closestWorldPosNDC);

                if (!m_wasInput && input)
                {
                    m_eventStream->push(
                        (uint64_t)CurvesEventType::eInsert, std::make_pair("pathStr", closestCurvesPath.GetText()),
                        std::make_pair("segmentStartIndex", (int64_t)closestSegmentStartIndex),
                        std::make_pair("curveIndex", (int64_t)closestCurvetIndex), std::make_pair("t", closestSegmentT));
                }
            }
            else
            {
                if (!m_wasInput && input)
                {
                    vec3f intersection;
                    if (getIntersectionPointOnPlaneOrMesh(origin, direction, cameraPath, intersection, snapWorldPos))
                    {
                        m_isAddingCv = true;
                        m_eventStream->push((uint64_t)CurvesEventType::eBeginAdd,
                                            std::make_pair("pathStr", getAddingCvCurves().GetPath().GetText()),
                                            std::make_pair("pos_x", intersection[0]),
                                            std::make_pair("pos_y", intersection[1]),
                                            std::make_pair("pos_z", intersection[2]));
                    }
                }
            }
        }
        else
        {
            if (input)
            {
                vec3f intersection;
                if (getIntersectionPointOnPlaneOrMesh(origin, direction, cameraPath, intersection, snapWorldPos))
                {
                    m_eventStream->push((uint64_t)CurvesEventType::eAdding,
                                        std::make_pair("pathStr", getAddingCvCurves().GetPath().GetText()),
                                        std::make_pair("pos_x", intersection[0]),
                                        std::make_pair("pos_y", intersection[1]),
                                        std::make_pair("pos_z", intersection[2]));
                }
            }
            else
            {
                if (m_wasInput)
                {
                    m_isAddingCv = false;
                    m_eventStream->push((uint64_t)CurvesEventType::eEndAdd,
                                        std::make_pair("pathStr", getAddingCvCurves().GetPath().GetText()),
                                        std::make_pair("pos_x", 0.f), std::make_pair("pos_y", 0.f),
                                        std::make_pair("pos_z", 0.f));
                }
            }
        }
    }

    m_wasInput = input;

    if (end)
    {
        m_hasSampledPoint = false;
    }
}

void CurveManipulatorContext::onCurveCreated(const carb::Float3* points, size_t count, CurveInterpolateTypes type)
{
    auto event =
        m_eventStream->createEventPtr((uint64_t)CurvesEventType::eAddMultiplePoints, carb::events::kGlobalSenderId);
    event->setValues(std::make_pair("pathStr", getAddingCvCurves().GetPath().GetText()));
    event->setValues(std::make_pair("type", (int64_t)type));

    auto dict = carb::getCachedInterface<dictionary::IDictionary>();
    auto pointsDictItem = dict->makeDictionaryAtPath(event->payload, "points");

    // carb.dictionary has an internal array length limit of 1024 (see constexpr size_t kMaxArrayIndex = 1024;),
    // and if you're dynamically adding more items into the array, when it reaches 1024 it turns the dictionary from
    // array into unordered_map then when you try to retrieve the data back, they become unordered and all data are in
    // wrong order. This breaks points array with size > 1024.
    //
    // However, if the initial size of the array is over 1024, it can keep growing and stay as array, not
    // being converted into unordered_map. Thus here we pre-populate the array's capacity with (incorrect) floats to
    // "reserve" the size over 1024, then replace them with float3.
    dict->setArray(pointsDictItem, &(points[0].x), count);

    for (size_t i = 0; i < count; i++)
    {
        auto entryItem = dict->makeDictionaryAtPath(pointsDictItem, std::to_string(i).c_str());
        dict->setArray(entryItem, &(points[i].x), 3);
    }

    m_eventStream->push(event);
    event->release();
}

UsdGeomBasisCurves CurveManipulatorContext::getAddingCvCurves() const
{
    // TODO hmmm what's the best way to append new CV if multiple curves are selected??
    // for now just pick the first curve in the hashmap
    // Need better UI/UX for editing
    if (!m_curves.empty())
    {
        return m_curves.begin()->second->basisCurvesPrim;
    }
    return UsdGeomBasisCurves();
}
}
}

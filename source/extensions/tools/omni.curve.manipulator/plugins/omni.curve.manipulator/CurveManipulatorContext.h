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

#include <carb/events/EventsUtils.h>
#include <carb/events/IEvents.h>
#include <carb/settings/SettingsUtils.h>

#include <omni/curvemanipulator/ICurveManipulator.h>
#include <omni/geometry/Curves.h>
#include <omni/math/linalg/vec.h>

using omni::math::linalg::matrix4d;
using omni::math::linalg::vec3f;
using namespace PXR_NS;
using namespace omni::curvecreator;

namespace carb
{
namespace dictionary
{
struct SubscriptionId;
}
}

namespace omni
{
namespace kit
{
class IApp;
class IViewportWindow;
struct IViewport;
struct StageUpdateNode;
struct IStageUpdate;

}

namespace renderer
{
struct IDebugDraw;
}

namespace usd
{
class UsdContext;
}

namespace curvemanipulator
{

class CurveManipulatorContext
{
public:
    CurveManipulatorContext(const char* usdContextName = "");

    ~CurveManipulatorContext();

    void enableCurveEditingMode(const char** primPaths, size_t count, CurveEditingModeType mode);

    bool isInCurveEditingMode() const;

    size_t getEditingCurvePathsCount() const;

    void getEditingCurvePaths(const char** primPaths) const;

    void disableCurveEditingMode();

    carb::events::IEventStream* getCurvesEventStream();

    CurveEditingModeType getCurveEditingMode() const;

    void setAddingCurveToBasisCurves(bool value);

    void setCurveEditingMode(CurveEditingModeType mode);

    void onRaycast(const carb::Float3& origin,
                   const carb::Float3& dir,
                   bool input,
                   bool end,
                   const char* cameraPath,
                   const carb::Float4& rect,
                   const double* viewProjMatrix,
                   const carb::Double3* snapWorldPos);

private:
    void onStageOpened();

    void onStageClosing();

    void onUpdate();

    void updateRendering();

    bool getClosestPointOnCurves(const vec3f& origin,
                                 const vec3f& direction,
                                 const matrix4d& viewProjMtx,
                                 const carb::Float4& rect,
                                 vec3f& closestPosition,
                                 SdfPath& closestCurvesPath,
                                 size_t& closestCurvetIndex,
                                 size_t& closestSegmentStartIndex,
                                 float& closestSegmentT,
                                 const float pixelDistance = 50.f);

    bool getIntersectionPointOnPlaneOrMesh(const vec3f& origin,
                                           const vec3f& direction,
                                           const std::string& activeCameraPath,
                                           vec3f& intersection,
                                           const carb::Double3* snapWorldPos) const;

    bool getDesiredCurvePlaneBaseOnCamera(vec3f& planeNormal, const std::string& activeCameraPath) const;

    bool getIntersectionPointOnDesiredCurvePlane(const vec3f& origin,
                                                 const vec3f& direction,
                                                 const std::string& activeCameraPath,
                                                 vec3f& intersection) const;

    void onCurveCreated(const carb::Float3* points, size_t count, CurveInterpolateTypes type);

    UsdGeomBasisCurves getAddingCvCurves() const;


    struct CurvesPrimData
    {
        CurvesPrimData(UsdGeomBasisCurves _curves) : basisCurvesPrim(_curves)
        {
        }

        omni::geometry::curves::SplineCurve createSplineCurve()
        {
            using namespace omni::geometry::curves;

            TfToken basisToken;
            basisCurvesPrim.GetBasisAttr().Get(&basisToken);
            TfToken wrapToken;
            basisCurvesPrim.GetWrapAttr().Get(&wrapToken);

            eBasisCurveWrap wrapType = eBasisCurveWrap::Pinned;
            if (wrapToken == pxr::UsdGeomTokens->nonperiodic)
            {
                wrapType = eBasisCurveWrap::NonPeriodic;
            }
            else if (wrapToken == pxr::UsdGeomTokens->periodic)
            {
                wrapType = eBasisCurveWrap::Periodic;
            }
            else if (wrapToken == pxr::UsdGeomTokens->pinned)
            {
                wrapType = eBasisCurveWrap::Pinned;
            }

            eBasisCurveType curveType;
            if (basisToken == pxr::UsdGeomTokens->bspline)
            {
                curveType = eBasisCurveType::BSpline;
            }
            else if (basisToken == pxr::UsdGeomTokens->bezier)
            {
                curveType = eBasisCurveType::Bezier;
            }
            else if (basisToken == pxr::UsdGeomTokens->catmullRom)
            {
                curveType = eBasisCurveType::CatmullRom;
            }

            return SplineCurve(wrapType, curveType);
        }

        UsdGeomBasisCurves basisCurvesPrim;
    };

    carb::events::IEventStreamPtr m_eventStream;

    carb::settings::ISettings* m_settings = nullptr;
    omni::usd::UsdContext* m_usdContext = nullptr;
    carb::events::ISubscriptionPtr m_stageEvtSub;
    carb::events::ISubscriptionPtr m_updateEvtSub;

    // for viz
    omni::renderer::IDebugDraw* m_debugDraw = nullptr;

    UsdStageRefPtr m_stage;
    std::unordered_map<SdfPath, std::unique_ptr<CurvesPrimData>, SdfPath::Hash> m_curves;

    carb::dictionary::SubscriptionId* m_pencilToolInterpolateModeSubId;
    carb::dictionary::SubscriptionId* m_pencilToolSpacingSubId;

    bool m_hasSampledPoint = false;
    vec3f m_sampledPointWorldPosition{ 0.f, 0.f, 0.f };
    vec3f m_sampledPointWorldPositionReversedZ{ 0.f, 0.f, 0.f };
    bool m_wasInput = false;

    bool m_isAddingCv = false;

#if SUPPORT_VP1
    omni::kit::IViewportWindow* getHoveredViewportWindow() const;

    bool shouldSnapToSurface() const;

    void onRaycast(const float* orig, const float* dir, bool input);

    omni::kit::IViewport* m_viewport = nullptr;
    omni::kit::StageUpdateNode* m_stageUpdateNode = nullptr;

    carb::settings::ThreadSafeLocalCache<bool> m_snapEnabled;
    carb::settings::ThreadSafeLocalCache<bool> m_snapToSurface;
    bool m_needRequestPicking = false;
    bool m_raycastFromVP1 = false;
#endif

    bool m_addingCurveToBasisCurves = false;
    CurveEditingModeType m_editingMode;
    omni::curvecreator::ICurveCreator* m_curveCreator = nullptr;
    omni::curvecreator::CurveCreatorContext* m_curveCreatorContext = nullptr;
};
}
}

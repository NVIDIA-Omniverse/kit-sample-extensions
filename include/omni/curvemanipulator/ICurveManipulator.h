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

#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>

#include <omni/curvecreator/ICurveCreator.h>

namespace carb
{
namespace events
{
class IEventStream;
}
}

namespace omni
{
namespace curvemanipulator
{

class CurveManipulatorContext;

enum class CurvesEventType : uint64_t
{
    eInsert = 0, ///! Insert a CV on existing curve
    eBeginAdd = 1, ///! Adding a new CV (mouse begins drag)
    eAdding = 2, ///! Adding a new CV (mouse is dragging)
    eEndAdd = 3, ///! Finished adding a new CV (mouse just released)
    eAddMultiplePoints = 4, ///! A curve was created but should be added to an existing curve.
    eBeginCurveEdit = 5, ///! Curve editing just started.
    eEndCurveEdit = 6, ///! Curve editing just ended.
    eCurveEditModeChanged = 7 ///! Curve editing mode changed.
};

enum class CurveEditingModeType : int32_t
{
    eDrag,
    eDraw,
};

class ICurveManipulator
{
public:
    CARB_PLUGIN_INTERFACE("omni::curvemanipulator::ICurveManipulator", 3, 2);

    virtual CurveManipulatorContext* createContext(const char* usdContextName = "") = 0;

    virtual void destroyContext(CurveManipulatorContext* context) = 0;

    /**
     * Enables curve editing on given prim paths.
     * Only CV on these prims can be selected and manipulated until curve editing mode exits.
     *
     * @param primPaths array of prim paths to enable curve editing mode. Each of them has to be a path to
     * UsdGeomBasisCurves prim.
     * @param count number of elements in the primPaths array.
     */
    virtual void enableCurveEditingMode(CurveManipulatorContext* context,
                                        const char** primPaths,
                                        size_t count,
                                        CurveEditingModeType mode) = 0;

    /**
     * Gets if curve editing mode is on.
     *
     * @return true if in curve editing mode, false otherwise.
     */
    virtual bool isInCurveEditingMode(const CurveManipulatorContext* context) const = 0;

    /**
     * Gets the number of curves being edited.
     *
     * @return the number of curves being edited.
     */
    virtual size_t getEditingCurvePathsCount(const CurveManipulatorContext* context) const = 0;

    /**
     * Fills an array of paths of curves being edited.
     *
     * @param primPaths array to be filled. It must be able to fit at least @ref getEditingCurvePathsCount entries.
     */
    virtual void getEditingCurvePaths(const CurveManipulatorContext* context, const char** primPaths) const = 0;

    /**
     * Exits curve editing mode. All proxy CV prims will be removed and restore normal selection mode.
     */
    virtual void disableCurveEditingMode(CurveManipulatorContext* context) = 0;

    /**
     * Gets the event stream for curve manipulator.
     *
     * @return IEventStream for curve manipulator.
     */
    virtual carb::events::IEventStream* getCurvesEventStream(CurveManipulatorContext* context) = 0;

    /**
     * Gets current curve editing mode.
     *
     * @return current curve editing mode.
     */
    virtual CurveEditingModeType getCurveEditingMode(const CurveManipulatorContext* context) const = 0;

    /**
     * Sets current curve editing mode.
     *
     * @param mode The new mode that the tool should be in.
     */
    virtual void setCurveEditingMode(CurveManipulatorContext* context, CurveEditingModeType mode) = 0;

    /**
     * Sets whether or not a new child curve is being added to the currently-edited basis curves.
     *
     * @param value True if a new child curve is being added to the currently-edited basis curves.
     */
    virtual void setAddingCurveToBasisCurves(CurveManipulatorContext* context, bool value) = 0;

    /**
     * Casts a ray to create or edit curve.
     * This is only needed by Viewport 2.0. Raycast is handled implicitly with Viewport 1.0.
     *
     * @param origin the origin of the ray in world space.
     * @param dir the direction of the ray in world space.
     * @param input if the left mouse button is down or not (drag vs hover).
     * @param end if this is the last ray cast event before mouse is released.
     * @param cameraPath path of the camera where the ray is casting from. This is used to determine plane to create
     * curve on.
     * @param rect viewport rect.
     * @param viewProjMatrix view-projection matrix of the camera.
     * @param snapWorldPos[optional] The candidate position for the curve tool to snap to. If nullptr, the desired plane
     * determined by camera will be used.
     */
    virtual void onRaycast(CurveManipulatorContext* context,
                           const carb::Float3& origin,
                           const carb::Float3& dir,
                           bool input,
                           bool end,
                           const char* cameraPath,
                           const carb::Float4& rect,
                           const double* viewProjMatrix,
                           const carb::Double3* snapWorldPos = nullptr) = 0;
};
}
}

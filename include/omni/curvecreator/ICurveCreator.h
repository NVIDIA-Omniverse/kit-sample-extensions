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

#include "CurveCreatorTypes.h"

#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>

namespace omni
{
namespace curvecreator
{

class CurveCreatorContext;

class ICurveCreator
{
public:
    CARB_PLUGIN_INTERFACE("omni::curvecreator::ICurveCreator", 1, 1);

    /**
     * Creates a CurveCreatorContext. Each tool that uses curve creator needs to create their own context to work on.
     *
     * @param plane the default plane to create the curve on if snap to face is not enabled. The first 3 elements is the
     * normal and the 4th is the distance along normal from origin.
     * @param spacing the distance between resampled curve CV. The larger the value the denser and more accurate the
     * curve is to drawn stroke.
     * @param type the interpolate type of the curve to be created. It can be either Linear or Cubic Bezier curve.
     * @param onCreatedFn callback function when a curve is created (mouse released).
     * @param userData user data to be passed back into onCreatedFn.
     * @return pointer to the created CurveCreatorContext.
     */
    virtual CurveCreatorContext* createContext(const carb::Float4& plane = { 0, 1, 0, 0 },
                                               float spacing = 50,
                                               CurveInterpolateTypes type = CurveInterpolateTypes::eLinear,
                                               OnCreatedFn onCreatedFn = nullptr,
                                               void* userData = nullptr) = 0;

    /**
     * Destroys a CurveCreatorContext.
     *
     * @param context CurveCreatorContext object to be destroyed.
     */
    virtual void destroyContext(CurveCreatorContext* context) = 0;

    /**
     * Enables curve creation mode.
     *
     * @param context CurveCreatorContext object this function to be set to.
     */
    virtual void startCurveCreation(CurveCreatorContext* context) = 0;

    /**
     * Disables curve creation mode.
     *
     * @param context CurveCreatorContext object this function to be set to.
     */
    virtual void stopCurveCreation(CurveCreatorContext* context) = 0;

    /**
     * Enables curve creation mode.
     *
     * @param context CurveCreatorContext object this function to be set to.
     */
    virtual void setOnCreatedFn(CurveCreatorContext* context, OnCreatedFn onCreatedFn, void* userData) = 0;

    /**
     * Sets desired plane.
     *
     * @param context CurveCreatorContext object this function to be set to.
     * @param plane the default plane to create the curve on if snap to face is not enabled. The first 3 elements is the
     * normal and the 4th is the distance along normal from origin.
     */
    virtual void setDesiredPlane(CurveCreatorContext* context, const carb::Float4& plane) = 0;

    /**
     * Sets CV spacing.
     *
     * @param context CurveCreatorContext object this function to be set to.
     * @param spacing the distance between resampled curve CV. The larger the value the denser and more accurate the
     * curve is to drawn stroke.
     */
    virtual void setCvSpacing(CurveCreatorContext* context, float spacing) = 0;

    /**
     * Sets interpolate type.
     *
     * @param context CurveCreatorContext object this function to be set to.
     * @param type the interpolate type of the curve to be created. It can be either Linear or Cubic Bezier curve.
     * curve is to drawn stroke.
     */
    virtual void setCurveInterpolateType(CurveCreatorContext* context, CurveInterpolateTypes type) = 0;

    /**
     * Casts a ray to create or edit curve.
     * This is only needed by Viewport 2.0. Raycast is handled implicitly with Viewport 1.0.
     *
     * @param origin the origin of the ray in world space.
     * @param dir the direction of the ray in world space.
     * @param input if the left mouse button is down or not (drag vs hover).
     * @param snapWorldPos[optional] The candidate position for the curve tool to snap to. If nullptr, the desired plane
     * determined by camera will be used.
     */
    virtual void onRaycast(CurveCreatorContext* context,
                           const carb::Float3& orig,
                           const carb::Float3& dir,
                           bool input,
                           const carb::Double3* snapWorldPos) = 0;
};
}
}

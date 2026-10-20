// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
#include <carb/events/IEvents.h>

// clang-format off
#include "animationSchema/animationCurveTypes.h"
#include "animx.h"
// clang-format on

#include <map>
#include <vector>

namespace omni
{
namespace anim
{
struct IAnimCurve
{
    CARB_PLUGIN_INTERFACE("omni::anim::IAnimCurve", 1, 1);

    struct Curve
    {
        std::vector<pxr::AnimationSchemaAnimationCurve::Key> keys;
        std::vector<pxr::AnimationSchemaAnimationCurve::Key> overridenKeys;
        pxr::TfToken preInfinityType;
        pxr::TfToken postInfinityType;
        pxr::UsdPrim animData;
    };

    enum CurveEventType
    {
        Nop = -1,
        Added = 0,
        Removed,
        Updated,
        KeySelectionChanged,
        KeysOverriden
    };

    bool(CARB_ABI* isUpdatingUsd)();
    carb::events::IEventStream*(CARB_ABI* getEventStream)();
    // Get curve prims from a prim. The input prim path can be target prim, curve node prim, animation data prim.
    std::vector<pxr::SdfPath>(CARB_ABI* getCurvePrims)(const pxr::SdfPath& prim);
    std::map<pxr::TfToken, const Curve*>(CARB_ABI* getCurves)(const pxr::SdfPath& prim);
    void(CARB_ABI* pumpKeysOverridenEvent)(const std::vector<pxr::SdfPath>& curvePaths);
    bool(CARB_ABI* isAttrSupported)(const pxr::SdfPath& attr);
    bool(CARB_ABI* evaluate)(const pxr::SdfPath& curvePath, double time, double& value);
    int(CARB_ABI* getTicksPerSecond)();
    std::vector<pxr::SdfPath>(CARB_ABI* getCurveNodes)(const pxr::SdfPath& prim /*, const pxr::SdfPath& animData*/);
    void(CARB_ABI* _removedApi)();
    bool(CARB_ABI* setOverridenKeys)(const pxr::SdfPath& curvePath,
                                     const std::vector<pxr::AnimationSchemaAnimationCurve::Key>& keys);
    bool(CARB_ABI* convertToAttrPrecision)(const pxr::SdfPath& attrPath, double& value);
    std::vector<std::pair<float, float>>(CARB_ABI* simplifyCatmull)(const std::vector<float>& keys,
                                                                    const std::vector<float>& values,
                                                                    float valueRangeEps,
                                                                    float maxErrorRatio);
};
}
}

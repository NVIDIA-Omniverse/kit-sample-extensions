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

#include "animationSchema/tokens.h"
#include "animx.h"

struct TransformData
{
    bool scale = false, rotate = false, translate = false;
    double scaleX, scaleY, scaleZ;
    double rotateX, rotateY, rotateZ;
    double translateX, translateY, translateZ;
};

struct AttributeToken
{
    pxr::TfToken valueToken;
    pxr::TfToken tangentTimeToken;
    pxr::TfToken tangentValueToken;
    pxr::TfToken interpolationTypeToken;
    pxr::TfToken remappingTypeToken;

    explicit AttributeToken(const pxr::TfToken& inputToken)
    {
        valueToken = inputToken;
        tangentTimeToken = pxr::TfToken(valueToken.GetString() + std::string(":tangentTime"));
        tangentValueToken = pxr::TfToken(valueToken.GetString() + std::string(":tangentValue"));
        interpolationTypeToken = pxr::TfToken(valueToken.GetString() + std::string(":interpolationType"));
        remappingTypeToken = pxr::TfToken(valueToken.GetString() + std::string(":remappingType"));
    }
};

extern int ticksPerSec; // Tcks per second

const std::map<pxr::TfToken, adsk::InfinityType> infinityTypeMap{
    { pxr::AnimationSchemaTokens->constant, adsk::InfinityType::Constant },
    { pxr::AnimationSchemaTokens->cycle, adsk::InfinityType::Cycle },
    { pxr::AnimationSchemaTokens->cycleRelative, adsk::InfinityType::CycleRelative },
    { pxr::AnimationSchemaTokens->linear, adsk::InfinityType::Linear },
    { pxr::AnimationSchemaTokens->oscillate, adsk::InfinityType::Oscillate },
};

typedef std::vector<AttributeToken> AttributeTokens;

TransformData getInterpolatedTransformData(const pxr::UsdPrim& curvePrim, const pxr::UsdPrim& targetPrim, double timeCode);
bool hasTransformTimeSamples(const pxr::UsdPrim& prim, bool includeScale = false);
void updateTransformAttributes(const pxr::UsdPrim& targetPrim, const TransformData& data);
void updateGeneralAttribute(const pxr::UsdPrim& curvePrim,
                            const pxr::UsdPrim& targetPrim,
                            const AttributeTokens& tokens,
                            double timeCode);

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

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/graph/core/iComputeGraph.h>
#include <omni/math/linalg/quat.h>
#include <omni/math/linalg/vec.h>

namespace omni
{
namespace genproc
{

using omni::geometry::curves::eBasisCurveWrap;
using omni::geometry::curves::SplineCurve;

using omni::graph::core::GraphContextObj;
using omni::graph::core::NodeObj;

using omni::graph::core::ConstBundlePrims;

using omni::math::linalg::matrix4d;
using omni::math::linalg::quatd;
using omni::math::linalg::vec2f;
using omni::math::linalg::vec3f;

pxr::UsdPrim getUsdPrimFromNode(const GraphContextObj& context, const NodeObj& nodeObj);

bool primInBundleToTriangles(ConstBundlePrims& prims,
                             const size_t primIndex,
                             std::vector<vec3f>& outputPoints,
                             std::vector<int>& outputIndices,
                             std::vector<vec3f>* outputNormals = nullptr,
                             std::vector<int>* outputIndicesMapping = nullptr,
                             std::vector<size_t>* outputFaceToPrim = nullptr,
                             std::vector<vec2f>* outputTexCoords = nullptr);

void primsInBundleToTriangles(ConstBundlePrims& prims,
                              std::vector<vec3f>& outputPoints,
                              std::vector<int>& outputIndices,
                              std::vector<vec3f>* outputNormals = nullptr,
                              std::vector<int>* outputIndicesMapping = nullptr,
                              std::vector<size_t>* outputFaceToPrim = nullptr,
                              std::vector<vec2f>* outputTexCoords = nullptr,
                              std::vector<size_t>* outputMeshIndices = nullptr);

void getPrimBoundingSpheres(ConstBundlePrims& prims, std::vector<vec3f>& centers, std::vector<float>& radiiSquared);

void getPrimBoundingBoxes(ConstBundlePrims& prims, std::vector<std::pair<vec3f, vec3f>>& extents);

void getPrimTransforms(ConstBundlePrims& prims, std::vector<matrix4d>& transforms);


static const Type s_DoubleType(BaseDataType::eDouble);
static const Type s_FloatType(BaseDataType::eFloat);
static const Type s_BoolType(BaseDataType::eBool);
static const Type s_IntType(BaseDataType::eInt);
enum class TimeAttrIndex
{
    TIME = 0,
    ELAPSED_TIME,
    USD_TIMECODE,
    PREV_USD_TIMECODE,
    PLAYBACK_EVALUATION,
    PLAYBACK_START_FRAME,
    PLAYBACK_END_FRAME
};
constexpr static size_t s_timeAttrCount = 7;
static inline const NameToken* getTimeAttrNames()
{
    static NameToken s_timeAttrNames[s_timeAttrCount]{ NameToken("time"),
                                                       NameToken("elapsedTime"),
                                                       NameToken("usdTimecode"),
                                                       NameToken("prevUsdTimecode"),
                                                       NameToken("playbackEvaluation"),
                                                       NameToken("playbackStartFrame"),
                                                       NameToken("playbackEndFrame") };
    return s_timeAttrNames;
}

struct TimeInfo
{
    double time;
    double elapsedTime;
    double usdTimecode;
    double playbackStartFrame;
    double playbackEndFrame;
    bool playbackEvaluation;
    bool hasTime;
    bool hasElapsedTime;
    bool hasUsdTimecode;
    bool hasPlaybackStartFrame;
    bool hasPlaybackEndFrame;
    bool hasPlaybackEvaluation;
    bool skipEvaluationStep;
    double framesPerSecond;
};

TimeInfo getTimeInfo(const GraphContextObj& context, ConstBundleHandle inputPrim);
TimeInfo getOrAddTimeInfo(const GraphContextObj& context,
                          BundleHandle outputPrim,
                          bool storeCurrUsdTimeCode = false,
                          bool storeElapsedTime = true);


}
}

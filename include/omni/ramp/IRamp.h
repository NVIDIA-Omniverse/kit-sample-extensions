// SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

namespace omni
{
namespace ramp
{

class IRamp
{
public:
    CARB_PLUGIN_INTERFACE("omni::ramp::IRamp", 1, 0);

    virtual void onStartup(const char* extId) = 0;

    virtual void onShutdown() = 0;

    virtual float getFloatAtPosition(const float position,
                                     const char* rampPositionsAttrPath,
                                     const char* rampValuesAttrPath,
                                     const char* rampInterpsAttrPath) = 0;

    virtual float getFloatAtPositionFromData(const float position,
                                             const size_t numRampKeys,
                                             const float* positions,
                                             const float* values,
                                             const int* interps) = 0;

    virtual void sampleFloatArray(const size_t numElements,
                                  float* out,
                                  const float* positions,
                                  const int rampMode,
                                  const size_t numRampKeys,
                                  const float* rampPositions,
                                  const float* rampValues,
                                  const int* rampInterps) = 0;

    virtual void getFloatArray(const size_t numElements,
                               float* out,
                               const float* positions,
                               const char* rampPositionsAttrPath,
                               const char* rampValuesAttrPath,
                               const char* rampInterpsAttrPath) = 0;

    virtual void addFloatKey(const float position,
                             const float value,
                             const int interpolation,
                             const char* rampPositionsAttrPath,
                             const char* rampValuesAttrPath,
                             const char* rampInterpsAttrPath) = 0;

    virtual void editFloatKey(const size_t index,
                              const float position,
                              const float value,
                              const int interpolation,
                              const char* rampPositionsAttrPath,
                              const char* rampValuesAttrPath,
                              const char* rampInterpsAttrPath) = 0;

    virtual void removeFloatKey(const size_t index,
                                const char* rampPositionsAttr,
                                const char* rampValuesAttr,
                                const char* rampInterpsAttr) = 0;

    virtual carb::Float3 getFloat3AtPosition(const float position,
                                             const char* rampPositionsAttrPath,
                                             const char* rampValuesAttrPath,
                                             const char* rampInterpsAttrPath) = 0;

    virtual carb::Float3 getFloat3AtPositionFromData(const float position,
                                                     const size_t numRampKeys,
                                                     const float* positions,
                                                     const carb::Float3* values,
                                                     const int* interps) = 0;

    virtual void getFloat3Array(const size_t numElements,
                                carb::Float3* out,
                                const float* positions,
                                const char* rampPositionsAttrPath,
                                const char* rampValuesAttrPath,
                                const char* rampInterpsAttrPath) = 0;

    virtual void sampleFloat3Array(const size_t numElements,
                                   carb::Float3* out,
                                   const float* positions,
                                   const int rampMode,
                                   const size_t numRampKeys,
                                   const float* rampPositions,
                                   const carb::Float3* rampValues,
                                   const int* rampInterps) = 0;

    virtual void addFloat3Key(const float position,
                              const carb::Float3 value,
                              const int interpolation,
                              const char* rampPositionsAttr,
                              const char* rampValuesAttr,
                              const char* rampInterpsAttr) = 0;

    virtual void editFloat3Key(const size_t index,
                               const float position,
                               const carb::Float3 value,
                               const int interpolation,
                               const char* rampPositionsAttr,
                               const char* rampValuesAttr,
                               const char* rampInterpsAttr) = 0;

    virtual void removeFloat3Key(const size_t index,
                                 const char* rampPositionsAttr,
                                 const char* rampValuesAttr,
                                 const char* rampInterpsAttr) = 0;
    // same as getFloatArray but without USD - based on array of ramp data
    virtual void getFloatArray2(const size_t numElements,
                                float* out,
                                const float* positions,
                                const size_t numRampKeys,
                                const float* rampPositions,
                                const float* rampValues,
                                const int* rampInterps) = 0;
};
}
}

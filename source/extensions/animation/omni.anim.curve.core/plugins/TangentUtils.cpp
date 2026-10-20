// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

#include "TangentUtils.h"

#include "CurveInterpolation.h"


// conver interpolationmethod string to animX curve interpolation method enum
enum adsk::CurveInterpolatorMethod getCurveInterpolationMethod(const char* interpolationMethod)
{
    if (interpolationMethod)
    {
        // still add bezier as the first option as it is expected
        // to be most common
        if (strcmp(interpolationMethod, "bezier") == 0)
        {
            return adsk::CurveInterpolatorMethod::Bezier;
        }
        if (strcmp(interpolationMethod, "hermite") == 0)
        {
            return adsk::CurveInterpolatorMethod::Hermite;
        }

        if (strcmp(interpolationMethod, "sine") == 0)
        {
            return adsk::CurveInterpolatorMethod::Sine;
        }

        if (strcmp(interpolationMethod, "parabolic") == 0)
        {
            return adsk::CurveInterpolatorMethod::Parabolic;
        }

        if (strcmp(interpolationMethod, "tangentlog") == 0)
        {
            return adsk::CurveInterpolatorMethod::TangentLog;
        }
    }

    // default to bezier
    return adsk::CurveInterpolatorMethod::Bezier;
}

void computeTangent(pxr::GfVec2d value,
                    bool hasPrevValue,
                    const pxr::GfVec2d& prevValue, // how do we send null
                    bool hasNextValue,
                    const pxr::GfVec2d& nextValue,
                    const char* interpolationMethod,
                    pxr::GfVec4d* tangent)
{
    using namespace adsk;

    KeyTimeValue curKeyVal, prevKeyVal, nextKeyVal;
    KeyTimeValue *prev = nullptr, *next = nullptr;
    seconds tanX, tanY;

    auto convertToKeyTimeVal = [&](const pxr::GfVec2d& inVal, KeyTimeValue& outVal)
    {
        outVal.time = inVal[0];
        outVal.value = inVal[1];
    };

    convertToKeyTimeVal(value, curKeyVal);
    if (hasPrevValue)
    {
        convertToKeyTimeVal(prevValue, prevKeyVal);
        prev = &prevKeyVal;
    }

    if (hasNextValue)
    {
        convertToKeyTimeVal(nextValue, nextKeyVal);
        next = &nextKeyVal;
    }

    const double OneThird = 1.0 / 3.0;
    CurveInterpolatorMethod interp = getCurveInterpolationMethod(interpolationMethod);
    autoTangent(true, curKeyVal, prev, next, interp, tanX, tanY);
    (*tangent)[0] = curKeyVal.time - tanX * OneThird;
    (*tangent)[1] = curKeyVal.value - tanY * OneThird;

    autoTangent(false, curKeyVal, prev, next, interp, tanX, tanY);
    (*tangent)[2] = curKeyVal.time + tanX * OneThird;
    (*tangent)[3] = curKeyVal.value + tanY * OneThird;
}


std::vector<float> computeTangent(float valueX,
                                  float valueY,
                                  bool hasPrevValue,
                                  float prevValueX,
                                  float prevValueY,
                                  bool hasNextValue,
                                  float nextValueX,
                                  float nextValueY,
                                  const char* interpolationMethod)
{
    pxr::GfVec4d outTangent;

    enum class LocalTangentType
    {
        Flat,
        Linear,
        Bezier,
    };

    auto calculateDiff = [&](float target_val_x, float target_val_y, float val_x, float val_y, double& out_delta_val_x,
                             double& out_delta_val_y, LocalTangentType tangent_type)
    {
        float diff_x = target_val_x - val_x;
        float diff_y = target_val_y - val_y;

        const double OneThird = 1.0 / 3.0;
        if (tangent_type == LocalTangentType::Flat)
        {
            out_delta_val_x = diff_x;
            out_delta_val_y = 0;
        }
        else if (tangent_type == LocalTangentType::Linear)
        {
            out_delta_val_x = diff_x;
            out_delta_val_y = diff_y;
        }
        else
        {
            // in the case of bezier or others - we just create 1/3 of point to target.
            // this will give similar to cubic curve without extra param
            out_delta_val_x = diff_x;
            out_delta_val_y = diff_y * 1.0 / 3.0f;
        }

        out_delta_val_x *= OneThird;
        out_delta_val_y *= OneThird;
    };

    if (hasPrevValue && hasNextValue)
    {

        computeTangent(pxr::GfVec2d(valueX, valueY), hasPrevValue, pxr::GfVec2d(prevValueX, prevValueY), hasNextValue,
                       pxr::GfVec2d(nextValueX, nextValueY), interpolationMethod, &outTangent);
    }
    // if either side of key exist, we generate our tangent
    else
    {
        LocalTangentType tangentType = LocalTangentType::Bezier;
        if (interpolationMethod)
        {
            if (strcmp(interpolationMethod, "linear") == 0)
            {
                tangentType = LocalTangentType::Linear;
            }
            else if (strcmp(interpolationMethod, "stepNext") == 0)
            {
                tangentType = LocalTangentType::Flat;
            }
        }

        double out_delta_tangent_x = 0, out_delta_tangent_y = 0;
        if (hasPrevValue)
        {
            calculateDiff(prevValueX, prevValueY, valueX, valueY, out_delta_tangent_x, out_delta_tangent_y, tangentType);
            outTangent = pxr::GfVec4d(valueX + out_delta_tangent_x, valueY + out_delta_tangent_y, valueX + 10.0, valueY);
        }
        else if (hasNextValue)
        {
            calculateDiff(nextValueX, nextValueY, valueX, valueY, out_delta_tangent_x, out_delta_tangent_y, tangentType);
            outTangent = pxr::GfVec4d(valueX - 10.0, valueY, valueX + out_delta_tangent_x, valueY + out_delta_tangent_y);
        }
        else // none of them
        {
            // just create flat line
            outTangent = pxr::GfVec4d(valueX - 10.0, valueY, valueX + 10.0, valueY);
        }
    }

    std::vector<float> outValue;
    outValue.resize(4);
    outValue[0] = (float)outTangent[0];
    outValue[1] = (float)outTangent[1];
    outValue[2] = (float)outTangent[2];
    outValue[3] = (float)outTangent[3];
    return outValue;
}

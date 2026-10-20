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

#include "animx.h"

template <typename KeyValueType_>
void getAttributeValueWithPrecision(const pxr::UsdAttribute& attr,
                                    KeyValueType_& value,
                                    const pxr::UsdTimeCode timeCode = pxr::UsdTimeCode::Default())
{
    value = 0;
    attr.Get<KeyValueType_>(&value, timeCode);
}


template <typename ValueType_>
void setAttributeWithPrecision(const pxr::UsdAttribute& attr,
                               const ValueType_& val,
                               const pxr::UsdTimeCode timeCode = pxr::UsdTimeCode::Default())
{
    pxr::UsdGeomXformOp xformOp(attr);
    auto precision = xformOp.GetPrecision();

    switch (precision)
    {
    case pxr::UsdGeomXformOp::PrecisionDouble:
        attr.Set(pxr::GfVec3d(val), timeCode);
        break;

    case pxr::UsdGeomXformOp::PrecisionFloat:
        attr.Set(pxr::GfVec3f(val), timeCode);
        break;

    case pxr::UsdGeomXformOp::PrecisionHalf:
        attr.Set(pxr::GfVec3h(val), timeCode);
        break;
    }
}

template <typename T>
bool getExactSampleOrDefault(pxr::UsdAttribute& attr, double time, T* value)
{
    double lowerTime;
    double upperTime;
    bool hasSample;

    if (!attr.GetBracketingTimeSamples(time, &lowerTime, &upperTime, &hasSample))
    {
        return false;
    }

    if (!hasSample || (lowerTime == time && upperTime == time))
    {
        return attr.Get(value, time);
    }
    else
    {
        return false;
    }
}


inline double GetCurveSampleInT(const pxr::GfVec4d& sample)
{
    return sample[0];
}
inline double GetCurveSampleInV(const pxr::GfVec4d& sample)
{
    return sample[1];
}
inline double GetCurveSampleOutT(const pxr::GfVec4d& sample)
{
    return sample[2];
}
static double GetCurveSampleOutV(const pxr::GfVec4d& sample)
{
    return sample[3];
}
inline void SetCurveSampleInT(pxr::GfVec4d& sample, double inT)
{
    sample[0] = inT;
}
inline void SetCurveSampleInV(pxr::GfVec4d& sample, double inV)
{
    sample[1] = inV;
}
inline void SetCurveSampleOutT(pxr::GfVec4d& sample, double outT)
{
    sample[2] = outT;
}
inline void SetCurveSampleOutV(pxr::GfVec4d& sample, double outV)
{
    sample[3] = outV;
}

inline double lerp(double alpha, double v0, double v1)
{
    if (alpha == 0.0)
        return v0;

    return (1.0 - alpha) * v0 + alpha * v1;
}

inline double easeInEaseOut(double t)
{
    if (t < 0.5)
        t = 2 * t * t;
    else
    {
        double x = t - 0.5;
        t = 2 * x * (1 - x) + 0.5;
    }

    return t;
}

inline double easeIn(double t)
{
    if (t < 0.5)
        t = 2 * t * t;

    return t;
}

inline double easeOut(double t)
{
    if (t > 0.5)
    {
        double x = t - 0.5;
        t = 2 * x * (1 - x) + 0.5;
    }

    return t;
}

template <typename SourceValueType_>
double interpolateCurve(const pxr::UsdAttribute& usdAttribute,
                        const pxr::UsdAttribute& usdTangentAttribute,
                        const double time,
                        double defaultValue = 0.0)
{
    if (!usdAttribute)
    {
        return defaultValue;
    }

    // get 2 samples relevant to time.
    //
    double lowerTime;
    double upperTime;
    bool hasSample;
    if (!usdAttribute.GetBracketingTimeSamples(time, &lowerTime, &upperTime, &hasSample))
    {
        return defaultValue;
    }
    else if (!hasSample || !usdTangentAttribute)
    {
        // If usdAttribute has no timeSamples array or curve control is not available, fall back to general
        // usdAttribute.Get(v,time).
        SourceValueType_ v;
        getAttributeValueWithPrecision(usdAttribute, v, time);
        return v;
    }

    // get lower and upper
    SourceValueType_ lowerValue;
    SourceValueType_ upperValue;
    getAttributeValueWithPrecision(usdAttribute, lowerValue, lowerTime);
    getAttributeValueWithPrecision(usdAttribute, upperValue, upperTime);

    // get lower and upper tangent
    pxr::GfVec4d lowerTangent;
    usdTangentAttribute.Get<pxr::GfVec4d>(&lowerTangent, lowerTime);
    pxr::GfVec4d upperTangent;
    usdTangentAttribute.Get<pxr::GfVec4d>(&lowerTangent, upperTime);

    // get lower curve sample.
    double lowerControlTime = GetCurveSampleOutT(lowerTangent);
    double lowerControlValue = GetCurveSampleOutV(lowerTangent);

    // get upper curve sample
    double upperControlTime = GetCurveSampleInT(upperTangent);
    double upperControlValue = GetCurveSampleInV(upperTangent);

    // interpolate with animX and store the real result.
    //


    double interpolatedValue = adsk::evaluateCurveSegment(
        adsk::SpanInterpolationMethod::Bezier, adsk::CurveInterpolatorMethod::Bezier, time, lowerTime, lowerValue,
        lowerControlTime, lowerControlValue, upperControlTime, upperControlValue, upperTime, upperValue);

    if (lowerTime == upperTime)
    {
        // adsk::evaluateCurveSegment seems to be buggy and return 0 when lowerTime == upperTime == t
        // though the code api description says lowerTime <= t <= upperTime is allowed.
        // So workaround the bug here.
        interpolatedValue = lowerValue;
    }

    return interpolatedValue;
}

inline double interpolateBezierCurve(double time,
                                     double lowerTime,
                                     double lowerValue,
                                     const pxr::GfVec4d& lowerTangent,
                                     double upperTime,
                                     double upperValue,
                                     const pxr::GfVec4d& upperTangent)
{
    // get lower curve sample.
    double lowerControlTime = GetCurveSampleOutT(lowerTangent);
    double lowerControlValue = GetCurveSampleOutV(lowerTangent);

    // get upper curve sample
    double upperControlTime = GetCurveSampleInT(upperTangent);
    double upperControlValue = GetCurveSampleInV(upperTangent);

    // interpolate with animX and store the real result.


    double interpolatedValue = adsk::evaluateCurveSegment(
        adsk::SpanInterpolationMethod::Bezier, adsk::CurveInterpolatorMethod::Bezier, time, lowerTime, lowerValue,
        lowerControlTime, lowerControlValue, upperControlTime, upperControlValue, upperTime, upperValue);

    if (lowerTime == upperTime)
    {
        // adsk::evaluateCurveSegment seems to be buggy and return 0 when lowerTime == upperTime == t
        // though the code api description says lowerTime <= t <= upperTime is allowed.
        // So workaround the bug here.
        interpolatedValue = lowerValue;
    }


    return interpolatedValue;
}

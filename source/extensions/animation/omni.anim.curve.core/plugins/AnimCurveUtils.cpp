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
#include <animationSchema/animationCurveTypes.h>
// clang-format on

#include "AnimCurveUtils.h"

#include "CurveInterpolation.h"
#include "QuaternionUtils.h"

#include <carb/Framework.h>

using namespace adsk;
using namespace pxr;

// predefined tokens
namespace
{
pxr::TfToken s_tokenInterpolationType("interpolationType");
pxr::TfToken s_tokenRemappingType("remappingType");

pxr::TfToken s_tokenScaleX("scaleX");
pxr::TfToken s_tokenScaleXTangentTime("scaleX:tangentTime");
pxr::TfToken s_tokenScaleXTangentValue("scaleX:tangentValue");
pxr::TfToken s_tokenScaleXInterpolation("scaleX:interpolationType");
pxr::TfToken s_tokenScaleXRemapping("scaleX:remappingType");

pxr::TfToken s_tokenScaleY("scaleY");
pxr::TfToken s_tokenScaleYTangentTime("scaleY:tangentTime");
pxr::TfToken s_tokenScaleYTangentValue("scaleY:tangentValue");
pxr::TfToken s_tokenScaleYInterpolation("scaleY:interpolationType");
pxr::TfToken s_tokenScaleYRemapping("scaleY:remappingType");

pxr::TfToken s_tokenScaleZ("scaleZ");
pxr::TfToken s_tokenScaleZTangentTime("scaleZ:tangentTime");
pxr::TfToken s_tokenScaleZTangentValue("scaleZ:tangentValue");
pxr::TfToken s_tokenScaleZInterpolation("scaleZ:interpolationType");
pxr::TfToken s_tokenScaleZRemapping("scaleZ:remappingType");

pxr::TfToken s_tokenRotateX("rotateX");
pxr::TfToken s_tokenRotateXTangentTime("rotateX:tangentTime");
pxr::TfToken s_tokenRotateXTangentValue("rotateX:tangentValue");
pxr::TfToken s_tokenRotateXInterpolation("rotateX:interpolationType");
pxr::TfToken s_tokenRotateXRemapping("rotateX:remappingType");

pxr::TfToken s_tokenRotateY("rotateY");
pxr::TfToken s_tokenRotateYTangentTime("rotateY:tangentTime");
pxr::TfToken s_tokenRotateYTangentValue("rotateY:tangentValue");
pxr::TfToken s_tokenRotateYInterpolation("rotateY:interpolationType");
pxr::TfToken s_tokenRotateYRemapping("rotateY:remappingType");

pxr::TfToken s_tokenRotateZ("rotateZ");
pxr::TfToken s_tokenRotateZTangentTime("rotateZ:tangentTime");
pxr::TfToken s_tokenRotateZTangentValue("rotateZ:tangentValue");
pxr::TfToken s_tokenRotateZInterpolation("rotateZ:interpolationType");
pxr::TfToken s_tokenRotateZRemapping("rotateZ:remappingType");

pxr::TfToken s_tokenTranslateX("translateX");
pxr::TfToken s_tokenTranslateXTangentTime("translateX:tangentTime");
pxr::TfToken s_tokenTranslateXTangentValue("translateX:tangentValue");
pxr::TfToken s_tokenTranslateXInterpolation("translateX:interpolationType");
pxr::TfToken s_tokenTranslateXRemapping("translateX:remappingType");

pxr::TfToken s_tokenTranslateY("translateY");
pxr::TfToken s_tokenTranslateYTangentTime("translateY:tangentTime");
pxr::TfToken s_tokenTranslateYTangentValue("translateY:tangentValue");
pxr::TfToken s_tokenTranslateYInterpolation("translateY:interpolationType");
pxr::TfToken s_tokenTranslateYRemapping("translateY:remappingType");

pxr::TfToken s_tokenTranslateZ("translateZ");
pxr::TfToken s_tokenTranslateZTangentTime("translateZ:tangentTime");
pxr::TfToken s_tokenTranslateZTangentValue("translateZ:tangentValue");
pxr::TfToken s_tokenTranslateZInterpolation("translateZ:interpolationType");
pxr::TfToken s_tokenTranslateZRemapping("translateZ:remappingType");

pxr::TfToken s_tokenXformOpScale("xformOp:scale");
pxr::TfToken s_tokenXformOpRotateXYZ("xformOp:rotateXYZ");
pxr::TfToken s_tokenXformOpRotateXZY("xformOp:rotateXZY");
pxr::TfToken s_tokenXformOpRotateYXZ("xformOp:rotateYXZ");
pxr::TfToken s_tokenXformOpRotateYZX("xformOp:rotateYZX");
pxr::TfToken s_tokenXformOpRotateZXY("xformOp:rotateZXY");
pxr::TfToken s_tokenXformOpRotateZYX("xformOp:rotateZYX");
pxr::TfToken s_tokenXformOpTranslate("xformOp:translate");
pxr::TfToken s_tokenXformOpTransform("xformOp:transform");

pxr::TfToken s_interpolationTypeLinearToken("linear");
pxr::TfToken s_interpolationTypeLinearSlerpToken("linearSlerp");
pxr::TfToken s_interpolationTypeBezierToken("bezier");
pxr::TfToken s_interpolationTypeBezierSlerpToken("bezierSlerp");
pxr::TfToken s_interpolationTypeStep("step");
pxr::TfToken s_interpolationTypeStepNext("stepNext");

pxr::TfToken s_remappingTypeLinearToken("linear");
pxr::TfToken s_remappingTypeEaseInToken("easeIn");
pxr::TfToken s_remappingTypeEaseOutToken("easeOut");
pxr::TfToken s_remappingTypeEaseInEaseOutToken("easeInEaseOut");
}

using namespace AnimationSchemaAnimationCurve;

template <typename T>
void setAttributeValue(pxr::UsdAttribute& attr, const T& value)
{
    if (attr.GetTypeName() == pxr::SdfValueTypeNames->Double)
        attr.Set((double)value);
    else if (attr.GetTypeName() == pxr::SdfValueTypeNames->Float)
        attr.Set((float)value);
}

pxr::GfVec4d getSampleTangent(pxr::UsdAttribute& tangentTimeAttribute,
                              pxr::UsdAttribute& tangentValueAttribute,
                              double time,
                              double value)
{
    pxr::GfVec4d result;

    pxr::VtArray<pxr::SdfTimeCode> tangentTime;
    pxr::VtDoubleArray tangentValue;
    // The code path is expected to have sample at time, but I do not check it here, perhaps because potential double
    // precision issue with USD timeCode<=>time conversion. So the fact is even sample at time is missing, the
    // interpolated value is use. But it is not intentional.
    bool timeGot = tangentTimeAttribute.Get(&tangentTime, time) && tangentTime.size() == 2;
    bool valueGot = tangentValueAttribute.Get(&tangentValue, time) && tangentValue.size() == 2;
    if (timeGot && valueGot)
    {
        result = pxr::GfVec4d(tangentTime[0].GetValue(), tangentValue[0], tangentTime[1].GetValue(), tangentValue[1]);
    }
    else
    {
        result = pxr::GfVec4d(time, value, time, value);
    }
    return result;
}

// check any rotate attribute
pxr::UsdAttribute getRotateAttribute(const pxr::UsdPrim& prim)
{
    pxr::UsdAttribute rotateAttr;

    if (rotateAttr = prim.GetAttribute(s_tokenXformOpRotateXYZ))
        return rotateAttr;

    if (rotateAttr = prim.GetAttribute(s_tokenXformOpRotateXZY))
        return rotateAttr;

    if (rotateAttr = prim.GetAttribute(s_tokenXformOpRotateYXZ))
        return rotateAttr;

    if (rotateAttr = prim.GetAttribute(s_tokenXformOpRotateYZX))
        return rotateAttr;

    if (rotateAttr = prim.GetAttribute(s_tokenXformOpRotateZXY))
        return rotateAttr;

    if (rotateAttr = prim.GetAttribute(s_tokenXformOpRotateXYZ))
        return rotateAttr;

    return rotateAttr;
}

// does this animation data prim have time samples for all transform related channels?
bool hasTransformTimeSamples(const pxr::UsdPrim& prim, bool includeScale)
{
    auto transX = prim.GetAttribute(s_tokenTranslateX);
    auto transY = prim.GetAttribute(s_tokenTranslateY);
    auto transZ = prim.GetAttribute(s_tokenTranslateZ);
    auto rotateX = prim.GetAttribute(s_tokenRotateX);
    auto rotateY = prim.GetAttribute(s_tokenRotateY);
    auto rotateZ = prim.GetAttribute(s_tokenRotateZ);

    bool hasTrans = transX && transX.GetNumTimeSamples() > 0 && transY && transY.GetNumTimeSamples() > 0 && transZ &&
                    transZ.GetNumTimeSamples() > 0;

    bool hasRot = rotateX && rotateX.GetNumTimeSamples() > 0 && rotateY && rotateY.GetNumTimeSamples() > 0 && rotateZ &&
                  rotateZ.GetNumTimeSamples() > 0;

    if (!includeScale)
        return hasTrans && hasRot;

    auto scaleX = prim.GetAttribute(s_tokenScaleX);
    auto scaleY = prim.GetAttribute(s_tokenScaleY);
    auto scaleZ = prim.GetAttribute(s_tokenScaleZ);

    bool hasScale = scaleX && scaleX.GetNumTimeSamples() > 0 && scaleY && scaleY.GetNumTimeSamples() > 0 && scaleZ &&
                    scaleZ.GetNumTimeSamples() > 0;

    return hasTrans && hasRot && hasScale;
}

void updateTransformAttributes(const pxr::UsdPrim& targetPrim, const TransformData& data)
{
    pxr::UsdAttribute translateAttr = targetPrim.GetAttribute(s_tokenXformOpTranslate);
    if (translateAttr && data.translate)
    {
        pxr::GfVec3d translate(data.translateX, data.translateY, data.translateZ);
        setAttributeWithPrecision(translateAttr, translate);
    }

    pxr::UsdAttribute rotateAttr = getRotateAttribute(targetPrim);
    if (rotateAttr && data.rotate)
    {
        pxr::GfVec3d rotate(data.rotateX, data.rotateY, data.rotateZ);
        setAttributeWithPrecision(rotateAttr, rotate);
    }

    pxr::UsdAttribute scaleAttr = targetPrim.GetAttribute(s_tokenXformOpScale);
    if (scaleAttr && data.scale)
    {
        pxr::GfVec3d scale(data.scaleX, data.scaleY, data.scaleZ);
        setAttributeWithPrecision(scaleAttr, scale);
    }

    pxr::UsdAttribute transformAttr = targetPrim.GetAttribute(s_tokenXformOpTransform);
    if (transformAttr)
    {
        pxr::GfMatrix4d transform;
        transformAttr.Get(&transform);

        if (data.translate)
            transform.SetTranslateOnly(pxr::GfVec3d(data.translateX, data.translateY, data.translateZ));

        if (data.rotate)
        {
            pxr::GfMatrix3d xRot(pxr::GfRotation(pxr::GfVec3f::XAxis(), data.rotateX));
            pxr::GfMatrix3d yRot(pxr::GfRotation(pxr::GfVec3f::YAxis(), data.rotateY));
            pxr::GfMatrix3d zRot(pxr::GfRotation(pxr::GfVec3f::ZAxis(), data.rotateZ));

            pxr::GfMatrix3d rotMat = xRot * yRot * zRot;
            transform.SetRotateOnly(rotMat);
        }

        transformAttr.Set(transform);
    }
}

// find global remapping type at current time.  If remapping type is not defined, return default type (linear)
inline pxr::TfToken getGlobalRemappingToken(const pxr::UsdPrim& curvePrim, double timeCode)
{
    pxr::TfToken defaultRemappingToken = s_remappingTypeLinearToken;

    auto globalRemappingAttribute = curvePrim.GetAttribute(s_tokenRemappingType);
    if (!globalRemappingAttribute)
        return defaultRemappingToken;

    pxr::TfToken authoredRemappingToken;
    if (globalRemappingAttribute.Get(&authoredRemappingToken, timeCode))
        return authoredRemappingToken;

    return defaultRemappingToken;
}

// returns remapped time where t is normalized between 0 (lower bound) and 1 (upper bound)
inline double getRemappedTime(double t, const pxr::TfToken& selectedRemappingToken)
{
    if (selectedRemappingToken == s_remappingTypeEaseInToken)
    {
        t = easeIn(t);
    }
    else if (selectedRemappingToken == s_remappingTypeEaseOutToken)
    {
        t = easeOut(t);
    }
    else if (selectedRemappingToken == s_remappingTypeEaseInEaseOutToken)
        t = easeInEaseOut(t);
    else if (selectedRemappingToken == s_remappingTypeLinearToken)
        t = t; // linear type doesn't need any remapping

    return t;
}

pxr::GfQuaternion getInterpolatedQuaternion(const pxr::UsdPrim& curvePrim,
                                            const pxr::TfToken& remappingToken,
                                            const pxr::UsdGeomXformOp::Type& rotateOpType,
                                            double time)
{
    double lowerTime, upperTime;
    bool hasSample;
    pxr::GfQuaternion q;

    auto rotateXAttribute = curvePrim.GetAttribute(s_tokenRotateX);
    if (!rotateXAttribute.GetBracketingTimeSamples(time, &lowerTime, &upperTime, &hasSample))
        return pxr::GfQuaternion(0);

    auto rotateYAttribute = curvePrim.GetAttribute(s_tokenRotateY);
    if (!rotateYAttribute.GetBracketingTimeSamples(time, &lowerTime, &upperTime, &hasSample))
        return pxr::GfQuaternion(0);

    auto rotateZAttribute = curvePrim.GetAttribute(s_tokenRotateZ);
    if (!rotateZAttribute.GetBracketingTimeSamples(time, &lowerTime, &upperTime, &hasSample))
        return pxr::GfQuaternion(0);

    double t = 0.0;
    if (upperTime > lowerTime)
    {
        t = (time - lowerTime) / (upperTime - lowerTime);
    }

    // always apply ease in-ease out on slerp (TODO - make this as another option)
    t = getRemappedTime(t, remappingToken);

    double lowerRotateX, upperRotateX, lowerRotateY, upperRotateY, lowerRotateZ, upperRotateZ;

    getAttributeValueWithPrecision(rotateXAttribute, lowerRotateX, lowerTime);
    getAttributeValueWithPrecision(rotateYAttribute, lowerRotateY, lowerTime);
    getAttributeValueWithPrecision(rotateZAttribute, lowerRotateZ, lowerTime);

    getAttributeValueWithPrecision(rotateXAttribute, upperRotateX, upperTime);
    getAttributeValueWithPrecision(rotateYAttribute, upperRotateY, upperTime);
    getAttributeValueWithPrecision(rotateZAttribute, upperRotateZ, upperTime);

    bool valid = false;
    pxr::GfQuaternion lowerQuat =
        getQuaternion(pxr::GfVec3d(lowerRotateX, lowerRotateY, lowerRotateZ), rotateOpType, valid);
    pxr::GfQuaternion upperQuat =
        getQuaternion(pxr::GfVec3d(upperRotateX, upperRotateY, upperRotateZ), rotateOpType, valid);

    pxr::GfQuaternion quat = slerp(t, lowerQuat, upperQuat);

    return quat;
}

// find global interpolation type at current time.  If interpolation type is not defined, return default type (linear)
inline pxr::TfToken getGlobalInterpolationToken(const pxr::UsdPrim& curvePrim, double timeCode)
{
    pxr::TfToken defaultInterpolationToken = s_interpolationTypeLinearToken;

    auto globalInterpolationAttribute = curvePrim.GetAttribute(s_tokenInterpolationType);
    if (!globalInterpolationAttribute)
        return defaultInterpolationToken;

    pxr::TfToken authoredInterpolationToken;
    if (globalInterpolationAttribute.Get(&authoredInterpolationToken, timeCode))
        return authoredInterpolationToken;

    return defaultInterpolationToken;
}

class AnimXCurve : public ICurve
{
protected:
    static double convertTime(int64_t time)
    {
        return (double)time / ticksPerSec;
    }

    static int64_t convertTime(double time)
    {
        return (int64_t)(time * ticksPerSec);
    }

    bool keyframe(double time, Keyframe& key, bool readLinearInterp) const
    {
        auto index = getOrgKey(time);
        if (index >= curve.size())
            return false;

        key = convertKey(curve[index], index, readLinearInterp);

        return true;
    }

    bool keyframeAtIndex(int index, Keyframe& key, bool readLinearInterp) const
    {
        if (index < 0 || index >= curve.size())
            return false;

        key = convertKey(curve[index], index, readLinearInterp);

        return true;
    }

    Keyframe convertKey(const Key& orgKey, int index, bool readLinearInterp) const
    {
        Keyframe key;
        key.time = convertTime(orgKey.time);
        key.value = orgKey.value;
        key.index = index;

        key.tanIn.x = -convertTime(orgKey.inTangent.time) * 3;
        key.tanIn.y = -orgKey.inTangent.value * 3;
        key.tanOut.x = convertTime(orgKey.outTangent.time) * 3;
        key.tanOut.y = orgKey.outTangent.value * 3;

        auto convertTangetType = [](const TfToken& tangentType)
        {
            if (tangentType == "fixed")
                return TangentType::Fixed;
            else if (tangentType == "linear")
                return TangentType::Linear;
            else if (tangentType == "step")
                return TangentType::Step;
            else
                return TangentType::Auto;
        };

        key.tanIn.type = convertTangetType(orgKey.inTangent.type);
        key.tanOut.type = convertTangetType(orgKey.outTangent.type);

        if (key.tanOut.type == TangentType::Linear)
        {
            key.linearInterpolation = true;

            Keyframe nextKey;
            if (readLinearInterp && keyframeAtIndex(key.index + 1, nextKey, false))
            {
                key.linearInterpolation = nextKey.tanIn.type == TangentType::Linear;
            }
        }
        else
            key.linearInterpolation = false;

        return key;
    }

public:
    mutable bool tangentWeighted = true;

    const std::vector<Key>& curve;

    const InfinityType PreInfinityType;
    const InfinityType PostInfinityType;

    AnimXCurve(const std::vector<Key>& curve, InfinityType preInfinityType, InfinityType postInfinityType)
        : curve(curve), PreInfinityType(preInfinityType), PostInfinityType(postInfinityType)
    {
    }

    unsigned getOrgKey(double time) const
    {
        Key orgKey;
        orgKey.time = convertTime(time);
        auto itr = std::lower_bound(curve.begin(), curve.end(), orgKey,
                                    [](const Key& left, const Key& right) { return left.time < right.time; });

        return (unsigned)(itr - curve.begin());
    }

    // Inherited via ICurve
    virtual bool keyframeAtIndex(int index, Keyframe& key) const override
    {
        return keyframeAtIndex(index, key, true);
    }
    virtual bool keyframe(double time, Keyframe& key) const override
    {
        return keyframe(time, key, true);
    }
    virtual bool first(Keyframe& key) const override
    {
        return keyframeAtIndex(0, key);
    }
    virtual bool last(Keyframe& key) const override
    {
        return keyframeAtIndex(keyframeCount() - 1, key);
    }
    virtual InfinityType preInfinityType() const override
    {
        return PreInfinityType;
    }
    virtual InfinityType postInfinityType() const override
    {
        return PostInfinityType;
    }
    virtual bool isWeighted() const override
    {
        return tangentWeighted;
    }
    virtual unsigned int keyframeCount() const override
    {
        return (unsigned)curve.size();
    }
    virtual bool isStatic() const override
    {
        return false;
    }
};

namespace adsk
{
// a simple extracted helper function.
inline double getCurveValueRange(double firstTime, double lastTime, const AnimXCurve& curve)
{
    double firstValue = evaluateCurve(firstTime, curve);
    double lastValue = evaluateCurve(lastTime, curve);
    double range = lastValue - firstValue;
    return range;
}

bool evaluateInfinity(double time, const AnimXCurve& curve, double& value);

bool evaluateCurve(double time, const AnimXCurve& curve, double& value)
{
    Keyframe first, last;
    if (!curve.first(first) || !curve.last(last))
        return false;

    if (first.time <= time && time <= last.time)
    {
        auto nextIndex = curve.getOrgKey(time);
        auto& nextKey = curve.curve[nextIndex];
        curve.tangentWeighted = nextKey.tangentWeighted;
        if (nextIndex > 0)
        {
            auto& prevKey = curve.curve[nextIndex - 1];
            if (prevKey.tangentWeighted)
                curve.tangentWeighted = true;
        }

        value = evaluateCurve(time, curve);
        return true;
    }
    else
    {
        return evaluateInfinity(time, curve, value);
    }
}

// 1. fixes toTickDoubleTime() problem of AnimX.
// 2. Add tangentWeighted per key.
bool evaluateInfinity(double time, const AnimXCurve& curve, double& value)
{
    auto tangent = [](const ICurve& curve, unsigned int index, bool inTangent)
    {
        Keyframe key;
        curve.keyframeAtIndex(index, key);
        double tanTime, tanValue;

        if (inTangent)
        {
            tanTime = key.tanIn.x;
            tanValue = key.tanIn.y;
        }
        else
        {
            tanTime = key.tanOut.x;
            tanValue = key.tanOut.y;
        }

        tanTime = std::max(tanTime, 1.0e-10);
        return tanValue / tanTime;
    };

    Keyframe first, last;
    if (!curve.first(first) || !curve.last(last))
        return false;

    Infinity infinity;
    if (time >= last.time)
    {
        infinity = Infinity::Post;
    }
    else
    {
        // sanity check.
        CARB_ASSERT(time < first.time);
        infinity = Infinity::Pre;
    }

    InfinityType preInfinityType = curve.preInfinityType();
    InfinityType postInfinityType = curve.postInfinityType();

    double range = last.time - first.time;
    double remainder, numCycles, notUsed, factoredTime;

    if (range == 0)
    {
        // special case zero range. Must fallback to Constant type
        factoredTime = first.time;
        numCycles = 0;
        preInfinityType = postInfinityType = InfinityType::Constant;
    }
    else
    {
        double diff = time - (infinity == Infinity::Post ? last.time : first.time);
        auto ratio = diff / range;
        remainder = fabs(modf(ratio, &numCycles));

        factoredTime = range * remainder;
        numCycles = fabs(numCycles) + 1;
    }

    if (infinity == Infinity::Pre)
    {
        if (preInfinityType == InfinityType::Oscillate)
        {
            if ((remainder = modf((numCycles / 2), &notUsed)) != 0.0)
                factoredTime = first.time + factoredTime;
            else
                factoredTime = last.time - factoredTime;
        }
        else if (preInfinityType == InfinityType::Cycle || preInfinityType == InfinityType::CycleRelative)
        {
            factoredTime = last.time - factoredTime;
        }
        else if (preInfinityType == InfinityType::Linear)
        {
            double inc = first.time - time;
            value = first.value - inc * tangent(curve, 0, false);
            return true;
        }
        else
        {
            value = adsk::evaluateCurve(first.time, curve);
            return true;
        }
    }
    else
    {
        if (postInfinityType == InfinityType::Oscillate)
        {
            if ((remainder = modf((numCycles / 2), &notUsed)) != 0.0)
                factoredTime = last.time - factoredTime;
            else
                factoredTime = first.time + factoredTime;
        }
        else if (postInfinityType == InfinityType::Cycle || postInfinityType == InfinityType::CycleRelative)
        {
            factoredTime = first.time + factoredTime;
        }
        else if (postInfinityType == InfinityType::Linear)
        {
            double inc = time - last.time;
            value = last.value + inc * tangent(curve, last.index, true);
            return true;
        }
        else
        {
            value = adsk::evaluateCurve(last.time, curve);
            return true;
        }
    }

    auto ret = evaluateCurve(factoredTime, curve, value);
    if (!ret)
        return false;

    if (infinity == Infinity::Pre && preInfinityType == InfinityType::CycleRelative)
    {
        range = getCurveValueRange(first.time, last.time, curve);
        value -= numCycles * range;
    }
    else if (infinity == Infinity::Post && postInfinityType == InfinityType::CycleRelative)
    {
        range = getCurveValueRange(first.time, last.time, curve);
        value += numCycles * range;
    }
    return true;
}
}

bool getInterpolatedValue(const std::vector<Key>& curve,
                          InfinityType preInfinityType,
                          InfinityType postInfinityType,
                          double time,
                          double& interpolatedValue)
{
    AnimXCurve animXCurve(curve, preInfinityType, postInfinityType);
    bool ret = evaluateCurve(time, animXCurve, interpolatedValue);
    return ret;
}

bool getInterpolatedValue(const pxr::UsdPrim& curvePrim,
                          const pxr::TfToken& valueToken,
                          const pxr::TfToken& tangentTimeToken,
                          const pxr::TfToken& tangentValueToken,
                          const pxr::TfToken& interpolationToken,
                          const pxr::TfToken& remappingToken,
                          double time,
                          double& interpolatedValue)
{
    // value, tangent, interpolation type per attribute
    auto valueAttribute = curvePrim.GetAttribute(valueToken);
    if (!valueAttribute)
        return false;

    if (!valueAttribute.HasAuthoredValue())
        return false;

    auto tangentTimeAttribute = curvePrim.GetAttribute(tangentTimeToken);
    auto tangentValueAttribute = curvePrim.GetAttribute(tangentValueToken);

    double lowerTime;
    double upperTime;
    bool hasSample;

    if (!valueAttribute.GetBracketingTimeSamples(time, &lowerTime, &upperTime, &hasSample))
    {
        // return value at default time
        valueAttribute.Get(&interpolatedValue);
        return true;
    }
    else if (!hasSample)
    {
        // If usdAttribute has no timeSamples array or curve control is not available, fall back to general
        // usdAttribute.Get(v,time).
        valueAttribute.Get(&interpolatedValue);
        return true;
    }
    else if (!tangentTimeAttribute || !tangentValueAttribute)
    {
        // If usdAttribute has no timeSamples array or curve control is not available, fall back to general
        // usdAttribute.Get(v,time).
        getAttributeValueWithPrecision(valueAttribute, interpolatedValue, time);
        return true;
    }

    // check interpolation type
    auto interpolationAttribute = curvePrim.GetAttribute(interpolationToken);

    pxr::TfToken authoredInterpolationToken;
    pxr::TfToken selectedInterpolationToken;

    // first check if interpolation type is authored per attribute
    // currently, use lowerTime interpolation token to describe interpolation type in the segment between lowerTime and
    // upperTime.
    if (interpolationAttribute && getExactSampleOrDefault(interpolationAttribute, lowerTime, &authoredInterpolationToken))
        selectedInterpolationToken = authoredInterpolationToken;
    else
        selectedInterpolationToken = getGlobalInterpolationToken(curvePrim, lowerTime);

    // check remapping type
    auto remappingAttribute = curvePrim.GetAttribute(remappingToken);

    pxr::TfToken authoredRemappingToken;
    pxr::TfToken selectedRemappingToken;

    if (remappingAttribute && getExactSampleOrDefault(remappingAttribute, lowerTime, &authoredRemappingToken))
        selectedRemappingToken = authoredRemappingToken;
    else
        selectedRemappingToken = getGlobalRemappingToken(curvePrim, lowerTime);

    double lowerValue;
    double upperValue;
    getAttributeValueWithPrecision(valueAttribute, lowerValue, lowerTime);
    getAttributeValueWithPrecision(valueAttribute, upperValue, upperTime);

    double range = upperTime - lowerTime;
    double t = (range == 0.0) ? lowerTime : (time - lowerTime) / range;

    // apply ease in, ease out, etc.
    t = getRemappedTime(t, selectedRemappingToken);

    if ((selectedInterpolationToken == s_interpolationTypeLinearToken) ||
        (selectedInterpolationToken == s_interpolationTypeLinearSlerpToken))
    {
        interpolatedValue = lerp(t, lowerValue, upperValue);
        return true;
    }
    else if (selectedInterpolationToken == s_interpolationTypeStep)
    {
        interpolatedValue = lowerValue;
        return true;
    }
    else if (selectedInterpolationToken == s_interpolationTypeStepNext)
    {
        interpolatedValue = upperValue;
        return true;
    }
    else if ((selectedInterpolationToken == s_interpolationTypeBezierToken) ||
             (selectedInterpolationToken == s_interpolationTypeBezierSlerpToken))
    {
        pxr::GfVec4d lowerTangent = getSampleTangent(tangentTimeAttribute, tangentValueAttribute, lowerTime, lowerValue);
        pxr::GfVec4d upperTangent = getSampleTangent(tangentTimeAttribute, tangentValueAttribute, upperTime, upperValue);

        interpolatedValue =
            interpolateBezierCurve(time, lowerTime, lowerValue, lowerTangent, upperTime, upperValue, upperTangent);
        return true;
    }

    // unknown interpolation type
    valueAttribute.Get(&interpolatedValue);
    return true;
}

TransformData getInterpolatedTransformData(const pxr::UsdPrim& curvePrim, const pxr::UsdPrim& targetPrim, double timeCode)
{
    bool currentScale = false, currentRotate = false, currentTranslate = false;
    double currentTX = 0.0, currentTY = 0.0, currentTZ = 0.0;
    double currentRX = 0.0, currentRY = 0.0, currentRZ = 0.0;
    double currentSX = 1.0, currentSY = 1.0, currentSZ = 1.0;

    // interpolation types
    pxr::TfToken globalInterpolationToken = getGlobalInterpolationToken(curvePrim, timeCode);
    pxr::TfToken globalRemappingToken = getGlobalRemappingToken(curvePrim, timeCode);

    // read attributes, do interpolation, store interpolated data, etc.
#define getInterpVal(name, shotName, axis)                                                                             \
    if (getInterpolatedValue(curvePrim, s_token##name##axis, s_token##name##axis##TangentTime,                         \
                             s_token##name##axis##TangentValue, s_token##name##axis##Interpolation,                    \
                             s_token##name##axis##Remapping, timeCode, current##shotName##axis))                       \
        current##name = true;

    getInterpVal(Scale, S, X);
    getInterpVal(Scale, S, Y);
    getInterpVal(Scale, S, Z);

    getInterpVal(Translate, T, X);
    getInterpVal(Translate, T, Y);
    getInterpVal(Translate, T, Z);

    // rotation angles are computed using two different options - one using quaternion (slerp) and another with curve
    // interpolation of Euler angles
    bool useSlerp = (globalInterpolationToken == s_interpolationTypeLinearSlerpToken) ||
                    (globalInterpolationToken == s_interpolationTypeBezierSlerpToken);
    if (useSlerp)
    {
        pxr::UsdAttribute targetRotateAttr = getRotateAttribute(targetPrim);
        if (!targetRotateAttr) // consider transform op as also rotateOp for decomposition
            targetRotateAttr = targetPrim.GetAttribute(s_tokenXformOpTransform);

        pxr::UsdGeomXformOp rotateOp(targetRotateAttr);

        if (rotateOp)
        {
            pxr::UsdGeomXformOp::Type opType = rotateOp.GetOpType();
            pxr::GfQuaternion quat = getInterpolatedQuaternion(curvePrim, globalRemappingToken, opType, timeCode);
            if (quat != pxr::GfQuaternion())
            {
                currentRotate = true;

                pxr::GfVec3d angles = decomposeQuatToEuler(quat, opType);

                currentRX = angles[0];
                currentRY = angles[1];
                currentRZ = angles[2];
            }
        }
    }
    else // use Euler
    {
        getInterpVal(Rotate, R, X);
        getInterpVal(Rotate, R, Y);
        getInterpVal(Rotate, R, Z);
    }

    return { currentScale, currentRotate, currentTranslate, currentSX, currentSY, currentSZ,
             currentRX,    currentRY,     currentRZ,        currentTX, currentTY, currentTZ };
}

void updateGeneralAttribute(const pxr::UsdPrim& curvePrim,
                            const pxr::UsdPrim& targetPrim,
                            const AttributeTokens& tokens,
                            double timeCode)
{
    for (const auto& attributeToken : tokens)
    {
        double value = 0.0;

        bool result = getInterpolatedValue(curvePrim, attributeToken.valueToken, attributeToken.tangentTimeToken,
                                           attributeToken.tangentValueToken, attributeToken.interpolationTypeToken,
                                           attributeToken.remappingTypeToken, timeCode, value);

        if (!result)
            continue;

        pxr::UsdAttribute targetAttribute = targetPrim.GetAttribute(attributeToken.valueToken);
        if (targetAttribute)
            setAttributeValue(targetAttribute, value);
    }
}

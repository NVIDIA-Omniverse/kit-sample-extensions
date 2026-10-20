// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#define CARB_EXPORTS

#include "Ramp.h"

#include <carb/Framework.h>
#include <carb/PluginUtils.h>

#include <omni/ramp/IRamp.h>

#include <iostream>

const struct carb::PluginImplDesc pluginDesc = { "omni.ramp.plugin", "Omni Ramp.", "NVIDIA",
                                                 carb::PluginHotReload::eEnabled, "dev" };

namespace omni
{
namespace ramp
{

class RampImpl final : public omni::ramp::IRamp
{
private:
    // TODO: Replace with FlatCache API.
    template <typename T>
    static void getArrayFromAttribute(const char* path, T& array)
    {
        pxr::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
        if (!stage)
            return;

        auto attr = stage->GetAttributeAtPath(pxr::SdfPath(path));
        if (!attr.IsValid())
            return;

        auto attrQuery = pxr::UsdAttributeQuery(attr);
        auto currTime = pxr::UsdTimeCode().Default();
        attrQuery.Get(&array, currTime);
    }

    // TODO: Replace with FlatCache API.
    template <typename T>
    static void setArrayToAttribute(const char* path, T& array)
    {
        pxr::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
        if (!stage)
            return;

        auto attr = stage->GetAttributeAtPath(pxr::SdfPath(path));
        if (!attr.IsValid())
            return;

        pxr::UsdAttribute(attr).Set(array);
    }

    template <typename T>
    static void orderKeys(pxr::VtArray<float>& rampPositions, pxr::VtArray<T>& rampValues, pxr::VtArray<int>& rampInterps)
    {
        size_t numRampKeys = rampPositions.size();

        // map indices to positions as pairs
        std::vector<std::pair<float, size_t>> positions_to_indices(numRampKeys);
        for (size_t i = 0; i < numRampKeys; ++i)
            positions_to_indices[i] = std::make_pair(rampPositions[i], i);

        // order pairs by first element (position)
        std::sort(positions_to_indices.begin(), positions_to_indices.end());

        // make a temp copy of values and interpolations
        pxr::VtArray<T> _values(rampValues.begin(), rampValues.end());
        pxr::VtArray<int> _interps(rampInterps.begin(), rampInterps.end());

        // write-out reordered data
        for (size_t i = 0; i < numRampKeys; ++i)
        {
            rampPositions[i] = positions_to_indices[i].first;
            rampValues[i] = _values[positions_to_indices[i].second];
            rampInterps[i] = _interps[positions_to_indices[i].second];
        }
    }

public:
    void onStartup(const char* extId)
    {
        CARB_UNUSED(extId);
    }

    void onShutdown()
    {
    }

    //
    // float (scalar) ramp
    //

    float getFloatAtPosition(const float position,
                             const char* rampPositionsAttrPath,
                             const char* rampValuesAttrPath,
                             const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> positions;
        getArrayFromAttribute(rampPositionsAttrPath, positions);
        pxr::VtArray<float> values;
        getArrayFromAttribute(rampValuesAttrPath, values);
        pxr::VtArray<int> interps;
        getArrayFromAttribute(rampInterpsAttrPath, interps);

        size_t numRampKeys = positions.size();
        if (values.size() < numRampKeys)
            numRampKeys = values.size();
        if (interps.size() < numRampKeys)
            numRampKeys = interps.size();

        float out = 0;
        ::ramp::sampleFloatValue(out, position, 0, numRampKeys, positions.data(), values.data(), interps.data());

        return out;
    }

    float getFloatAtPositionFromData(
        const float position, const size_t numRampKeys, const float* positions, const float* values, const int* interps)
    {
        float out = 0;
        ::ramp::sampleFloatValue(out, position, 0, numRampKeys, positions, values, interps);

        return out;
    }

    void getFloatArray(const size_t numElements,
                       float* out,
                       const float* positions,
                       const char* rampPositionsAttrPath,
                       const char* rampValuesAttrPath,
                       const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<float> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        ::ramp::sampleFloatArray(numElements, out, positions, 0, rampPositions.size(), rampPositions.data(),
                                 rampValues.data(), rampInterps.data());
    }

    void getFloatArray2(const size_t numElements,
                        float* out,
                        const float* positions,
                        const size_t numRampKeys,
                        const float* rampPositions,
                        const float* rampValues,
                        const int* rampInterps)
    {
        ::ramp::sampleFloatArray(numElements, out, positions, 0, numRampKeys, rampPositions, rampValues, rampInterps);
    }


    void sampleFloatArray(const size_t numElements,
                          float* out,
                          const float* positions,
                          const int rampMode,
                          const size_t numRampKeys,
                          const float* rampPositions,
                          const float* rampValues,
                          const int* rampInterps)
    {
        ::ramp::sampleFloatArray(
            numElements, out, positions, rampMode, numRampKeys, rampPositions, rampValues, rampInterps);
    }

    void addFloatKey(const float position,
                     const float value,
                     const int interpolation,
                     const char* rampPositionsAttrPath,
                     const char* rampValuesAttrPath,
                     const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<float> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        rampPositions.push_back(position);
        rampValues.push_back(value);
        rampInterps.push_back(interpolation);

        orderKeys(rampPositions, rampValues, rampInterps);

        setArrayToAttribute(rampPositionsAttrPath, rampPositions);
        setArrayToAttribute(rampValuesAttrPath, rampValues);
        setArrayToAttribute(rampInterpsAttrPath, rampInterps);
    }

    void editFloatKey(const size_t index,
                      const float position,
                      const float value,
                      const int interpolation,
                      const char* rampPositionsAttrPath,
                      const char* rampValuesAttrPath,
                      const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<float> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        rampPositions[index] = position;
        rampValues[index] = value;
        rampInterps[index] = interpolation;

        orderKeys(rampPositions, rampValues, rampInterps);

        setArrayToAttribute(rampPositionsAttrPath, rampPositions);
        setArrayToAttribute(rampValuesAttrPath, rampValues);
        setArrayToAttribute(rampInterpsAttrPath, rampInterps);
    }

    void removeFloatKey(const size_t index,
                        const char* rampPositionsAttrPath,
                        const char* rampValuesAttrPath,
                        const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<float> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        rampPositions.erase(rampPositions.begin() + index);
        rampValues.erase(rampValues.begin() + index);
        rampInterps.erase(rampInterps.begin() + index);

        setArrayToAttribute(rampPositionsAttrPath, rampPositions);
        setArrayToAttribute(rampValuesAttrPath, rampValues);
        setArrayToAttribute(rampInterpsAttrPath, rampInterps);
    }

    //
    // float3 (color) ramp
    //

    carb::Float3 getFloat3AtPosition(const float position,
                                     const char* rampPositionsAttrPath,
                                     const char* rampValuesAttrPath,
                                     const char* rampInterpsAttrPath)
    {
        // TODO: Replace with FlatCache API.
        pxr::VtArray<float> positions;
        getArrayFromAttribute(rampPositionsAttrPath, positions);
        pxr::VtArray<pxr::GfVec3f> values;
        getArrayFromAttribute(rampValuesAttrPath, values);
        pxr::VtArray<int> interps;
        getArrayFromAttribute(rampInterpsAttrPath, interps);

        size_t numRampKeys = positions.size();
        if (values.size() < numRampKeys)
            numRampKeys = values.size();
        if (interps.size() < numRampKeys)
            numRampKeys = interps.size();

        carb::Float3 out;
        ::ramp::sampleFloat3Value(out, position, 0, numRampKeys, positions.data(),
                                  reinterpret_cast<const carb::Float3*>(values.data()), interps.data());

        return out;
    }

    carb::Float3 getFloat3AtPositionFromData(const float position,
                                             const size_t numRampKeys,
                                             const float* positions,
                                             const carb::Float3* values,
                                             const int* interps)
    {
        carb::Float3 out;
        ::ramp::sampleFloat3Value(out, position, 0, numRampKeys, positions, values, interps);

        return out;
    }

    void getFloat3Array(const size_t numElements,
                        carb::Float3* out,
                        const float* positions,
                        const char* rampPositionsAttrPath,
                        const char* rampValuesAttrPath,
                        const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<pxr::GfVec3f> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        ::ramp::sampleFloat3Array(numElements, out, positions, 0, rampPositions.size(), rampPositions.data(),
                                  reinterpret_cast<carb::Float3*>(rampValues.data()), rampInterps.data());
    }

    void sampleFloat3Array(const size_t numElements,
                           carb::Float3* out,
                           const float* positions,
                           const int rampMode,
                           const size_t numRampKeys,
                           const float* rampPositions,
                           const carb::Float3* rampValues,
                           const int* rampInterps)
    {
        ::ramp::sampleFloat3Array(
            numElements, out, positions, rampMode, numRampKeys, rampPositions, rampValues, rampInterps);
    }

    void addFloat3Key(const float position,
                      const carb::Float3 value,
                      const int interpolation,
                      const char* rampPositionsAttrPath,
                      const char* rampValuesAttrPath,
                      const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<pxr::GfVec3f> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        rampPositions.push_back(position);
        rampValues.push_back(pxr::GfVec3f(value.x, value.y, value.z));
        rampInterps.push_back(interpolation);

        orderKeys(rampPositions, rampValues, rampInterps);

        setArrayToAttribute(rampPositionsAttrPath, rampPositions);
        setArrayToAttribute(rampValuesAttrPath, rampValues);
        setArrayToAttribute(rampInterpsAttrPath, rampInterps);
    }

    void editFloat3Key(const size_t index,
                       const float position,
                       const carb::Float3 value,
                       const int interpolation,
                       const char* rampPositionsAttrPath,
                       const char* rampValuesAttrPath,
                       const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<pxr::GfVec3f> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        rampPositions[index] = position;
        rampValues[index] = pxr::GfVec3f(value.x, value.y, value.z);
        rampInterps[index] = interpolation;

        orderKeys(rampPositions, rampValues, rampInterps);

        setArrayToAttribute(rampPositionsAttrPath, rampPositions);
        setArrayToAttribute(rampValuesAttrPath, rampValues);
        setArrayToAttribute(rampInterpsAttrPath, rampInterps);
    }

    void removeFloat3Key(const size_t index,
                         const char* rampPositionsAttrPath,
                         const char* rampValuesAttrPath,
                         const char* rampInterpsAttrPath)
    {
        pxr::VtArray<float> rampPositions;
        getArrayFromAttribute(rampPositionsAttrPath, rampPositions);
        pxr::VtArray<pxr::GfVec3f> rampValues;
        getArrayFromAttribute(rampValuesAttrPath, rampValues);
        pxr::VtArray<int> rampInterps;
        getArrayFromAttribute(rampInterpsAttrPath, rampInterps);

        rampPositions.erase(rampPositions.begin() + index);
        rampValues.erase(rampValues.begin() + index);
        rampInterps.erase(rampInterps.begin() + index);

        setArrayToAttribute(rampPositionsAttrPath, rampPositions);
        setArrayToAttribute(rampValuesAttrPath, rampValues);
        setArrayToAttribute(rampInterpsAttrPath, rampInterps);
    }
};
}
}


CARB_PLUGIN_IMPL(pluginDesc, omni::ramp::RampImpl)

void fillInterface(omni::ramp::RampImpl& iface)
{
    iface = {};
}

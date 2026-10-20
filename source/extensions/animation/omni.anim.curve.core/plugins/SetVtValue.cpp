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

#ifdef _MSC_VER
#    pragma warning(disable : 4506 4244)
#endif

using namespace pxr;

typedef std::array<int8_t, sizeof(GfVec4d)> ValueUnion;

struct Functions
{
    void (*setValue)(double, int, VtValue&);
    bool (*setAttrValue)(UsdAttribute& attr, const VtValue& value);
    ValueUnion (*getValueRawData)(const VtValue&);
    void (*setValueRaw)(double, int, void*);
    void (*convertPrecision)(double&);
};

template <typename T, std::enable_if_t<!GfIsGfVec<T>::value, bool> = true>
static void convertPrecision(double& value)
{
    value = (T)value;
}

template <typename T, std::enable_if_t<GfIsGfVec<T>::value, bool> = true>
static void convertPrecision(double& value)
{
    value = (typename T::ScalarType)value;
}

template <typename T>
static bool setAttrValue(UsdAttribute& attr, const VtValue& value)
{
    return attr.Set(value.Get<T>());
}

template <typename T>
static ValueUnion getValueRawData(const VtValue& vtValue)
{
    T value = vtValue.Get<T>();
    ValueUnion valueUnion;
    std::memcpy(valueUnion.data(), &value, sizeof(value));
    return valueUnion;
}

template <typename T, std::enable_if_t<GfIsGfVec<T>::value, bool> = true>
static void setValueRaw(double value, int index, void* data)
{
    auto& dataT = *(T*)data;
    dataT[index] = (typename T::ScalarType)value;
}

template <typename T, std::enable_if_t<GfIsGfVec<T>::value, bool> = true>
static void setValue(double value, int index, VtValue& attrValue)
{
    T rawValue = {};

    if (!attrValue.IsEmpty())
    {
        rawValue = attrValue.Get<T>(); // c4506
    }

    rawValue[index] = (typename T::ScalarType)value;
    attrValue = rawValue;
}

template <typename T, std::enable_if_t<!GfIsGfVec<T>::value, bool> = true>
static void setValueRaw(double value, int index, void* data)
{
    auto& dataT = *(T*)data;
    dataT = (T)value;
}

template <typename T, std::enable_if_t<!GfIsGfVec<T>::value, bool> = true>
static void setValue(double value, int index, VtValue& attrValue)
{
    attrValue = (T)value; // c4244
}

#define SetValueEntry(type)                                                                                            \
    {                                                                                                                  \
        TfType::Find<type>(),                                                                                          \
        {                                                                                                              \
            setValue<type>, setAttrValue<type>, getValueRawData<type>, setValueRaw<type>, convertPrecision<type>       \
        }                                                                                                              \
    }

#define SetValueVecEntry(type, shortType)                                                                              \
    SetValueEntry(type), SetValueEntry(GfVec2##shortType), SetValueEntry(GfVec3##shortType),                           \
        SetValueEntry(GfVec4##shortType)

static std::map<TfType, Functions> setValueFuncs = { SetValueEntry(bool),        SetValueEntry(uint8_t),
                                                     SetValueEntry(int32_t),     SetValueEntry(uint32_t),
                                                     SetValueEntry(int64_t),     SetValueEntry(uint64_t),
                                                     SetValueVecEntry(int, i),   SetValueVecEntry(GfHalf, h),
                                                     SetValueVecEntry(float, f), SetValueVecEntry(double, d) };

bool setVtValue(double value, int index, void* data, const TfType& type)
{
    auto itr = setValueFuncs.find(type);
    if (itr == setValueFuncs.end())
        return false;

    itr->second.setValueRaw(value, index, data);

    return true;
}

bool setVtValue(double value, int index, VtValue& vtValue)
{
    auto itr = setValueFuncs.find(vtValue.GetType());
    if (itr == setValueFuncs.end())
        return false;

    itr->second.setValue(value, index, vtValue);
    return true;
}

ValueUnion getValueRawData(const VtValue& vtValue)
{
    return setValueFuncs.find(vtValue.GetType())->second.getValueRawData(vtValue);
}

bool setAttrValue(UsdAttribute& attr, const VtValue& value)
{
    auto itr = setValueFuncs.find(value.GetType());
    if (itr == setValueFuncs.end())
        return false;

    return itr->second.setAttrValue(attr, value);
}

bool isValueTypeSupported(const TfType& type)
{
    return setValueFuncs.find(type) != setValueFuncs.end();
}

bool convertToAttrPrecision(const UsdAttribute& attr, double& value)
{
    auto itr = setValueFuncs.find(attr.GetTypeName().GetType());
    if (itr == setValueFuncs.end())
        return false;

    itr->second.convertPrecision(value);

    return true;
}

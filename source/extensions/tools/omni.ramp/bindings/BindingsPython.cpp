// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <carb/BindingsPythonUtils.h>
#include <carb/logging/Log.h>

#include <omni/ramp/IRamp.h>

#include <iostream>
#include <vector>

CARB_BINDINGS("omni.ramp.python")

namespace
{
// helper functions
//
static py::list getFloatArray(omni::ramp::IRamp& IRamp,
                              const py::list positions,
                              const char* rampPositionsAttrPath,
                              const char* rampValuesAttrPath,
                              const char* rampInterpsAttrPath)
{
    size_t numElements = positions.size();

    size_t i = 0;
    std::vector<float> _positions(numElements);
    for (py::handle pos : positions)
        _positions[i++] = pos.cast<float>();

    std::vector<float> _out(numElements);
    IRamp.getFloatArray(positions.size(), _out.data(), _positions.data(), rampPositionsAttrPath, rampValuesAttrPath,
                        rampInterpsAttrPath);

    return py::cast(_out);
}

static py::list getFloat3Array(omni::ramp::IRamp& IRamp,
                               const py::list positions,
                               const char* rampPositionsAttrPath,
                               const char* rampValuesAttrPath,
                               const char* rampInterpsAttrPath)
{
    size_t numElements = positions.size();

    size_t i = 0;
    std::vector<float> _positions(numElements);
    for (py::handle pos : positions)
        _positions[i++] = pos.cast<float>();

    std::vector<carb::Float3> _out(numElements);
    IRamp.getFloat3Array(positions.size(), _out.data(), _positions.data(), rampPositionsAttrPath, rampValuesAttrPath,
                         rampInterpsAttrPath);

    i = 0;
    py::list l(numElements);
    for (carb::Float3 v : _out)
        l[i++] = py::make_tuple(v.x, v.y, v.z);

    return l;
}


static py::list getFloatArrayFromRampData(omni::ramp::IRamp& IRamp,
                                          const py::list positions,
                                          py::list rampPositionsPy,
                                          py::list rampValuesPy,
                                          py::list rampInterpsPy)
{
    size_t numKeys = std::min(rampPositionsPy.size(), std::min(rampValuesPy.size(), rampInterpsPy.size()));
    float* rampPositions = new float[numKeys];
    float* rampValues = new float[numKeys];
    int* rampInterps = new int[numKeys];
    for (size_t i = 0; i < numKeys; i++)
        rampPositions[i] = rampPositionsPy[i].cast<float>();
    for (size_t i = 0; i < numKeys; i++)
        rampValues[i] = rampValuesPy[i].cast<float>();
    for (size_t i = 0; i < numKeys; i++)
        rampInterps[i] = rampInterpsPy[i].cast<int>();

    size_t numElements = positions.size();

    size_t i = 0;
    std::vector<float> _positions(numElements);
    for (py::handle pos : positions)
        _positions[i++] = pos.cast<float>();

    std::vector<float> _out(numElements);

    IRamp.getFloatArray2(numElements, _out.data(), _positions.data(), numKeys, rampPositions, rampValues, rampInterps);

    delete[] rampPositions;
    delete[] rampValues;
    delete[] rampInterps;

    return py::cast(_out);
}

static py::list generateBitmap(const size_t numPixelsX,
                               const size_t numPixelsY,
                               // min/max values are provided by caller instead of
                               // being computed live from the ramp arrays to
                               // accommodate for specific ui/ux behavior
                               const float minValue,
                               const float maxValue,
                               std::vector<float>& values)
{
    const float range = maxValue - minValue;
    const size_t zero = minValue < 0 && maxValue > 0 ? size_t(fabs(minValue) / range * numPixelsY) : 0;

    py::list out(numPixelsX * numPixelsY * 4);
    std::vector<unsigned char> rgba(numPixelsX * numPixelsY * 4, 255);

    unsigned char _y = 0;
    const size_t _numPixelsX = numPixelsX * 4;
    const size_t _numPixelsY = numPixelsY - 1;
    for (size_t x = 0; x < numPixelsX; ++x)
    {
        const size_t _x = x * 4;
        for (size_t y = 0; y < numPixelsY; ++y)
        {
            const size_t index = (_numPixelsY - y) * _numPixelsX + _x;

            rgba[index] = rgba[index + 1] = rgba[index + 2] = rgba[index + 3] = 255;

            _y = range ? (unsigned char)((values[x] - minValue) / range * _numPixelsY) : 0;

            rgba[index + 3] = y > _y ? 0 : 24;

            if (y == zero && zero != 0 && !(x % 4))
            {
                rgba[index] = rgba[index + 1] = rgba[index + 2] = 0;
                rgba[index + 3] = 255;
            }
            else if (y > 0)
            {
                const size_t index2 = (numPixelsY - y) * _numPixelsX + _x;
                if (rgba[index + 3] != rgba[index2 + 3] && rgba[index2 + 3] != 255 && rgba[index + 3] != 24)
                {
                    rgba[index] = rgba[index + 1] = rgba[index + 2] = 96;
                    rgba[index + 3] = 255;
                }
            }

            out[index] = rgba[index];
            out[index + 1] = rgba[index + 1];
            out[index + 2] = rgba[index + 2];
            out[index + 3] = rgba[index + 3];
        }
    }
    return out;
}


// Populating arrays in Python is too slow for interactive UX.
// Package data here instead.
static py::list getFloatArrayAsRGBA8(omni::ramp::IRamp& IRamp,
                                     const size_t numPixelsX,
                                     const size_t numPixelsY,
                                     // min/max values are provided by caller instead of
                                     // being computed live from the ramp arrays to
                                     // accommodate for specific ui/ux behavior
                                     const float minValue,
                                     const float maxValue,
                                     const char* rampPositionsAttrPath,
                                     const char* rampValuesAttrPath,
                                     const char* rampInterpsAttrPath)
{
    // quit early if image with no pixels
    if (!numPixelsX || !numPixelsY)
        return py::list(0);

    std::vector<float> values(numPixelsX);
    std::vector<float> positions(numPixelsX);
    for (size_t i = 0; i < numPixelsX; ++i)
        positions[i] = (float)i / (numPixelsX - 1);

    IRamp.getFloatArray(positions.size(), values.data(), positions.data(), rampPositionsAttrPath, rampValuesAttrPath,
                        rampInterpsAttrPath);

    auto out = generateBitmap(numPixelsX, numPixelsY, minValue, maxValue, values);
    return out;
}

static py::list getFloatArrayAsRGBA8_2(omni::ramp::IRamp& IRamp,
                                       const size_t numPixelsX,
                                       const size_t numPixelsY,
                                       // min/max values are provided by caller instead of
                                       // being computed live from the ramp arrays to
                                       // accommodate for specific ui/ux behavior
                                       const float minValue,
                                       const float maxValue,
                                       py::list rampPositionsPy,
                                       py::list rampValuesPy,
                                       py::list rampInterpsPy)
{
    size_t numElements = rampPositionsPy.size();
    if (rampValuesPy.size() < numElements)
        numElements = rampValuesPy.size();
    if (rampInterpsPy.size() < numElements)
        numElements = rampInterpsPy.size();

    float* rampPositions = new float[numElements];
    float* rampValues = new float[numElements];
    int* rampInterps = new int[numElements];
    for (size_t i = 0; i < numElements; i++)
        rampPositions[i] = rampPositionsPy[i].cast<float>();
    for (size_t i = 0; i < numElements; i++)
        rampValues[i] = rampValuesPy[i].cast<float>();
    for (size_t i = 0; i < numElements; i++)
        rampInterps[i] = rampInterpsPy[i].cast<int>();

    if (!numPixelsX || !numPixelsY)
        return py::list(0);

    std::vector<float> values(numPixelsX);
    std::vector<float> positions(numPixelsX);
    for (size_t i = 0; i < numPixelsX; ++i)
        positions[i] = (float)i / (numPixelsX - 1);

    IRamp.getFloatArray2(
        positions.size(), values.data(), positions.data(), numElements, rampPositions, rampValues, rampInterps);

    delete[] rampPositions;
    delete[] rampValues;
    delete[] rampInterps;

    auto out = generateBitmap(numPixelsX, numPixelsY, minValue, maxValue, values);
    return out;
}

// END - helper functions

PYBIND11_MODULE(_omni_ramp, m)
{
    // clang-format off
    using namespace carb;
    using namespace omni::ramp;

    m.doc() = "pybind11 ramp bindings";

    defineInterfaceClass<omni::ramp::IRamp>(m, "IRamp", "acquire_interface", "release_interface")
        .def("get_float_at_position", &omni::ramp::IRamp::getFloatAtPosition, R"(
            Sample float value at position in the ramp.
            )")
        .def("get_float_array", &getFloatArray, R"(
            Sample float values at positions in the ramp.
            )")
        .def("get_float_array_from_ramp_data", &getFloatArrayFromRampData, R"(
            Sample float values at positions in the given ramp data.
            )")
        .def("get_float_array_as_rgba8", &getFloatArrayAsRGBA8, R"(
            Sample float values at positions in the ramp.
            )")
        .def("get_float_array_as_rgba8_2", &getFloatArrayAsRGBA8_2, R"(
            Sample float values at positions in the ramp.
            )")
        .def("add_float_key", &omni::ramp::IRamp::addFloatKey, R"(
            Add float key (position, value, interpolation) at position in the ramp.
            )")
        .def("edit_float_key", &omni::ramp::IRamp::editFloatKey, R"(
            Set position, value and interpolation of a float key in the ramp.
            )")
        .def("remove_float_key", &omni::ramp::IRamp::removeFloatKey, R"(
            Remove float key from the ramp.
            )")

        .def("get_float3_at_position", &omni::ramp::IRamp::getFloat3AtPosition, R"(
            Sample float3 value at position in the ramp.
            )")
        .def("get_float3_array", &getFloat3Array, R"(
            Sample float3 values at positions in the ramp.
            )")
        .def("add_float3_key", &omni::ramp::IRamp::addFloat3Key, R"(
            Add float3 key (position, value, interpolation) at position in the ramp.
            )")
        .def("edit_float3_key", &omni::ramp::IRamp::editFloat3Key, R"(
            Set position, value and interpolation of a float3 key in the ramp.
            )")
        .def("remove_float3_key", &omni::ramp::IRamp::removeFloat3Key, R"(
            Remove float3 key from the ramp.
            )");
}
}

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

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include <carb/Types.h>

#include <omni/usd/UsdContext.h>

#include <omp.h>

namespace ramp
{
enum MODE
{
    OVER,
    ADD,
    MULT
};
enum INTERPOLATION
{
    NONE,
    LINEAR,
    BEZIER
};

static void sampleFloatValue(float& out,
                             float position,
                             int rampMode,
                             size_t numRampKeys,
                             const float* rampPositions,
                             const float* rampValues,
                             const int* rampInterps)
{
    // if no ramp keys
    if (!numRampKeys)
    {
        return;
    }
    // if only one ramp key
    else if (numRampKeys == 1)
    {
        if (rampMode == MODE::OVER)
            out = rampValues[0];
        else if (rampMode == MODE::ADD)
            out += rampValues[0];
        else // mult
            out *= rampValues[0];
    }
    // look up pair of ramp keys
    else
    {
        for (size_t j = 0; j < numRampKeys - 1; ++j)
        {
            // sampled position coincides with the first key
            if (position - rampPositions[j] <= 0.001f)
            {
                if (rampMode == MODE::OVER)
                    out = rampValues[j];
                else if (rampMode == MODE::ADD)
                    out += rampValues[j];
                else // mult
                    out *= rampValues[j];

                break;
            }
            else if (position >= rampPositions[numRampKeys - 1])
            {
                if (rampMode == MODE::OVER)
                    out = rampValues[numRampKeys - 1];
                else if (rampMode == MODE::ADD)
                    out += rampValues[numRampKeys - 1];
                else // mult
                    out *= rampValues[numRampKeys - 1];

                break;
            }
            // sampled position is between the first and second keys
            else if (position > rampPositions[j] && position < rampPositions[j + 1])
            {
                // fit
                float t = rampPositions[j + 1] - rampPositions[j];
                t = (position - rampPositions[j]) / t;

                float t2 = 1.0f - t;
                float c1 = t2 * t2 * t2;
                float c2 = 3 * t2 * t2 * t;
                float c3 = 3 * t2 * t * t;
                float c4 = t * t * t;

                float result = 0;

                if (rampInterps[j] == INTERPOLATION::NONE)
                    result = rampValues[j];
                else if (rampInterps[j] == INTERPOLATION::LINEAR)
                    result = rampValues[j] * (1 - t) + rampValues[j + 1] * t;
                else // bezier
                    result =
                        c1 * rampValues[j] + c2 * rampValues[j] + c3 * (rampValues[j + 1]) + c4 * (rampValues[j + 1]);

                if (rampMode == MODE::OVER)
                    out = result;
                else if (rampMode == MODE::ADD)
                    out += result;
                else // mult
                    out *= result;

                break;
            }
            // sampled position coincides with the second key
            else if (position - rampPositions[j + 1] <= 0.001f ||
                     (position > rampPositions[j + 1] && j + 2 == numRampKeys))
            {
                if (rampMode == MODE::OVER)
                    out = rampValues[j + 1];
                else if (rampMode == MODE::ADD)
                    out += rampValues[j + 1];
                else // mult
                    out *= rampValues[j + 1];

                break;
            }
        }
    }
}

static void sampleFloat3Value(carb::Float3& out,
                              float position,
                              int rampMode,
                              size_t numRampKeys,
                              const float* rampPositions,
                              const carb::Float3* rampValues,
                              const int* rampInterps)
{
    if (!numRampKeys)
    {
        return;
    }

    // if only one ramp key
    else if (numRampKeys == 1)
    {
        if (rampMode == MODE::OVER)
        {
            out.x = rampValues[0].x;
            out.y = rampValues[0].y;
            out.z = rampValues[0].z;
        }
        else if (rampMode == MODE::ADD)
        {
            out.x += rampValues[0].x;
            out.y += rampValues[0].y;
            out.z += rampValues[0].z;
        }
        else // mult
        {
            out.x *= rampValues[0].x;
            out.y *= rampValues[0].y;
            out.z *= rampValues[0].z;
        }
    }
    // look up pair of ramp keys
    else
    {
        for (size_t j = 0; j < numRampKeys - 1; ++j)
        {
            // sampled position coincides with the first key
            if (position - rampPositions[j] <= 0.001f)
            {
                if (rampMode == MODE::OVER)
                {
                    out.x = rampValues[j].x;
                    out.y = rampValues[j].y;
                    out.z = rampValues[j].z;
                }
                else if (rampMode == MODE::ADD)
                {
                    out.x += rampValues[j].x;
                    out.y += rampValues[j].y;
                    out.z += rampValues[j].z;
                }
                else // mult
                {
                    out.x *= rampValues[j].x;
                    out.y *= rampValues[j].y;
                    out.z *= rampValues[j].z;
                }

                break;
            }
            // sampled position is between the first and second keys
            else if (position > rampPositions[j] && position < rampPositions[j + 1])
            {
                // fit
                float t = rampPositions[j + 1] - rampPositions[j];
                t = (position - rampPositions[j]) / t;

                float t2 = 1.0f - t;
                float c1 = t2 * t2 * t2;
                float c2 = 3 * t2 * t2 * t;
                float c3 = 3 * t2 * t * t;
                float c4 = t * t * t;

                carb::Float3 result;
                if (rampInterps[j] == INTERPOLATION::NONE)
                {
                    result.x = rampValues[j].x;
                    result.y = rampValues[j].y;
                    result.z = rampValues[j].z;
                }
                else if (rampInterps[j] == INTERPOLATION::LINEAR)
                {
                    result.x = rampValues[j].x * (1 - t) + rampValues[j + 1].x * t;
                    result.y = rampValues[j].y * (1 - t) + rampValues[j + 1].y * t;
                    result.z = rampValues[j].z * (1 - t) + rampValues[j + 1].z * t;
                }
                else // bezier
                {
                    result.x = c1 * rampValues[j].x + c2 * rampValues[j].x + c3 * (rampValues[j + 1].x) +
                               c4 * (rampValues[j + 1].x);
                    result.y = c1 * rampValues[j].y + c2 * rampValues[j].y + c3 * (rampValues[j + 1].y) +
                               c4 * (rampValues[j + 1].y);
                    result.z = c1 * rampValues[j].z + c2 * rampValues[j].z + c3 * (rampValues[j + 1].z) +
                               c4 * (rampValues[j + 1].z);
                }

                if (rampMode == MODE::OVER)
                {
                    out = result;
                }
                else if (rampMode == MODE::ADD)
                {
                    out.x = out.x + result.x;
                    out.y = out.y + result.y;
                    out.z = out.z + result.z;
                }
                else // mult
                {
                    out.x = out.x * result.x;
                    out.y = out.y * result.y;
                    out.z = out.z * result.z;
                }

                break;
            }
            // sampled position coincides with the second key
            else if (position - rampPositions[j + 1] <= 0.001f ||
                     (position > rampPositions[j + 1] && j + 2 == numRampKeys))
            {
                if (rampMode == MODE::OVER)
                {
                    out.x = rampValues[j + 1].x;
                    out.y = rampValues[j + 1].y;
                    out.z = rampValues[j + 1].z;
                }
                else if (rampMode == MODE::ADD)
                {
                    out.x += rampValues[j + 1].x;
                    out.y += rampValues[j + 1].y;
                    out.z += rampValues[j + 1].z;
                }
                else // mult
                {
                    out.x *= rampValues[j + 1].x;
                    out.y *= rampValues[j + 1].y;
                    out.z *= rampValues[j + 1].z;
                }

                break;
            }
        }
    }
}

static void sampleFloatArray(const size_t numElements,
                             float* out,
                             const float* positions,
                             const int rampMode,
                             const size_t numRampKeys,
                             const float* rampPositions,
                             const float* rampValues,
                             const int* rampInterps)
{
    if (numElements > 10000)
    {
        //        omp_set_num_threads(omp_get_max_threads());
        // #pragma omp parallel for
        for (int i = 0; i < numElements; ++i)
            sampleFloatValue(out[i], positions[i], rampMode, numRampKeys, rampPositions, rampValues, rampInterps);
    }
    else
    {
        for (int i = 0; i < numElements; ++i)
            sampleFloatValue(out[i], positions[i], rampMode, numRampKeys, rampPositions, rampValues, rampInterps);
    }
}

static void sampleFloat3Array(const size_t numElements,
                              carb::Float3* out,
                              const float* positions,
                              const int rampMode,
                              const size_t numRampKeys,
                              const float* rampPositions,
                              const carb::Float3* rampValues,
                              const int* rampInterps)
{
    if (numElements > 10000)
    {
        //        omp_set_num_threads(omp_get_max_threads());
        // #pragma omp parallel for
        for (int i = 0; i < numElements; ++i)
            sampleFloat3Value(out[i], positions[i], rampMode, numRampKeys, rampPositions, rampValues, rampInterps);
    }
    else
    {
        for (int i = 0; i < numElements; ++i)
            sampleFloat3Value(out[i], positions[i], rampMode, numRampKeys, rampPositions, rampValues, rampInterps);
    }
}
}

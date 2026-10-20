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

#include <omni/graph/core/ArrayWrapper.h>
#include <omni/graph/core/Type.h>
#include <omni/graph/dynamics/Types.h>
#include <omni/math/linalg/vec.h>

using omni::graph::core::AttributeRole;
using omni::graph::core::BaseDataType;
using omni::graph::core::Type;
using omni::math::linalg::vec2f;
using omni::math::linalg::vec3f;

namespace omni
{
namespace particle
{
namespace system
{
namespace core2
{

enum class SolverPhase
{
    EMITTER = 0,
    INIT,
    PRESOLVE,
    SOLVER,
    POSTSOLVE,
    EXTINCTION
};


static constexpr Type DoubleType(BaseDataType::eDouble);
static constexpr Type FloatType(BaseDataType::eFloat);
static constexpr Type BoolType(BaseDataType::eBool);
static constexpr Type UInt64Type(BaseDataType::eUInt64);
static constexpr Type IntType(BaseDataType::eInt);
static constexpr Type Float3Type(BaseDataType::eFloat, 3);
static constexpr Type TokenType(BaseDataType::eToken);


static bool BoolArrayTypeDefault{ false };
static vec3f Point3fArrayTypeDefault{ 0.0f, 0.0f, 0.0f };
static vec3f Vector3fArrayTypeDefault{ 0.0f, 0.0f, 0.0f };
static vec3f Float3ArrayTypeDefault{ 0.0f, 0.0f, 0.0f };
static float FloatArrayTypeDefault{ 0.0f };
static int IntArrayTypeDefault{ 0 };
static uint64_t UInt64ArrayTypeDefault{ 0 };
static vec3f Color3fArrayTypeDefault{ 1.0f, 1.0f, 1.0f };


// NOTE: this struct is quite similar to carb::flatcache::AttrNameAndType.
// we may want to consider using that type in the future.
struct ParticleAttrDescription
{
    std::string name;
    Type type;

    bool operator==(const ParticleAttrDescription& other)
    {
        return name == other.name;
    }

    bool operator<(const ParticleAttrDescription& other) const
    {
        return name.compare(other.name) < 0;
    }
};

} // namespace core2
} // namespace system
} // namespace particle
} // namespace omni

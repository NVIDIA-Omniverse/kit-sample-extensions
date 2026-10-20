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

#include <omni/core/IObject.h>

#include <string.h>
#include <vector>

namespace omni
{
namespace particle
{
namespace system
{
namespace core2
{

OMNI_DECLARE_INTERFACE(IParticleSystem);

class IParticleSystem_abi
    : public omni::core::Inherits<omni::core::IObject, OMNI_TYPE_ID("omni.particle.system.core2.IParticleSystem")>
{
protected:
    virtual std::vector<std::pair<std::string, std::string>> getOperatorKeys_abi() noexcept = 0;
};


} // namespace core2
} // namespace system
} // namespace particle
} // namespace omni

#include "IParticleSystem.gen.h"

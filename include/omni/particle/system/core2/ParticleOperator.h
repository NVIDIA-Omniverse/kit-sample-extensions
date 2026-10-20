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

#include "IParticleBuffer.h"
#include "Types.h"

#include <omni/graph/dynamics/IOperatorConfigSerializer.h>
#include <omni/graph/dynamics/Operator.h>

#include <set>

using omni::graph::dynamics::IOperatorConfigSerializer;
using omni::particle::system::core2::ParticleAttrDescription;

namespace omni
{
namespace particle
{
namespace system
{
namespace core2
{


class ParticleOperatorBase : public omni::graph::dynamics::OperatorBase<ObjectPtr<IParticleBuffer>, ParticleHandle>
{
public:
    ParticleOperatorBase() = delete;
    ParticleOperatorBase(const GraphContextObj& context,
                         ObjectPtr<IOperatorConfigSerializer> config,
                         ObjectPtr<IParticleBuffer> manager) noexcept
        : omni::graph::dynamics::OperatorBase<ObjectPtr<IParticleBuffer>, ParticleHandle>(context, config, manager){};

    virtual ~ParticleOperatorBase() = default;

    void initialize() override
    {
    }

    void standup() override
    {
    }

    ElementKernel generateKernel() override
    {
        // default no-op kernel
        return [](ParticleHandle&) {};
    }

    void teardown() override
    {
    }

public:
    virtual SolverPhase getSolverPhase() const
    {
        return SolverPhase::PRESOLVE;
    }

    virtual std::set<ParticleAttrDescription> getRequiredAttributes() const
    {
        return std::set<ParticleAttrDescription>{};
    }

    virtual bool isKernelThreadsafe() const
    {
        return false;
    }
};

using ParticleOperatorFactory =
    omni::graph::dynamics::OperatorFactory<ParticleOperatorBase, omni::core::ObjectPtr<IParticleBuffer>>;


} // namespace core2
} // namespace system
} // namespace particle
} // namespace omni

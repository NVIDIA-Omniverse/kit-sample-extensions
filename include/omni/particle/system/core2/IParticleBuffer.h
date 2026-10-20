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

#include "Types.h"

#include <omni/graph/core/Handle.h>
#include <omni/graph/dynamics/IOperatorConfigSerializer.h>
#include <omni/graph/dynamics/Operator.h>

#include <set>
#include <unordered_map>

using omni::core::ObjectPtr;
using omni::graph::core::GraphContextObj;
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


struct GenericData
{
    void* data;
    omni::graph::dynamics::AttributeType type;
    AttributeDataHandle handle;
};


using NameToData = std::unordered_map<NameToken, GenericData>;


class ParticleHandle
{
public:
    ParticleHandle() = delete;
    ParticleHandle(NameToData* bufferData, const GraphContextObj* context)
        : m_currentIndex(0), m_bufferHeads(bufferData), m_context(context)
    {
    }

    void setIndex(size_t index)
    {
        m_currentIndex = index;
    }

    template <typename T>
    T& get(const char* name)
    {
        return get<T>(m_context->iToken->getHandle(name));
    }

    template <typename T>
    T& get(const NameToken name)
    {
        // TODO error handling for out of range exception
        T* typedHead = reinterpret_cast<T*>(m_bufferHeads->at(name).data);
        return typedHead[m_currentIndex];
    }

    void copy(ParticleHandle& other)
    {
        for (auto& attribute : *m_bufferHeads)
        {
            switch (attribute.second.type)
            {
            case omni::graph::dynamics::AttributeType::VECTOR_ARRAY:
            {
                vec3f* typedHead = reinterpret_cast<vec3f*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<vec3f>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::FLOAT_ARRAY:
            {
                float* typedHead = reinterpret_cast<float*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<float>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::INT_ARRAY:
            {
                int* typedHead = reinterpret_cast<int*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<int>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::UINT64_ARRAY:
            {
                uint64_t* typedHead = reinterpret_cast<uint64_t*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<uint64_t>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::BOOL_ARRAY:
            {
                bool* typedHead = reinterpret_cast<bool*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<bool>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::FLOAT2_ARRAY:
            {
                vec2f* typedHead = reinterpret_cast<vec2f*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<vec2f>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::QUATERNION_ARRAY:
            {
                quatf* typedHead = reinterpret_cast<quatf*>(attribute.second.data);
                typedHead[m_currentIndex] = other.get<quatf>(attribute.first);
            }
            break;
            case omni::graph::dynamics::AttributeType::UNKNOWN:
                // we shouldn't be here
                CARB_ASSERT(0);
                break;
            default:
                // we shouldn't be here
                CARB_ASSERT(0);
            }
        }
    }

    void swap(ParticleHandle& other)
    {
        for (auto& attribute : *m_bufferHeads)
        {
            switch (attribute.second.type)
            {
            case omni::graph::dynamics::AttributeType::VECTOR_ARRAY:
            {
                vec3f* typedHead = reinterpret_cast<vec3f*>(attribute.second.data);
                vec3f temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<vec3f>(attribute.first);
                other.get<vec3f>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::FLOAT_ARRAY:
            {
                float* typedHead = reinterpret_cast<float*>(attribute.second.data);
                float temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<float>(attribute.first);
                other.get<float>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::INT_ARRAY:
            {
                int* typedHead = reinterpret_cast<int*>(attribute.second.data);
                int temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<int>(attribute.first);
                other.get<int>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::UINT64_ARRAY:
            {
                uint64_t* typedHead = reinterpret_cast<uint64_t*>(attribute.second.data);
                uint64_t temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<uint64_t>(attribute.first);
                other.get<uint64_t>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::BOOL_ARRAY:
            {
                bool* typedHead = reinterpret_cast<bool*>(attribute.second.data);
                bool temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<bool>(attribute.first);
                other.get<bool>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::FLOAT2_ARRAY:
            {
                vec2f* typedHead = reinterpret_cast<vec2f*>(attribute.second.data);
                vec2f temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<vec2f>(attribute.first);
                other.get<vec2f>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::QUATERNION_ARRAY:
            {
                quatf* typedHead = reinterpret_cast<quatf*>(attribute.second.data);
                quatf temp = typedHead[m_currentIndex];
                typedHead[m_currentIndex] = other.get<quatf>(attribute.first);
                other.get<quatf>(attribute.first) = temp;
            }
            break;
            case omni::graph::dynamics::AttributeType::UNKNOWN:
                // we shouldn't be here
                CARB_ASSERT(0);
                break;
            default:
                // we shouldn't be here
                CARB_ASSERT(0);
            }
        }
    }

private:
    size_t m_currentIndex;
    NameToData* m_bufferHeads;
    const GraphContextObj* m_context;
};


using ElementKernel = std::function<void(ParticleHandle&)>;
using FilterFn = std::function<bool(ParticleHandle&)>;

OMNI_DECLARE_INTERFACE(IParticleBuffer);

class IParticleBuffer_abi
    : public omni::core::Inherits<omni::core::IObject, OMNI_TYPE_ID("omni.particle.system.core2.IParticleBuffer")>
{
protected:
    virtual size_t getParticleCount_abi() const noexcept = 0;

    virtual bool checkLength_abi(NameToken name, size_t expectedCount) const noexcept = 0;

    virtual void emitParticles_abi(size_t count) noexcept = 0;

    virtual ParticleHandle getParticleHandle_abi() noexcept = 0;

    virtual void deleteParticle_abi(ParticleHandle& deletedParticle) noexcept = 0;

    virtual void shrinkBuffer_abi() noexcept = 0;

    virtual omni::graph::dynamics::AttributeType getType_abi(NameToken name) const noexcept = 0;

    virtual bool hasAttribute_abi(NameToken name) const noexcept = 0;

    virtual void* getAttributeData_abi(NameToken name) noexcept = 0;

    virtual void conformAttributeLengths_abi(size_t maximumCount) noexcept = 0;

    virtual void setIterationInterval_abi(size_t start, size_t end) noexcept = 0;

    virtual void setDt_abi(const float& dt) noexcept = 0;

    virtual float getDt_abi() const noexcept = 0;

    virtual void setCurrentTime_abi(const float& currentTime) noexcept = 0;

    virtual float getCurrentTime_abi() const noexcept = 0;

    virtual void addManagedBuffer_abi(const ParticleAttrDescription& attribute) noexcept = 0;

    virtual void refreshManagedBuffers_abi() noexcept = 0;

    virtual void applyToInterval_abi(ElementKernel kernel, bool parallel) noexcept = 0;

    virtual void deleteParticles_abi(FilterFn filter) noexcept = 0;

    virtual void setSeed_abi(uint64_t seed) noexcept = 0;

    virtual float getNextRandom_abi() noexcept = 0;

    virtual size_t getBufferSize_abi() const noexcept = 0;
};

} // namespace core2
} // namespace system
} // namespace particle
} // namespace omni

#include "IParticleBuffer.gen.h"

OMNI_DEFINE_INTERFACE_API(omni::particle::system::core2::IParticleBuffer){
    public: size_t getParticleCount() const noexcept { return this->getParticleCount_abi();
}

bool checkLength(NameToken name, size_t expectedCount) const noexcept
{
    return this->checkLength_abi(name, expectedCount);
}

void emitParticles(size_t count) noexcept
{
    this->emitParticles_abi(count);
}

omni::particle::system::core2::ParticleHandle getParticleHandle() noexcept
{
    return this->getParticleHandle_abi();
}

void deleteParticle(omni::particle::system::core2::ParticleHandle& deletedParticle) noexcept
{
    this->deleteParticle_abi(deletedParticle);
}

void shrinkBuffer() noexcept
{
    shrinkBuffer_abi();
}

omni::graph::dynamics::AttributeType getType(NameToken name) const noexcept
{
    return getType_abi(name);
}

bool hasAttribute(NameToken name) const noexcept
{
    return hasAttribute_abi(name);
}

void* getAttributeData(NameToken name) noexcept
{
    return this->getAttributeData_abi(name);
}

void conformAttributeLengths(size_t maximumCount) noexcept
{
    this->conformAttributeLengths_abi(maximumCount);
}

void setIterationInterval(size_t start, size_t end) noexcept
{
    this->setIterationInterval_abi(start, end);
}

void setDt(const float& dt) noexcept
{
    this->setDt_abi(dt);
}

float getDt() const noexcept
{
    return this->getDt_abi();
}

void setCurrentTime(const float& currentTime) noexcept
{
    this->setCurrentTime_abi(currentTime);
}

float getCurrentTime() const noexcept
{
    return this->getCurrentTime_abi();
}

void cacheManagedBuffers(const std::set<ParticleAttrDescription>& attributes)
{
    for (const auto& attribute : attributes)
    {
        this->addManagedBuffer_abi(attribute);
    }
}

void addManagedBuffer(const ParticleAttrDescription& attribute) noexcept
{
    this->addManagedBuffer_abi(attribute);
}

void refreshManagedBuffers() noexcept
{
    this->refreshManagedBuffers_abi();
}

void applyToInterval(omni::particle::system::core2::ElementKernel kernel, bool parallel = true) noexcept
{
    this->applyToInterval_abi(kernel, parallel);
}

void deleteParticles(omni::particle::system::core2::FilterFn filter) noexcept
{
    this->deleteParticles_abi(filter);
}

void setSeed(uint64_t seed) noexcept
{
    this->setSeed_abi(seed);
}

float getNextRandom() noexcept
{
    return this->getNextRandom_abi();
}

size_t getBufferSize() const noexcept
{
    return this->getBufferSize_abi();
}
}
;

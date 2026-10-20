// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <omni/core/ITypeFactory.h>
#include <omni/python/PyBind.h>
#include <omni/python/PyString.h>
#include <omni/python/PyVec.h>

#include <sstream>

auto bindGenericData(py::module& m)
{
    py::class_<omni::particle::system::core2::GenericData> s(m, "GenericData");

    s.def(py::init(
              [](void* data, omni::graph::dynamics::AttributeType type, omni::graph::core::AttributeDataHandle handle)
              {
                  omni::particle::system::core2::GenericData tmp;
                  tmp.data = data;
                  tmp.type = type;
                  tmp.handle = handle;

                  return tmp;
              }),
          py::arg("data"), py::arg("type"), py::arg("handle"));

    s.def_readwrite("data", &omni::particle::system::core2::GenericData::data);
    s.def_readwrite("type", &omni::particle::system::core2::GenericData::type);
    s.def_readwrite("handle", &omni::particle::system::core2::GenericData::handle);

    return s;
}

auto bindIParticleBuffer(py::module& m)
{
    // hack around pybind11 issues with C++17
    //   - https://github.com/pybind/pybind11/issues/2234
    //   - https://github.com/pybind/pybind11/issues/2666
    //   - https://github.com/pybind/pybind11/issues/2856
    py::class_<omni::core::Generated<omni::particle::system::core2::IParticleBuffer_abi>,
               omni::core::ObjectPtr<omni::core::Generated<omni::particle::system::core2::IParticleBuffer_abi>>,
               omni::core::IObject>
        clsParent(m, "_IParticleBuffer");
    py::class_<omni::particle::system::core2::IParticleBuffer,
               omni::core::Generated<omni::particle::system::core2::IParticleBuffer_abi>,
               omni::core::ObjectPtr<omni::particle::system::core2::IParticleBuffer>, omni::core::IObject>
        cls(m, "IParticleBuffer");
    cls.def(py::init(
        [](const omni::core::ObjectPtr<omni::core::IObject>& obj)
        {
            auto tmp = omni::core::cast<omni::particle::system::core2::IParticleBuffer>(obj.get());
            if (!tmp)
            {
                throw std::runtime_error("invalid type conversion");
            }
            return tmp;
        }));
    cls.def(py::init(
        []()
        {
            auto tmp = omni::core::createType<omni::particle::system::core2::IParticleBuffer>();
            if (!tmp)
            {
                throw std::runtime_error("unable to create omni::particle::system::core2::IParticleBuffer instantiation");
            }
            return tmp;
        }));
    cls.def_property_readonly("particle_count", &omni::particle::system::core2::IParticleBuffer::getParticleCount);
    cls.def_property_readonly("particle_handle", &omni::particle::system::core2::IParticleBuffer::getParticleHandle);
    cls.def_property("dt", &omni::particle::system::core2::IParticleBuffer::getDt,
                     &omni::particle::system::core2::IParticleBuffer::setDt);
    cls.def_property("current_time", &omni::particle::system::core2::IParticleBuffer::getCurrentTime,
                     &omni::particle::system::core2::IParticleBuffer::setCurrentTime);
    cls.def_property("seed", nullptr, &omni::particle::system::core2::IParticleBuffer::setSeed);
    cls.def_property_readonly("next_random", &omni::particle::system::core2::IParticleBuffer::getNextRandom);
    cls.def_property_readonly("buffer_size", &omni::particle::system::core2::IParticleBuffer::getBufferSize);
    cls.def("check_length", &omni::particle::system::core2::IParticleBuffer::checkLength, py::arg("name"),
            py::arg("expected_count"));
    cls.def("emit_particles", &omni::particle::system::core2::IParticleBuffer::emitParticles, py::arg("count"));
    cls.def("delete_particle", &omni::particle::system::core2::IParticleBuffer::deleteParticle,
            py::arg("deleted_particle"));
    cls.def("shrink_buffer", &omni::particle::system::core2::IParticleBuffer::shrinkBuffer);
    cls.def("get_type", &omni::particle::system::core2::IParticleBuffer::getType, py::arg("name"));
    cls.def("has_attribute", &omni::particle::system::core2::IParticleBuffer::hasAttribute, py::arg("name"));
    cls.def("get_attribute_data", &omni::particle::system::core2::IParticleBuffer::getAttributeData, py::arg("name"));
    cls.def("conform_attribute_lengths", &omni::particle::system::core2::IParticleBuffer::conformAttributeLengths,
            py::arg("maximum_count"));
    cls.def("set_iteration_interval", &omni::particle::system::core2::IParticleBuffer::setIterationInterval,
            py::arg("start"), py::arg("end"));
    cls.def(
        "add_managed_buffer", &omni::particle::system::core2::IParticleBuffer::addManagedBuffer, py::arg("attribute"));
    cls.def("refresh_managed_buffers", &omni::particle::system::core2::IParticleBuffer::refreshManagedBuffers);
    cls.def("apply_to_interval", &omni::particle::system::core2::IParticleBuffer::applyToInterval, py::arg("kernel"),
            py::arg("parallel"));
    cls.def("delete_particles", &omni::particle::system::core2::IParticleBuffer::deleteParticles, py::arg("filter"));
    return omni::python::PyBind<omni::particle::system::core2::IParticleBuffer>::bind(cls);
}

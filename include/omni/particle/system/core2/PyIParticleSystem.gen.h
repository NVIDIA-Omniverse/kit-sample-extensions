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

auto bindIParticleSystem(py::module& m)
{
    // hack around pybind11 issues with C++17
    //   - https://github.com/pybind/pybind11/issues/2234
    //   - https://github.com/pybind/pybind11/issues/2666
    //   - https://github.com/pybind/pybind11/issues/2856
    py::class_<omni::core::Generated<omni::particle::system::core2::IParticleSystem_abi>,
               omni::python::detail::PyObjectPtr<omni::core::Generated<omni::particle::system::core2::IParticleSystem_abi>>,
               omni::core::IObject>
        clsParent(m, "_IParticleSystem");
    py::class_<omni::particle::system::core2::IParticleSystem,
               omni::core::Generated<omni::particle::system::core2::IParticleSystem_abi>,
               omni::python::detail::PyObjectPtr<omni::particle::system::core2::IParticleSystem>, omni::core::IObject>
        cls(m, "IParticleSystem");
    cls.def(py::init(
        [](const omni::core::ObjectPtr<omni::core::IObject>& obj)
        {
            auto tmp = omni::core::cast<omni::particle::system::core2::IParticleSystem>(obj.get());
            if (!tmp)
            {
                throw std::runtime_error("invalid type conversion");
            }
            return tmp;
        }));
    cls.def(py::init(
        []()
        {
            auto tmp = omni::core::createType<omni::particle::system::core2::IParticleSystem>();
            if (!tmp)
            {
                throw std::runtime_error("unable to create omni::particle::system::core2::IParticleSystem instantiation");
            }
            return tmp;
        }));
    cls.def_property_readonly("operator_keys", &omni::particle::system::core2::IParticleSystem::getOperatorKeys);
    return omni::python::PyBind<omni::particle::system::core2::IParticleSystem>::bind(cls);
}

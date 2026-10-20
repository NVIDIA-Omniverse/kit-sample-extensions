// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <carb/BindingsPythonUtils.h>
#include <carb/events/IEvents.h>

#include <omni/curvecreator/ICurveCreator.h>

CARB_BINDINGS("omni.curve.creator.python")

DISABLE_PYBIND11_DYNAMIC_CAST(carb::events::IEventStream)

using namespace carb;
using namespace omni::curvecreator;

namespace
{

PYBIND11_MODULE(_omni_curve_creator, m)
{
    m.doc() = "pybind11 omni.curve.creator bindings";

    m.def(
        "get_interface", []() { return getCachedInterface<ICurveCreator>(); }, py::return_value_policy::reference);

    py::enum_<CurveInterpolateTypes>(m, "CurveInterpolateTypes", R"(
        Curve Interpolate Types.
        )")
        .value("LINEAR", CurveInterpolateTypes::eLinear)
        .value("CUBIC", CurveInterpolateTypes::eCubic);

    defineInterfaceClass<ICurveCreator>(m, "ICurveCreator", "acquire_interface", "release_interface");
}
} // namespace

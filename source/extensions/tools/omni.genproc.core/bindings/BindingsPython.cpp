// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.


#include "../plugins/IGenproc.h"

#include <carb/BindingsPythonUtils.h>
#include <carb/logging/Log.h>

CARB_BINDINGS("omni.genproc.core.python")

namespace
{
PYBIND11_MODULE(_omni_genproc_core, m)
{
    // clang-format off
    using namespace carb;
    using namespace omni::genproc;

    m.doc() = "pybind11 omni.genproc.core bindings";

    defineInterfaceClass<omni::genproc::IGenproc>(m, "IGenproc", "acquire_interface", "release_interface");
}
}

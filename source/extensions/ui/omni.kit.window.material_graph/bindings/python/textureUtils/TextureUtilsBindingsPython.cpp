// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include <carb/BindingsPythonUtils.h>
#include <carb/Framework.h>

#include "TextureUtils.h"

CARB_BINDINGS("omni.kit.window.material_graph.textureUtils.python")

namespace
{
PYBIND11_MODULE(_textureUtils, m)
{
    using namespace carb;
    using namespace omni::kit::materialGraph;

    m.doc() = "TextureUtils bindings.";

    m.def(
        "get_texture_info",
        [](const char* path) {
            // Returns (valid: bool, channel_count: int) for a file path.
            bool valid = false;
            int32_t channels = 0;

            if (auto iface = getFramework()->acquireInterface<TextureUtilsPlugin>())
            {
                // release the GIL to avoid deadlock
                py::gil_scoped_release release;
                iface->get_texture_info(path, &valid, &channels);
            }
            return py::make_tuple(valid, channels);
        },
        py::arg("path"));

    m.def(
        "create_texture_icon",
        [](const char* path, const char* output_path, int32_t size) {
            // Returns True if an icon was written successfully.
            if (auto iface = getFramework()->acquireInterface<TextureUtilsPlugin>())
            {
                // release the GIL to avoid deadlock
                py::gil_scoped_release release;
                return iface->create_texture_icon(path, output_path, size);
            }

            return false;
        },
        py::arg("path"), py::arg("output_path"), py::arg("size"));
}
} // namespace

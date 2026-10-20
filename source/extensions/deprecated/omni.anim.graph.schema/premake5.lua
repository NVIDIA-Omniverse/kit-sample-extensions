-- SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

local ext = get_current_extension_info()
ext.group = "deprecated"

local ext_id = ext.id
ext.id = "omni.anim.graph.schema"
project_ext(ext)
ext.id = ext_id

repo_build.prebuild_link {
    { "docs", ext.target_dir.."/docs" },
    { "data", ext.target_dir.."/data" },
}

repo_build.prebuild_copy {
    { "python/__init__.py", ext.target_dir.."/omni/anim/graph/schema" },
}

local schema = require("tools/schema/premake5")
schema.project(ext, "animGraphSchema", _SCRIPT_DIR)

-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Shared utility functions for premake scripts

local premake_utils = {}

function premake_utils.get_repo_tool_command(args)
    local cmd
    if os.target() == "windows" then
        cmd = "\""..root.."/repo.bat\" "
    else
        cmd = "bash \""..root.."/repo.sh\" "
    end
    cmd = cmd .. args
    return cmd
end

return premake_utils

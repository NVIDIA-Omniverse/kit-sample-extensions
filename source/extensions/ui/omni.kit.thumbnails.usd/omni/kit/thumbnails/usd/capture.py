# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
async def _viewport_capture_bytes(capture_byes_callback: str, aov_name: str = "", usd_context_name: str = ""):
    try:
        from omni.kit.viewport.utility import capture_viewport_to_buffer, get_active_viewport

        capture = capture_viewport_to_buffer(get_active_viewport(), capture_byes_callback)
        return await capture.wait_for_result()
    except ImportError:
        pass


async def _viewport_capture_file(screen_capture_path: str, aov_name: str = "", usd_context_name: str = ""):
    try:
        from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport

        capture = capture_viewport_to_file(get_active_viewport(), screen_capture_path, is_hdr=False)
        return await capture.wait_for_result()
    except ImportError:
        pass

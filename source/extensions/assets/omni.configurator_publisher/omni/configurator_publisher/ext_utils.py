# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.kit.app


def get_enabled_collector_extension_version():
    enabled_version = None
    mgr = omni.kit.app.get_app().get_extension_manager()
    for version in mgr.fetch_extension_versions("omni.kit.usd.collect"):
        if version["enabled"]:
            enabled_version = version["version"]
    if enabled_version is None:
        carb.log_error("Failed to get the target extension version")
        current_version = (0, 0, 0)
    else:
        current_version = enabled_version[:3]

    return current_version

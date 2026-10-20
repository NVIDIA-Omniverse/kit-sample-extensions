# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.kit.ui_test as ui_test


async def expand_advanced_convert_option_frame():
    """Expand the Advanced Options frame in Converter Options GUI window"""
    await ui_test.wait_n_updates(3)

    advanced_frame = ui_test.find("Options Test//Frame/**/CollapsableFrame[*].identifier=='advanced_parameters_frame'")
    await advanced_frame.click()
    await ui_test.wait_n_updates(3)

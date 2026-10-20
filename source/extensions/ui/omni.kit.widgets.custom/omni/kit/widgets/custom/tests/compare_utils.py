# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
"""The utilities for image comparison"""

from pathlib import Path

import carb
import carb.tokens
import omni.kit.test
from omni.kit.test_helpers_gfx.compare_utils import capture_and_compare as _capture_and_compare

OUTPUTS_DIR = Path(omni.kit.test.get_test_output_path())
KIT_ROOT = Path(carb.tokens.get_tokens_interface().resolve("${kit}")).parent.parent.parent
GOLDEN_DIR = KIT_ROOT.joinpath("data/tests/omni.ui.tests")


async def capture_and_compare(image_name: str, threshold, golden_img_dir: Path = None, use_log: bool = True):
    """
    Captures frame and compares it with the golden image.

    Args:
        image_name: the image name of the image and golden image.
        threshold: the max threshold to collect TC artifacts.
        golden_img_dir: the directory path that stores the golden image. Leave it to None to use default dir.

    Returns:
        A value that indicates the maximum difference between pixels. 0 is no difference
        in the range [0-255].
    """

    if not golden_img_dir:
        golden_img_dir = GOLDEN_DIR

    return await _capture_and_compare(image_name, threshold, OUTPUTS_DIR, golden_img_dir, use_log=use_log)

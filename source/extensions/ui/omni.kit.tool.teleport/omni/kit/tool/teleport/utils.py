# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import math
import queue
from pathlib import Path

import carb
import carb.settings
import omni.kit.app
from omni import ui
from omni.ui import color as cl
from pxr import Gf, UsdGeom


def get_icon_path(icon_file):  # pragma: no cover -- currently unused
    path = Path(__file__).parent
    count = 7
    while count > 0:
        if Path.exists(path.joinpath("icons")):
            return path.joinpath(f"icons/{icon_file}").as_posix()
        path = path.parent
        count = count - 1

    carb.log_error(f"Can not find icon path for {__file__}")
    return ""


def get_data_path(data_file):
    path = Path(__file__).parent
    count = 7
    while count > 0:
        if Path.exists(path.joinpath("data")):
            return path.joinpath(f"data/{data_file}").as_posix()
        path = path.parent
        count = count - 1

    carb.log_error(f"Can not find data path for {__file__}")
    return ""

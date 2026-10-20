# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
import omni.services.facilities.base as _facilities


class CarbLogFacility(_facilities.Facility):
    def __init__(self):
        self._functions = {
            "debug": carb.log_verbose,
            "info": carb.log_info,
            "warning": carb.log_warn,
            "error": carb.log_error,
            "exception": carb.log_error,
        }

    def __getattr__(self, name):
        try:
            return self._functions[name]
        except KeyError:
            raise AttributeError(f"{name} is not a valid log level")

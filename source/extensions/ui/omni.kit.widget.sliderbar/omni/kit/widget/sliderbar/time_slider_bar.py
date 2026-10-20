# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from .slider_bar import SliderBar


class TimeSliderBar(SliderBar):
    def _get_display_value(self, value: float) -> str:
        section = " PM"
        if value < 1.0:
            section = " AM"
            hour = 12
        elif value < 12.0:
            hour = int(value)
            section = " AM"
        elif value < 13.0:
            hour = int(value)
        else:
            hour = int(value) - 12

        minute = int((value - int(value)) * 60)
        return "{:2d}:{:02d} {}".format(hour, minute, section)

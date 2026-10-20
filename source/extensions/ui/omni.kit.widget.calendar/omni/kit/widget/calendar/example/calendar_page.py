# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from datetime import datetime

from omni import ui
from omni.kit.widget.calendar import Calendar
from omni.kit.widget.examples import ExamplePage


class CalendarPage(ExamplePage):
    def __init__(self):
        super().__init__("Calendar")

    def destroy(self):
        self._calendar = None

    def build_page(self):
        with ui.VStack(spacing=5):
            ui.Label("Default:", height=20)
            date_time = datetime.now()
            self._calendar = Calendar(date_time)

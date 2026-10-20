# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from datetime import datetime
from typing import Callable

import omni.ui as ui
from omni.kit.widget.calendar import Calendar

from .search_field_popup import SearchFieldPopup


class CalendarPopup(SearchFieldPopup):
    def __init__(
        self, width: int = 400, title: str = "Select a Date", on_day_selected_fn: Callable[[str], None] = None
    ):
        super().__init__(width=width, title=title, popup=True)
        self._day_selected_handler = on_day_selected_fn
        self._build_ui()

    def _build_ui(self):
        # Create and show the window with field and list of tips
        super()._build_ui()

        with self._window.frame:
            with ui.ZStack(height=0, style=self._style):
                ui.Rectangle(style_type_name_override="Background")
                self._calendar = Calendar(datetime.now(), day_selected_handler=self._day_selected_handler)
        self.hide()

    def reset(self):
        if self._calendar:
            self._calendar.set_date(datetime.now())

    def destroy(self):
        super().destroy()
        self._calendar = None

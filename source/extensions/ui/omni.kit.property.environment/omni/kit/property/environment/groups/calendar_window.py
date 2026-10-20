# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import datetime
from typing import Optional

import omni.ui as ui
from omni.kit.environment.core import get_sunstudy_player
from omni.kit.widget.calendar import Calendar

from .style import CALENDAR_STYLE


class CalendarWindow(ui.Window):
    def __init__(self):
        flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_POPUP
        )
        super().__init__("Calendar", flags=flags, width=0, height=0, padding_x=0, padding_y=0)
        self._date = datetime.date(2021, 11, 12)

        self._container = None
        self._calendar = None
        self.frame.set_style(CALENDAR_STYLE)
        self._build_ui()

    def _build_ui(self):

        with self.frame:
            self._container = ui.VStack()
            with self._container:
                ui.Spacer(height=5)
                self._calendar = Calendar(self._date, style=CALENDAR_STYLE, show_combobox=True)
                ui.Spacer(height=5)

        self._last_date = self._calendar.model.as_string
        self._calendar.model.add_value_changed_fn(self._on_calendar_changed)

    @property
    def model(self) -> Optional[ui.AbstractValueModel]:
        if self._calendar is not None:
            return self._calendar.model
        else:
            return None

    @property
    def computed_content_width(self) -> float:
        if self._container is not None:
            return self._container.computed_content_width
        else:
            return 0

    @property
    def computed_content_height(self) -> float:
        if self._container is not None:
            return self._container.computed_content_height
        else:
            return 0

    def _on_calendar_changed(self, model: ui.AbstractValueModel) -> None:
        date = model.as_string
        year, month, day = date.split("-")
        last_year, last_month, last_day = self._last_date.split("-")
        self._last_date = date
        if day != last_day:
            self.visible = False

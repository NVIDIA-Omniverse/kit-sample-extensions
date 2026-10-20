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
import os

import carb
import omni.ext
import omni.ui as ui
from omni.kit.widgets.custom import SimpleListItem, SimpleListModel, SimpleListView, TitleWindowBase


class StringModel(ui.SimpleStringModel):
    def __init__(self, listview):
        super().__init__("")
        self._listview = listview

    def end_edit(self):
        # Get the current string of this model
        fieldString = self.as_string
        if fieldString:
            values = fieldString.split(",")
            self._listview.insert(SimpleListItem(values))


class MultiListWindow(TitleWindowBase):
    def __init__(self):
        super().__init__(
            "Multi columns list view",  # Title & window name
            ui.DockPreference.DISABLED,  # Dock preference
            "",  # Window icon
            400,  # Width
            0,  # Height
            True,  # Resizable
            False,  # If has option button
            True,  # If has help button
            True,  # If has close button
        )

    def _build_content(self):
        with ui.HStack():
            ui.Spacer(width=20)
            with ui.VStack(spacing=10):
                self._model = SimpleListModel(columns_count=2)
                self._listview = SimpleListView(height=500, model=self._model)

                ui.Label("Add to list (using ',' to split columns): ")
                self._field_model = StringModel(self._listview)
                ui.StringField(self._field_model)

                ui.Button("Remove selected", height=26, clicked_fn=self._remove_selected)
                ui.Button("Clear", height=26, clicked_fn=self._clear)

                ui.Spacer(height=30)
            ui.Spacer(width=20)

    def _remove_selected(self):
        self._listview.remove_selected()

    def _clear(self):
        self._listview.clear()

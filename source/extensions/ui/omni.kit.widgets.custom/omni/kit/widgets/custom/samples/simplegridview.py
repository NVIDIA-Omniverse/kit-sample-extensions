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
from omni.kit.widgets.custom import LightColors, SimpleGridView, SimpleListItem, SimpleListModel, TitleWindowBase


class StringModel(ui.SimpleStringModel):
    def __init__(self, gridview):
        super().__init__("")
        self._gridview = gridview

    def end_edit(self):
        # Get the current string of this model
        fieldString = self.as_string
        if fieldString:
            self._gridview.insert_item(SimpleListItem(fieldString))


class SimpleGridDelegate(ui.AbstractItemDelegate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build_widget(self, model, item, *args):
        ui.Label(
            item.get_value_model().as_string,
            width=50,
            alignment=ui.Alignment.CENTER,
            style={"Label": {"color": 0xFFFF0000}, "Label:selected": {"color": LightColors.TextSelected}},
        )


class SimpleGridWindow(TitleWindowBase):
    def __init__(self):
        self._model = SimpleListModel()
        self._model.insert_item(SimpleListItem("This"))
        self._model.insert_item(SimpleListItem("is"))
        self._model.insert_item(SimpleListItem("a"))
        self._model.insert_item(SimpleListItem("gridview"))

        super().__init__(
            "Simple grid view",  # Title & window name
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
                self._gridview = SimpleGridView(
                    height=500, column_count=2, row_height=30, model=self._model, delegate=SimpleGridDelegate()
                )

                with ui.HStack(height=26):
                    ui.Label("Add to grid: ")
                    self._field_model = StringModel(self._gridview)
                    ui.StringField(self._field_model)

                ui.Button("Update Model", height=26, clicked_fn=self._update_model)
                ui.Button("Clear", height=26, clicked_fn=self._clear)

                ui.Spacer(height=30)
            ui.Spacer(width=20)

    def _update_model(self):
        model = SimpleListModel()
        model.insert_item(SimpleListItem("New"))
        model.insert_item(SimpleListItem("Model"))

        self._gridview.model = model

    def _clear(self):
        self._gridview.clear()

# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui
from omni.kit.widgets.custom import CustomWidgetComboBox, LabelDelegate, TitleWindowBase


class StringModel(ui.SimpleStringModel):
    def __init__(self, combobox):
        super().__init__("")
        self._combobox = combobox

    def end_edit(self):
        # Get the current string of this model
        fieldString = self.as_string
        if fieldString:
            self._combobox.insert(fieldString)


class SimpleComboxBoxWindow(TitleWindowBase):
    def __init__(self):
        super().__init__(
            "Combobox view",  # Title & window name
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
                ui.Spacer(height=20)
                self._combobox = CustomWidgetComboBox(
                    -1,
                    "Test",
                    "Widget",
                    "ComboBox",
                    # height=26,
                    item_delegate=LabelDelegate(),
                    alignment=ui.Alignment.CENTER,
                    padding_y=4,
                    padding_x=8,
                )
                with ui.HStack(height=26):
                    ui.Label("Add to combobox: ")
                    self._field_model = StringModel(self._combobox)
                    ui.StringField(self._field_model)
                ui.Button("Remove selected", height=26, clicked_fn=self._remove_selected)
                ui.Button("Clear", height=26, clicked_fn=self._clear)
                ui.Spacer(height=20)
            ui.Spacer(width=20)

    def _remove_selected(self):
        self._combobox.remove_selected()

    def _clear(self):
        self._combobox.clear()

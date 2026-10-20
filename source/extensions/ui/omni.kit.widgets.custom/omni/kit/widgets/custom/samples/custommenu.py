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
from omni.kit.widgets.custom import (
    AbstractWidgetDelegate,
    CustomWidgetMenu,
    CustomWidgetMenuItem,
    FloatSpinner,
    Switch,
    TitleWindowBase,
)


class SpinnerDelegate(AbstractWidgetDelegate):
    def __init__(self, name):
        self._name = name

    def create_widget(self, value, *args, **kwargs):
        spinner_kwargs = kwargs.copy()
        spinner_kwargs["style_type_name_override"] = "MenuItem"
        with ui.HStack():
            ui.Label(self._name, *args, **spinner_kwargs, width=80)
            self._spinner = FloatSpinner(
                self._on_value_changed,
                value=value,
                step=0.01,
                vertical=True,
                width=70,
                height=10,
                min_value=0,
                max_value=100,
                opaque_for_mouse_events=True,
            )

    def set_value(self, value):
        self._spinner.value = value

    def get_value(self):
        return self._spinner.value

    def _on_value_changed(self, value):
        pass


class SwitchDelegate(AbstractWidgetDelegate):
    def __init__(self, name):
        self._name = name

    def create_widget(self, value, *args, **kwargs):
        switch_kwargs = kwargs.copy()
        switch_kwargs["style_type_name_override"] = "MenuItem"
        with ui.HStack():
            ui.Label(self._name, *args, **switch_kwargs, width=80, height=24)

            self._switch = Switch(value, opaque_for_mouse_events=True)

    def set_value(self, value):
        self._switch.status = value

    def get_value(self):
        return self._switch.status


class SimpleCustomMenuWindow(TitleWindowBase):
    def __init__(self):
        super().__init__(
            "Single custom menu view",  # Title & window name
            ui.DockPreference.DISABLED,  # Dock preference
            "",  # Window icon
            400,  # Width
            0,  # Height
            True,  # Resizable
            False,  # If has option button
            True,  # If has help button
            True,  # If has close button
        )
        self._menu = None
        self._center_menu = None
        self._right_menu = None
        self._widgets_menu = None

    def destroy(self):
        super().destroy()
        self._menu = None

    def _build_content(self):
        with ui.VStack(spacing=10):
            ui.Spacer(height=20)
            self._button = ui.Button("Left alignment Custom Menu", height=26, clicked_fn=self._show_menu)
            self._center_button = ui.Button(
                "Center alignment Custom Menu", height=26, clicked_fn=self._show_center_menu
            )
            self._right_button = ui.Button("Right alignment Custom Menu", height=26, clicked_fn=self._show_right_menu)
            self._widget_button = ui.Button("Different widgets Menu", height=26, clicked_fn=self._show_widgets_menu)
            ui.Spacer(height=20)

    def _show_menu(self):
        if self._menu is None:
            self._menu = CustomWidgetMenu(
                ["test", "left", "alignment", "menu"], width=100, on_selection_changed_fn=self._on_selection_changed
            )
        self._menu.show_at(self._button, ui.Alignment.BOTTOM)

    def _show_center_menu(self):
        if self._center_menu is None:
            self._center_menu = CustomWidgetMenu(
                ["test", "center", "alignment", "menu"],
                width=100,
                on_selection_changed_fn=self._on_selection_changed,
                alignment=ui.Alignment.CENTER,
            )
        self._center_menu.show_at(self._center_button, ui.Alignment.BOTTOM)

    def _show_right_menu(self):
        if self._right_menu is None:
            self._right_menu = CustomWidgetMenu(
                ["test", "right", "alignment", "menu"],
                width=100,
                on_selection_changed_fn=self._on_selection_changed,
                alignment=ui.Alignment.RIGHT_CENTER,
            )
        self._right_menu.show_at(self._right_button, ui.Alignment.BOTTOM)

    def _show_widgets_menu(self):
        if self._widgets_menu is None:
            self._delegate = [SpinnerDelegate("spinner"), SwitchDelegate("switch")]
            self._widgets_menu = CustomWidgetMenu(
                [50, True], width=200, on_selection_changed_fn=self._on_selection_changed, delegate=self._delegate
            )
        self._widgets_menu.show_at(self._widget_button, ui.Alignment.BOTTOM)

    def _on_selection_changed(self, index):
        # print(f"selection change to: {index}")
        pass

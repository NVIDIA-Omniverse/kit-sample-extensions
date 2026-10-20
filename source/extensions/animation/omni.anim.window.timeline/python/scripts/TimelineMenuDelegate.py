## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##


import omni.ui as ui

from .utils import SUB_STEPPING_SETTING_MAX, SUB_STEPPING_SETTING_MIN


class TimelineMenuDelegate(ui.MenuDelegate):
    def __init__(self):
        self._delegates = []
        super().__init__()

    def build_item(self, item: ui.MenuItem):
        for delegate in self._delegates:
            if item.text == delegate.name:
                delegate.build_item(item)
                return
        super().build_item(item)

    def add_item_delegate(self, menu_item_delegate):
        self._delegates.append(menu_item_delegate)


class CompensationMenuItemDelegate:
    def __init__(self, name: str, value: float, menu_cb: callable):
        self._value = value
        self._menu_cb = menu_cb
        self._name = name

    def destroy(self):
        self._menu_cb = None

    @property
    def name(self):
        return self._name

    def build_item(self, item: ui.MenuItem):
        with ui.HStack(height=ui.Fraction(1), content_clipping=True):
            ui.Spacer(width=24)
            ui.Label(item.text)
            widget = ui.FloatDrag(
                width=40,
                min=0.0,
                max=100.0,
                step=0.1,
                style={
                    "Slider": {"margin": 2, "padding": 0, "font_size": 12},
                },
            )
            widget.model.set_value(self._value)
            widget.model.add_value_changed_fn(self._value_changed)

    def _value_changed(self, model):
        value = model.get_value_as_float()
        if self._menu_cb:
            self._menu_cb(value)


class SubstepMenuItemDelegate:
    def __init__(self, name: str, value: int, menu_cb: callable):
        self._name = name
        self._value = value
        self._menu_cb = menu_cb

    def destroy(self):
        self._menu_cb = None

    @property
    def name(self):
        return self._name

    def build_item(self, item: ui.MenuItem):
        with ui.HStack(height=ui.Fraction(1), content_clipping=True):
            ui.Spacer(width=24)
            ui.Label(item.text)
            ui.Spacer()
            widget = ui.IntDrag(
                width=20,
                min=SUB_STEPPING_SETTING_MIN,
                max=SUB_STEPPING_SETTING_MAX,
                step=1,
                style={
                    "Slider": {"margin": 0, "padding": 0, "font_size": 12},
                },
            )
            widget.model.set_value(self._value)
            widget.model.add_value_changed_fn(self._value_changed)

    def _value_changed(self, model):
        value = model.get_value_as_int()
        if self._menu_cb:
            self._menu_cb(value)

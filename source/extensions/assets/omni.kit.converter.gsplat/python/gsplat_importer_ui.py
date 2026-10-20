# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""
UI helpers for the asset importer delegate.
"""

from __future__ import annotations

from typing import List

from omni import ui

__all__ = ["MinimalItem", "MinimalModal", "CustomProgressModel", "ProgressPopup"]


class MinimalItem(ui.AbstractItem):
    """Helper for :class:`MinimalModal` — one row in a combo item model."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.model = ui.SimpleStringModel(text)


class MinimalModal(ui.AbstractItemModel):
    """Indexed string labels for :class:`omni.ui.ComboBox`."""

    def __init__(self, default_index: int, item_labels: list[str]) -> None:
        super().__init__()
        self._default_index = default_index
        self._current_index = ui.SimpleIntModel(default_index)
        self._current_index.add_value_changed_fn(lambda _: self._item_changed(None))
        self._items = [MinimalItem(label) for label in item_labels]

    @property
    def current_index(self) -> int:
        return self._current_index.as_int

    def get_item_children(self, _: ui.AbstractItem | None = None) -> List[ui.AbstractItem]:
        return self._items

    def get_item_value_model(self, item: MinimalItem, _):
        if item is None:
            return self._current_index
        return item.model


class CustomProgressModel(ui.AbstractValueModel):
    def __init__(self) -> None:
        super().__init__()
        self._value = 0.0

    def set_value(self, value):
        try:
            value = float(value)
        except ValueError:
            value = None
        if value != self._value:
            self._value = value
            self._value_changed()

    def get_value_as_float(self):
        return self._value

    def get_value_as_string(self):
        return str(int(self._value * 100)) + "%"


class ProgressPopup:
    """Modal window with status label, progress bar, and optional cancel."""

    def __init__(self, title, cancel_button_text="CANCEL", cancel_button_fn=None, status_text="", modal=True):
        self._status_text = status_text
        self._title = title
        self._cancel_button_text = cancel_button_text
        self._cancel_button_fn = cancel_button_fn
        self._cancel_button = None
        self._modal = modal
        self._build_ui()

    def destroy(self):
        if self._cancel_button:
            self._cancel_button.set_clicked_fn(None)
            self._cancel_button = None
        if self._popup:
            self._popup.destroy()
            self._popup = None
        self._status_label = None
        self._progress_bar = None
        self._progress_bar_model = None

    def __enter__(self):
        self._popup.visible = True
        return self

    def __exit__(self, type, value, trace):
        self._popup.visible = False

    def set_cancel_fn(self, on_cancel_button_clicked):
        self._cancel_button_fn = on_cancel_button_clicked

    def set_progress(self, progress):
        self._progress_bar.model.set_value(progress)

    def get_progress(self):
        return self._progress_bar.model.get_value_as_float()

    progress = property(get_progress, set_progress)

    def set_status_text(self, status_text):
        self._status_label.text = status_text

    def get_status_text(self):
        return self._status_label.text

    status_text = property(get_status_text, set_status_text)

    def show(self):
        self._popup.visible = True

    def hide(self):
        self._popup.visible = False

    def is_visible(self):
        return self._popup.visible

    def _on_cancel_button_fn(self):
        self.hide()
        if self._cancel_button_fn:
            self._cancel_button_fn()

    def _build_ui(self):
        self._popup = ui.Window(self._title, visible=False, height=0, dockPreference=ui.DockPreference.DISABLED)
        self._popup.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_MOVE
        )

        if self._modal:
            self._popup.flags = self._popup.flags | ui.WINDOW_FLAGS_MODAL

        with self._popup.frame:
            with ui.VStack(height=0):
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._status_label = ui.Label(self._status_text, width=0, height=0)
                    ui.Spacer()
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._progress_bar_model = CustomProgressModel()
                    self._progress_bar = ui.ProgressBar(
                        self._progress_bar_model, width=300, style={"color": 0xFFFF9E3D}
                    )
                    ui.Spacer()
                ui.Spacer(height=5)
                with ui.HStack(height=0):
                    ui.Spacer(height=0)
                    self._cancel_button = ui.Button(self._cancel_button_text, width=80, height=0)
                    self._cancel_button.set_clicked_fn(self._on_cancel_button_fn)
                    ui.Spacer(height=0)
                ui.Spacer(width=0, height=10)

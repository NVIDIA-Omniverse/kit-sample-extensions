# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import List

import carb
import carb.settings
import omni.ui as ui


class Prompt:
    def __init__(
        self, title: str, text: str, button_text: list, button_fn: list, modal: bool = False, callback_addons: List = []
    ):
        self._title = title
        self._text = text
        self._button_list = []
        self._modal = modal
        self._callback_addons = callback_addons
        self._buttons = []
        for name, fn in zip(button_text, button_fn):
            self._button_list.append((name, fn))

        self._build_ui()

    def destroy(self):
        self._cancel_button_fn = None
        self._ok_button_fn = None
        self._button_list = []
        if self._window:
            self._window.destroy()
            del self._window
        self._window = None

        for button in self._buttons:
            button.set_clicked_fn(None)
        self._buttons.clear()

        self._callback_addons = []

    def __del__(self):
        self.destroy()

    def __enter__(self):
        self.show()

        if self._modal:
            settings = carb.settings.get_settings()
            # Only use first word as a reason (e.g. "Creating, Openning"). URL won't work as a setting key.
            operation = self._text.split(" ")[0].lower()
            self._hang_detector_disable_key = "/app/hangDetector/disableReasons/{0}".format(operation)
            settings.set(self._hang_detector_disable_key, "1")
            settings.set("/crashreporter/data/appState", operation)

        return self

    def __exit__(self, type, value, trace):
        self.hide()

        if self._modal:
            settings = carb.settings.get_settings()
            settings.destroy_item(self._hang_detector_disable_key)
            settings.set("/crashreporter/data/appState", "started")

    def show(self):
        self._window.visible = True

    def hide(self):
        self._window.visible = False

    def is_visible(self):
        return self._window.visible

    def set_text(self, text):
        self._text_label.text = text

    def _build_ui(self):
        self._window = ui.Window(self._title, visible=False, height=0, dockPreference=ui.DockPreference.DISABLED)
        self._window.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_MOVE
            | ui.WINDOW_FLAGS_NO_CLOSE
        )

        if self._modal:
            self._window.flags |= ui.WINDOW_FLAGS_MODAL

        with self._window.frame:
            with ui.VStack(height=0):
                ui.Spacer(width=0, height=10)
                with ui.HStack(height=0):
                    ui.Spacer(widht=10, height=0)
                    self._text_label = ui.Label(
                        self._text,
                        width=ui.Percent(100),
                        height=0,
                        word_wrap=True,
                        alignment=ui.Alignment.CENTER,
                    )
                    ui.Spacer(widht=10, height=0)
                ui.Spacer(width=0, height=10)
                with ui.HStack(height=0):
                    ui.Spacer(height=0)
                    for name, fn in self._button_list:
                        if name:
                            button = ui.Button(name)
                            if fn:
                                button.set_clicked_fn(lambda on_fn=fn: (self.hide(), on_fn()))
                            else:
                                button.set_clicked_fn(lambda: self.hide())
                            self._buttons.append(button)
                    ui.Spacer(height=0)
                ui.Spacer(width=0, height=10)

                for callback in self._callback_addons:
                    if callback and callable(callback):
                        callback()

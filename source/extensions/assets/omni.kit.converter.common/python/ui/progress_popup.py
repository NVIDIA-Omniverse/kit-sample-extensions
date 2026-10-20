# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import typing

import omni.ui as ui

__all__ = ["ProgressDialog"]


class ProgressDialog:
    """
    Progress popup class with step and progress info.
    """

    def __init__(self, title: str = "CAD Converter Progress"):
        """Constructor..creates the popup window"""
        self._window = ui.Window(
            title,
            width=550,
            height=150,
            visible=False,
            flags=ui.WINDOW_FLAGS_MODAL
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_CLOSE,
        )
        self._window.frame.set_build_fn(self._build_ui)
        self._cancel_fn: typing.Optional[typing.Callable] = None
        self._step_label_string = "Extracting input file"
        self._step_label = None
        self._progress_label = None
        self._progress_bar = None
        self._cancel_btn = None

    @property
    def window(self):
        return self._window

    def __del__(self):
        """Destructor"""
        self.destroy()

    def clear(self):
        """
        Clear labels and progress bar
        """
        if self._progress_bar.model:
            self._progress_bar.model.set_value(0)
        if self._progress_label:
            self._progress_label.text = ""
        if self._step_label:
            self._step_label.text = ""

    def show(self, step_label: str = ""):
        """Shows the popup"""
        if self._step_label:
            self._step_label.text = step_label
        else:
            self._step_label_string = step_label
        self._window.visible = True

    def hide(self):
        """Hides the popup"""
        self._window.visible = False

    def destroy(self):
        """Destroys the popup"""
        self._window = None
        self._progress_label = None
        self._progress_bar = None
        self._step_label = None

    def _build_ui(self):
        """Build UI for the popup"""
        with self._window.frame:
            with ui.VStack(spacing=10):
                self._step_label = ui.Label(self._step_label_string, alignment=ui.Alignment.CENTER, word_wrap=True)
                self._progress_label = ui.Label("Please wait...", alignment=ui.Alignment.CENTER, elided_text=True)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._progress_bar = ui.ProgressBar(height=22, style={"color": 0xFFFF9E3D}, width=300)
                    ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer()
                    ui.Button("Cancel", clicked_fn=self._on_cancel, identifier="cancel_btn")
                    ui.Spacer()

    def set_progress_info(self, progress_text, progress_value):
        """Updates progress label and progress bar"""
        if self._progress_label:
            self._progress_label.text = progress_text
            self._progress_bar.model.set_value(progress_value)

    def set_step_info(self, title: str):
        """Updates step label"""
        if self._step_label:
            self._step_label.text = title

    def _on_cancel(self):
        if self._cancel_fn:
            self._cancel_fn()
        self._window.visible = False

    def set_cancel_fn(self, cb):
        """Sets cancel clicked callback function"""
        self._cancel_fn = cb

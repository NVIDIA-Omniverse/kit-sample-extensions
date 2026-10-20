# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import carb.settings
import omni.ui


class Prompt:
    """
    A window to prompt information.
    Comes from omni.kit.window.file.
    """

    def __init__(
        self,
        title: str,
        text: str,
        ok_button_text: str = "OK",
        cancel_button_text: str = None,
        ok_button_fn: callable = None,
        cancel_button_fn: callable = None,
        modal: bool = False,
    ):
        self._title = title
        self._text = text
        self._button_list = [(ok_button_text, ok_button_fn), (cancel_button_text, cancel_button_fn)]
        self._modal = modal
        self._build_ui()

    def __init__(self, title: str, text: str, button_text: list, button_fn: list, modal: bool = False):
        self._title = title
        self._text = text
        self._button_list = []
        self._modal = modal
        for name, fn in zip(button_text, button_fn):
            self._button_list.append((name, fn))

        self._build_ui()

    def destroy(self):
        self._cancel_button_fn = None
        self._ok_button_fn = None
        self._button_list = []
        if self._window:
            del self._window
        self._window = None

    def __del__(self):
        self.destroy()

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, type, value, trace):
        self.hide()

    def show(self):
        self._window.visible = True

    def hide(self):
        self._window.visible = False

    def is_visible(self):
        return self._window.visible

    def set_text(self, text):
        self._text_label.text = text

    def _build_ui(self):
        self._window = omni.ui.Window(
            self._title, visible=False, height=0, dockPreference=omni.ui.DockPreference.DISABLED
        )
        self._window.flags = (
            omni.ui.WINDOW_FLAGS_NO_COLLAPSE
            | omni.ui.WINDOW_FLAGS_NO_RESIZE
            | omni.ui.WINDOW_FLAGS_NO_SCROLLBAR
            | omni.ui.WINDOW_FLAGS_NO_RESIZE
            | omni.ui.WINDOW_FLAGS_NO_MOVE
            | omni.ui.WINDOW_FLAGS_NO_CLOSE
        )

        if self._modal:
            self._window.flags |= omni.ui.WINDOW_FLAGS_MODAL

        with self._window.frame:
            with omni.ui.VStack(height=0):
                omni.ui.Spacer(width=0, height=10)
                with omni.ui.HStack(height=0):
                    omni.ui.Spacer(widht=10, height=0)
                    self._text_label = omni.ui.Label(
                        self._text,
                        width=omni.ui.Percent(100),
                        height=0,
                        word_wrap=True,
                        alignment=omni.ui.Alignment.CENTER,
                    )
                    omni.ui.Spacer(widht=10, height=0)
                omni.ui.Spacer(width=0, height=10)
                with omni.ui.HStack(height=0):
                    omni.ui.Spacer(height=0)
                    for name, fn in self._button_list:
                        if name:
                            button = omni.ui.Button(name)
                            if fn:
                                button.set_clicked_fn(lambda on_fn=fn: (self.hide(), on_fn()))
                            else:
                                button.set_clicked_fn(lambda: self.hide())
                    omni.ui.Spacer(height=0)
                omni.ui.Spacer(width=0, height=10)

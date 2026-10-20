# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui


class SearchWordButton:
    """
    Represents a search word widget, combined with a label to show the word and a close button to remove it.
    Args:
        word (str): String of word.
    Keyword args:
        on_close_fn (callable): Function called when close button clicked. Function signure:
            void on_close_fn(widget: SearchWordButton)
    """

    def __init__(self, word: str, on_close_fn: callable = None, on_dbl_click: callable = None, supported: bool = True):
        self._supported = supported
        style = "ExtendedSearchField.Word" if supported else "ExtendedSearchField.Word.Unsupported"
        self._on_close_fn = on_close_fn
        self._container = ui.ZStack(width=0)
        with self._container:
            with ui.VStack():
                ui.Spacer(height=5)
                ui.Rectangle(style_type_name_override=style)
                ui.Spacer(height=5)
            with ui.HStack():
                ui.Spacer(width=3)
                label = ui.Label(
                    word,
                    width=0,
                    style_type_name_override=f"{style}.Label",
                    tooltip="Unsupported prefix" if not supported else "",
                )
                label.set_mouse_double_clicked_fn(on_dbl_click)
                ui.Spacer(width=3)
                ui.Button(
                    image_width=8,
                    style_type_name_override=f"{style}.Button",
                    clicked_fn=lambda: on_close_fn(self) if on_close_fn is not None else None,
                )

    def __del__(self):
        self.destroy()

    def is_supported(self) -> bool:
        return self._supported

    def destroy(self):
        self._on_close_fn = None

    def close(self):
        if self._on_close_fn:
            self._on_close_fn(self)

    @property
    def visible(self) -> None:
        """
        Widget visibility
        """
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._container.visible = value

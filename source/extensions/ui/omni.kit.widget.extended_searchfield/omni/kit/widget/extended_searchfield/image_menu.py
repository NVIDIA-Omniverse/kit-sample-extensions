# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Callable

import carb
import omni.ui as ui

from .browser_delegate import BrowserDelegate
from .path_field import FolderPathField, ImagePathField
from .search_field_popup import AbstractDialog, SearchFieldPopup


class ImageMenu(SearchFieldPopup):

    @staticmethod
    def validate_prefixes(prefixes: list) -> bool:
        return "image" in prefixes

    """The ImageMenu is a popup dialog that is a drag target for an image.
    Alternatively an image can be selected with a file picker.
    The selected image will be displayed along with a thumbnail.
    """

    def __init__(
        self,
        popup: bool = False,
        width: int = 400,
        browser_delegate: BrowserDelegate = None,
        title: str = "Image Dialog",
        ok_handler: Callable[[AbstractDialog, str], None] = None,
        cancel_handler: Callable[[AbstractDialog], None] = None,
        ok_label: str = "Search by Image",
        cancel_label: str = "Close",
    ):
        super().__init__(
            popup=popup,
            width=width,
            title=title,
            ok_handler=lambda d: self._ok_wrapper(d, ok_handler),
            cancel_handler=lambda d: self._cancel_wrapper(d, cancel_handler),
            ok_label=ok_label,
            cancel_label=cancel_label,
            alternate_search_text="Drag and Drop Image Here",
            button_style="ImageMenu.Button",
        )

        self._browser_delegate = browser_delegate
        self._build_ui()

    def clear(self):
        self._image_path_field.model.set_value("")

    def _ok_wrapper(self, dialog: AbstractDialog, ok_handler: Callable[[AbstractDialog, str], None] = None):
        if ok_handler:
            ok_handler(dialog, self._image_path_field.model.get_value_as_string())

    def _cancel_wrapper(self, dialog: AbstractDialog, cancel_handler: Callable[[AbstractDialog], None] = None):
        self.hide()
        if cancel_handler:
            cancel_handler(dialog)

    def _path_selected(self, path_field: FolderPathField):
        path = path_field.model.get_value_as_string()
        if path and self._browser_delegate:
            self._browser_delegate.current_directory = path
        asyncio.ensure_future(self.reset_position())

    def _build_ui(self):
        # Create and show the window with field and list of tips
        super()._build_ui()

        with self._window.frame:
            with ui.ZStack(height=0, style=self._style):
                ui.Rectangle(style_type_name_override="Background")
                with ui.VStack():
                    ui.Spacer(height=5)
                    self._image_path_field = ImagePathField(
                        "image",
                        ok_handler=lambda _: asyncio.ensure_future(self.reset_position()),
                        cancel_handler=lambda: asyncio.ensure_future(self.reset_position()),
                    )
                    ui.Spacer(height=5)

                    path = None
                    if self._browser_delegate:
                        path = self._browser_delegate.current_directory

                    if path is None:
                        self._path_field = None
                    else:
                        with ui.HStack():
                            ui.Spacer(width=10)
                            ui.Label("Search Path", width=0)
                            ui.Spacer(width=10)
                            self._path_field = FolderPathField(
                                name="path",
                                hint="",
                                ok_handler=self._path_selected,
                                cancel_handler=lambda: asyncio.ensure_future(self.reset_position()),
                            )
                            self._path_field._model.set_value(path)
                            ui.Spacer(width=4)
                    ui.Spacer(height=4)
                    with ui.HStack():
                        ui.Spacer(width=100)
                        super()._build_ok_cancel_buttons()
                    ui.Spacer(height=5)
        self.hide()

    def show(self, **kwargs):
        super().show(**kwargs)
        if self._browser_delegate:
            path = self._browser_delegate.current_directory
            if self._path_field and path:
                self._path_field._model.set_value(path)

    def destroy(self):
        super().destroy()
        self._path_field = None
        self._image_path_field = None

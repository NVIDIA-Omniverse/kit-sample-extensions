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
import traceback

import carb
import omni

from .filebrowser import FileBrowserMode
from .filebrowser.app_filebrowser import FileBrowserUI
from .prompt import Prompt


class FilePicker:
    def __init__(self, title, mode, file_type, filter_options):
        self._mode = mode
        self._ui_handler = None
        self._app = omni.kit.app.get_app()
        self._open_handler = None
        self._cancel_handler = None

        try:
            self._ui_handler = FileBrowserUI(title, mode, file_type, filter_options)
            carb.log_info(f"{self.__class__} using new FileBrowserUI")
        except Exception as e:  # pragma: no cover
            carb.log_warn(f"{self.__class__} failed to initalized new FileBrowserUI: {e}")

        if not self._ui_handler:  # pragma: no cover
            carb.log_warn(
                f"{self.__class__} neither old or new FileBrowserUI could be initalized. UI will not be avaliable"
            )

        self._prompt = None

    def _show_prompt(self, file_path, file_save_handler):
        if not self._prompt:
            self._prompt = Prompt(
                f'{omni.ui.get_custom_glyph_code("${glyphs}/exclamation.svg")} Overwrite', "", "OK", "Cancel"
            )
        self._prompt.set_text(f"File {os.path.basename(file_path)} already exists, do you want to overwrite it?")
        if file_save_handler:
            self._prompt.set_confirm_fn(lambda: file_save_handler(file_path))
        self._prompt.show()

    def _save_and_prompt_if_exists(self, file_path, file_save_handler=None):
        result, entry = omni.client.stat(file_path)
        if result == omni.client.Result.OK:
            self._show_prompt(file_path, file_save_handler)
        elif file_save_handler:
            file_save_handler(file_path)

    def _on_file_open(self, path):
        if self._mode == FileBrowserMode.SAVE:
            self._save_and_prompt_if_exists(path, self._open_handler)
        elif self._open_handler:
            self._open_handler(path)

    def _on_cancel_open(self):
        if self._cancel_handler:
            self._cancel_handler()

    def set_file_selected_fn(self, file_open_handler):
        self._open_handler = file_open_handler

    def set_cancel_fn(self, cancel_handler):
        self._cancel_handler = cancel_handler

    def show(self, dir=None, filename=None, show_local=False):
        if self._ui_handler:
            if dir:
                self._ui_handler.set_current_directory(dir)

            if filename:
                self._ui_handler.set_current_filename(filename)
            self._ui_handler.open(self._on_file_open, self._on_cancel_open, show_local)

    def set_current_directory(self, dir):
        if self._ui_handler:
            self._ui_handler.set_current_directory(dir)

    def set_current_filename(self, filename):
        if self._ui_handler:
            self._ui_handler.set_current_filename(filename)

    def destroy(self):
        if self._ui_handler:
            self._ui_handler.destroy()
        self._ui_handler = None

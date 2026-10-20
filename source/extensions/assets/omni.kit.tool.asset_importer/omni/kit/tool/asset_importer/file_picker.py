__all__ = ["FilePicker"]

import asyncio
import os
import traceback
from typing import Callable, List, Tuple

import carb
import omni
import omni.client
from omni.kit.widget.filebrowser import FileBrowserItem
from omni.kit.widget.prompt import PromptButtonInfo, PromptManager

from .filebrowser import FileBrowserMode, FileBrowserSelectionType
from .filebrowser.app_filebrowser import FileBrowserUI


class FilePicker:
    def __init__(
        self,
        title: str,
        mode: FileBrowserMode,
        file_type: FileBrowserSelectionType,
        filter_options: List[Tuple[str, str]],
        save_extensions: List[str] = [],
        apply_button_name: str = "",
        allow_multi_selections=False,
        import_to_stage=False,
        options_pane_build_fn: Callable[[List[str]], bool] = None,
        on_selection_changed: Callable[[List[str]], bool] = None,
    ):
        self._mode = mode
        self._app = omni.kit.app.get_app()
        self._open_handler = None
        self._cancel_handler = None
        self._allow_multi_selections = allow_multi_selections
        self._import_to_stage = import_to_stage
        self._options_pane_build_fn = options_pane_build_fn
        self._on_selection_changed = on_selection_changed
        if self._options_pane_build_fn:
            build_fn = self._build_options_pane
        else:
            build_fn = None

        if self._on_selection_changed:
            selection_fn = self._selection_changed
        else:
            selection_fn = None

        self._ui_handler = FileBrowserUI(
            title=title,
            apply_button_name=apply_button_name,
            mode=mode,
            selection_type=file_type,
            filter_options=filter_options,
            save_extensions=save_extensions,
            allow_multi_selection=self._allow_multi_selections,
            build_options_pane_fn=build_fn,
            on_selection_changed=selection_fn,
        )

    def _selection_changed(self, paths: List[FileBrowserItem]):
        to_convert_paths = []
        for path_item in paths:
            if isinstance(path_item, FileBrowserItem):
                if path_item.is_folder:
                    continue

                to_convert_paths.append(path_item.path)
            else:
                to_convert_paths.append(path_item)

        if self._on_selection_changed:
            self._on_selection_changed(to_convert_paths)

    def _build_options_pane(self, paths: List[FileBrowserItem]):
        to_convert_paths = []
        for path_item in paths:
            if isinstance(path_item, FileBrowserItem):
                if path_item.is_folder:
                    continue

                to_convert_paths.append(path_item.path)
            else:
                to_convert_paths.append(path_item)

        if self._options_pane_build_fn:
            return self._options_pane_build_fn(to_convert_paths, self._import_to_stage)
        else:
            return False

    def _save_and_prompt_if_exists(self, file_path: str, file_save_handler: Callable[[str], None] = None):
        result, _ = omni.client.stat(file_path)
        existed = result == omni.client.Result.OK
        if existed:
            PromptManager.post_simple_prompt(
                f'{omni.kit.ui.get_custom_glyph_code("${glyphs}/exclamation.svg")} Overwrite',
                f"File {os.path.basename(file_path)} already exists, do you want to overwrite it?",
                PromptButtonInfo("CONFIRM", lambda: file_save_handler(file_path)),
                PromptButtonInfo("CANCEL"),
            )
        elif file_save_handler:
            file_save_handler(file_path)

    def _on_file_open(self, paths: List[str]):
        if self._open_handler:
            self._open_handler(paths)

    def _on_cancel_open(self):
        if self._cancel_handler:
            self._cancel_handler()

    def set_file_selected_fn(self, file_open_handler: Callable[[List[str]], None]):
        self._open_handler = file_open_handler

    def set_cancel_fn(self, cancel_handler: Callable[[], None]):
        self._cancel_handler = cancel_handler

    def show(self, dir: str = None, filename: str = None):
        if self._ui_handler:
            if dir:
                self._ui_handler.set_current_directory(dir)

            if filename:
                self._ui_handler.set_current_filename(filename)
            self._ui_handler.open(self._on_file_open, self._on_cancel_open)

    def set_current_directory(self, dir: str):
        if self._ui_handler:
            self._ui_handler.set_current_directory(dir)

    def set_current_filename(self, filename: str):
        if self._ui_handler:
            self._ui_handler.set_current_filename(filename)

    def destroy(self):
        self._options_pane_build_fn = None
        self._on_selection_changed = None
        self._open_handler = None
        self._cancel_handler = None
        if self._ui_handler:
            self._ui_handler.destroy()
        self._ui_handler = None

# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
from typing import Callable

import omni.ui as ui
from omni.kit.window.filepicker import FilePickerDialog

from .named_field import NamedField
from .style import ICON_PATH
from .utils import IMAGE_TYPES, is_omniverse_url


class AbstractPathField(NamedField):
    """Create an input field for a path. This will be a stringfield and a button
    that opens a filepicker dialog.
    """

    def __init__(
        self,
        name: str,
        hint: str = "",
        valid_types: list = ["All Files (*)"],
        dialog_prompt: str = "Select File..",
        ok_handler: Callable[[NamedField], None] = None,
        cancel_handler: Callable = None,
    ):
        """Init for PathField which also builds the UI.

        Args:
            name (str): The name of the field.
            hint (str, optional): The hint displayed over the search field.
            valid_types (list, optional): The valid types when searching for the path in the file picker.
            dialog_prompt (str, optional): The file picker dialog prompt.
            ok_handler (Callable[[NamedField], None], optional): The handler to call when a value is selected.
        """
        self._valid_types: list = valid_types
        self._dialog_prompt: str = dialog_prompt
        self._ok_handler: Callable[[NamedField], None] = ok_handler
        self._cancel_handler: Callable = cancel_handler
        super().__init__(name, hint)

    def destroy(self):
        super().destroy()
        self._ok_handler = None
        self._cancel_handler = None

    def _on_filter_item(self, item) -> bool:
        """The filter function for FilePickerDialog. Must be implemented by subclass.

        Args:
            item (FileDialogItem): The item to filter.

        Returns:
            bool: Return True for selectable items.
        """
        raise NotImplementedError

    def _on_file_pick(self, dialog, filename, dirname):
        path = ""
        if dirname:
            # pathlib Path will mangle omniverse urls, and os.path will mix / and \
            path = f"{dirname}{filename}" if dirname[-1] == "/" else f"{dirname}/{filename}"
        elif filename:
            path = filename
        self._model.set_value(path)
        dialog.hide()
        if self._ok_handler:
            self._ok_handler(self)

    def _cancel_wrapper(self, dialog: FilePickerDialog):
        dialog.hide()
        if self._cancel_handler:
            self._cancel_handler()

    def _on_show_dialog(self):
        dialog = FilePickerDialog(
            self._dialog_prompt,
            apply_button_label="Select",
            click_apply_handler=lambda filename, dirname: self._on_file_pick(dialog, filename, dirname),
            click_cancel_handler=lambda *_: self._cancel_wrapper(dialog),
            item_filter_options=self._valid_types,
            item_filter_fn=lambda item: self._on_filter_item(item),
        )
        dialog.show()

    def _build_ui(self):
        raise NotImplementedError


class ImagePathField(AbstractPathField):
    """This version of the path field picks image files only."""

    def __init__(
        self,
        name: str,
        hint: str = "",
        ok_handler: Callable[[NamedField], None] = None,
        cancel_handler: Callable = None,
    ):
        super().__init__(
            name,
            hint,
            valid_types=["Image Files"] + IMAGE_TYPES,
            dialog_prompt="Select Image..",
            ok_handler=lambda f: self._ok_wrapper(ok_handler, f),
            cancel_handler=cancel_handler,
        )

    def _ok_wrapper(self, ok_handler: Callable[[NamedField], None], field: NamedField):
        result = self._model.get_value_as_string().rstrip("/")
        self._model.set_value(result)

        if is_omniverse_url(result):
            self._image_path_button.text = os.path.basename(result)
            self._image_path_button.visible = True
        else:
            self._image.source_url = result
            self._image_block.visible = True
        self._image_selection_button.visible = False

        ok_handler(field)

    def _clear(self):
        self._model.set_value("")
        self._image.source_url = ""
        self._image_block.visible = False
        self._image_selection_button.text = self._button_text
        self._image_selection_button.visible = True
        self._image_path_button.visible = False

    def _on_filter_item(self, item) -> bool:
        if not item or item.is_folder:
            return True
        return os.path.splitext(item.path)[1].lower() in IMAGE_TYPES

    def _build_ui(self):
        with ui.HStack():
            ui.Spacer(width=5)
            self._model = ui.SimpleStringModel()
            with ui.ZStack():
                self._button_text = (
                    "Drag and drop an image on the search field above,\n\r" "or click to select an image."
                )
                self._image_selection_button = ui.Button(
                    self._button_text,
                    style_type_name_override="ImageMenu.ImageButton",
                    clicked_fn=self._on_show_dialog,
                    height=60,
                )

                self._image_path_button = ui.Button(
                    " ",
                    style_type_name_override="ImageMenu.ImageButton",
                    alignment=ui.Alignment.CENTER,
                    clicked_fn=self._clear,
                    height=60,
                )
                self._image_path_button.visible = False

                self._image_block = ui.HStack()
                with self._image_block:
                    ui.Spacer()
                    with ui.VStack(width=100):
                        ui.Spacer(height=5)
                        with ui.ZStack():
                            self._image = ui.Image(style_type_name_override="ImageMenu.Image", height=55)
                            with ui.VStack():
                                with ui.HStack():
                                    ui.Spacer()
                                    ui.Button(
                                        image_url=f"{ICON_PATH}/close.svg", width=20, height=20, clicked_fn=self._clear
                                    )
                                ui.Spacer()
                        ui.Spacer()
                    ui.Spacer()
                self._image_block.visible = False
            ui.Spacer(width=5)


class FolderPathField(AbstractPathField):
    """This version of the path field picks folders only."""

    def __init__(
        self,
        name: str,
        hint: str = "",
        ok_handler: Callable[[NamedField], None] = None,
        cancel_handler: Callable = None,
    ):
        super().__init__(
            name,
            hint,
            valid_types=["Folders"],
            dialog_prompt="Select Folder..",
            ok_handler=lambda f: self._ok_wrapper(ok_handler, f),
            cancel_handler=cancel_handler,
        )

    def _ok_wrapper(self, ok_handler: Callable[[NamedField], None], field: NamedField):
        result = self._model.get_value_as_string().rstrip("/")
        self._model.set_value(result)
        ok_handler(field)

    def _on_filter_item(self, item) -> bool:
        return not item or item.is_folder

    def _build_ui(self):
        self._container = ui.HStack()
        with self._container:
            with ui.ZStack():
                with ui.HStack():
                    self._string_field = ui.StringField(style_type_name_override="ImagePathField")
                    self._model = self._string_field.model
                    self._sub_begin_edit = self._model.subscribe_begin_edit_fn(self._on_begin_edit)
                    self._sub_end_edit = self._model.subscribe_end_edit_fn(self._on_end_edit)

                    # Only allow entering a path with the button, not the string_field
                    self._string_field.enabled = False

                    ui.Spacer(width=4)
                    with ui.VStack(width=20):
                        self._filter_button = ui.Button(
                            image_url=f"{ICON_PATH}/folder.svg",
                            image_width=14,
                            height=18,
                            style_type_name_override="Separate.Button",
                            name="folder",
                            tooltip=self._dialog_prompt,
                            clicked_fn=self._on_show_dialog,
                        )
                    ui.Spacer(width=4)
                self._hint_container = ui.HStack(spacing=5)
                with self._hint_container:
                    ui.Spacer(width=10)
                    ui.Label(self._hint, style_type_name_override="ExtendedSearchField.Hint")

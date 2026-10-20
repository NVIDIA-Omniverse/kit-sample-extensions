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
from typing import Callable, List

import omni.ui as ui

from ....search_grammar import GrammarPrefix
from .calendar_field import CalendarController
from .named_field import NamedField
from .search_field_popup import AbstractDialog, SearchFieldPopup
from .utils import quotify, split_with_quotes


class SearchMenu(SearchFieldPopup):
    """Popup dialog that displays detailed search options for extended search.

    Opening the dialog will populate the fields with a string.
    Clicking search will return the new string.
    """

    H_SPACING = 5
    LABEL_COLUMN_WIDTH = 75
    SUPPORTED_PREFIXES: List[str] = [
        GrammarPrefix.CREATED_BY,
        GrammarPrefix.MODIFIED_BY,
        GrammarPrefix.NAME,
        GrammarPrefix.TAG,
        GrammarPrefix.EXT,
        GrammarPrefix.LARGER_THAN,
        GrammarPrefix.SMALLER_THAN,
        GrammarPrefix.CREATED_BEFORE,
        GrammarPrefix.CREATED_AFTER,
        GrammarPrefix.MODIFIED_BEFORE,
        GrammarPrefix.MODIFIED_AFTER,
        GrammarPrefix.DESCRIPTION,
    ]
    AUTO_GROUPED_PREFIXES: List[str] = [
        GrammarPrefix.DESCRIPTION,
        GrammarPrefix.LARGER_THAN,
        GrammarPrefix.SMALLER_THAN,
    ]
    SINGLE_VALUE_PREFIXES: List[str] = [
        GrammarPrefix.CREATED_BEFORE,
        GrammarPrefix.CREATED_AFTER,
        GrammarPrefix.LARGER_THAN,
        GrammarPrefix.SMALLER_THAN,
    ]
    AUTO_OR_PREFIXES: List[str] = [GrammarPrefix.EXT, GrammarPrefix.MODIFIED_BY, GrammarPrefix.CREATED_BY]

    @staticmethod
    def validate_prefixes(prefixes: list) -> bool:
        for p in prefixes:
            if p in SearchMenu.SUPPORTED_PREFIXES:
                return True
        return False

    def __init__(
        self,
        popup: bool = False,
        width: int = 400,
        title: str = "Search Dialog",
        ok_handler: Callable[[AbstractDialog, str], None] = None,
        cancel_handler: Callable[[AbstractDialog], None] = None,
        ok_label: str = "Search",
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
            button_style="SearchMenu.Button",
        )

        self._fields = {}
        self._me_buttons = {}
        self._build_ui()

    def build_ui_for_prefixes(self, prefixes: list):
        """Set new prefix list (from search service).
        Rebuild UI and copy over any UI elements that remain in the prefix list.
        """
        if prefixes != self._prefixes:
            self._prefixes = prefixes
            self._fields = {}
            self._build_ui()

    def clear(self):
        for field in self._fields.values():
            field.set_default()
        # set date back to "Anytime"
        if GrammarPrefix.MODIFIED_BEFORE in self._fields and GrammarPrefix.MODIFIED_AFTER in self._fields:
            self._calendar.clear()

    def _ok_wrapper(self, dialog: AbstractDialog, ok_handler: Callable[[AbstractDialog, str], None] = None):
        """Convert the fields of the search menu to a single string."""
        search_words = []
        for name, field in self._fields.items():
            text = field.model.get_value_as_string().strip()
            # description and path get special treatment. Only create 1 value.
            if text and name in SearchMenu.AUTO_GROUPED_PREFIXES:
                search_words.append(f"{name}:{quotify(text)}")
            elif text and name in SearchMenu.AUTO_OR_PREFIXES:
                # Ensure commas are the separators
                values = [value for value in text.replace(" ", ",").split(",") if value]
                search_words.append(name + ":" + ",".join(values))
            else:
                values = split_with_quotes(text)
                for value in values:
                    search_words.append(f"{name}:{value}")

        if ok_handler:
            ok_handler(dialog, search_words)

    def _cancel_wrapper(self, dialog: AbstractDialog, cancel_handler: Callable[[AbstractDialog], None] = None):
        self.hide()
        if cancel_handler:
            cancel_handler(dialog)

    async def reset_position(self):
        await super().reset_position()
        if GrammarPrefix.PATH in self._fields:
            value = self._fields[GrammarPrefix.PATH].model.get_value_as_string().strip()
            self._fields[GrammarPrefix.PATH]._hint_container.visible = not bool(value)

    def _set_field_to_username(self, field_name: str):
        if field_name in self._fields:
            self._fields[field_name].model.set_value(self._username)

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, name: str):
        self._username = name
        for me_button in self._me_buttons.values():
            me_button.visible = True if self._username else False

    def _build_ui_field(self, field_name: str, label: str, hint: str, me_button: bool = False):
        if field_name in self._prefixes:
            with ui.HStack(spacing=SearchMenu.H_SPACING):
                ui.Spacer(width=5)
                ui.Label(label, width=SearchMenu.LABEL_COLUMN_WIDTH)
                self._fields[field_name] = NamedField(field_name, hint=hint)
                if me_button:
                    self._me_buttons[field_name] = ui.Button(
                        "Me",
                        width=30,
                        clicked_fn=lambda f=field_name: self._set_field_to_username(field_name),
                        style_type_name_override="MeButton.Button",
                    )
                    self._me_buttons[field_name].visible = True if self._username else False
                ui.Spacer(width=5)
            ui.Spacer(height=3)

    def populate_fields(self, search_words):
        # populate search fields with search_words
        fields = {key: [] for key in self._fields.keys()}
        for word in search_words:
            c = word.find(":")
            if c != -1:
                prefix = word[:c]
                suffix = word[c + 1 :]
                # No need for quotes as all terms will be grouped together
                if prefix in SearchMenu.AUTO_GROUPED_PREFIXES or prefix in SearchMenu.AUTO_OR_PREFIXES:
                    suffix = suffix.strip('"')
                if prefix in fields:
                    if prefix in SearchMenu.SINGLE_VALUE_PREFIXES:
                        fields[prefix] = [suffix]
                    else:
                        fields[prefix].append(suffix)

        self.clear()
        for key in self._fields.keys():
            if fields[key]:
                # Note: This should handle both larger AND smaller as BETWEEN, but this has been purposefully disabled
                # for now to align the UI with navigator.
                if key == GrammarPrefix.LARGER_THAN:
                    self._file_size_model.get_item_value_model().set_value(0)
                elif key == GrammarPrefix.SMALLER_THAN:
                    self._file_size_model.get_item_value_model().set_value(1)
                if key == GrammarPrefix.MODIFIED_BEFORE:
                    self._calendar.set_before_date(" ".join(fields[key]))
                elif key == GrammarPrefix.MODIFIED_AFTER:
                    self._calendar.set_after_date(" ".join(fields[key]))
                elif key in SearchMenu.AUTO_OR_PREFIXES:
                    self._fields[key].model.set_value(",".join(fields[key]))
                else:
                    self._fields[key].model.set_value(" ".join(fields[key]))

    def _build_ui(self):
        # Create and show the window with field and list of tips
        super()._build_ui()
        with self._window.frame:
            with ui.ZStack(height=0, style=self._style):
                ui.Rectangle(style_type_name_override="Background")
                with ui.VStack():
                    ui.Spacer(height=5)
                    error_messages = ui.HStack(height=0, spacing=5)
                    with error_messages:
                        with ui.ZStack(height=0):
                            ui.Rectangle(style_type_name_override="ErrorMessages")
                            error_label = ui.Label("", style_type_name_override="ErrorMessages.Label")
                    error_messages.visible = False

                    def show_error_message(visible: bool, message: str = ""):
                        error_messages.visible = visible
                        error_label.text = message

                    self._build_ui_field(
                        field_name=GrammarPrefix.DESCRIPTION, label="AI Search", hint="e.g. red rusty barrel"
                    )
                    self._build_ui_field(field_name=GrammarPrefix.NAME, label="File Name", hint="File or Folder Name")
                    self._build_ui_field(
                        field_name=GrammarPrefix.CREATED_BY,
                        label="Created by",
                        hint="e.g. user-name@my-company.com",
                        me_button=True,
                    )
                    self._build_ui_field(
                        field_name=GrammarPrefix.MODIFIED_BY,
                        label="Modified by",
                        hint="e.g. user-name@my-company.com",
                        me_button=True,
                    )
                    self._build_ui_field(field_name=GrammarPrefix.TAG, label="Tags", hint="e.g. red, blue")
                    self._build_ui_field(field_name=GrammarPrefix.EXT, label="File Type", hint="e.g. usd")
                    if GrammarPrefix.LARGER_THAN in self._prefixes and GrammarPrefix.SMALLER_THAN in self._prefixes:
                        with ui.HStack(spacing=SearchMenu.H_SPACING):
                            ui.Spacer(width=5)
                            ui.Label("File Size", width=SearchMenu.LABEL_COLUMN_WIDTH)
                            # A third option "Between" has been temporarily removed to align the UI with navigator
                            self._file_size_model = ui.ComboBox(0, "Greater than", "Less than", width=100).model
                            self._fields[GrammarPrefix.LARGER_THAN] = NamedField(GrammarPrefix.LARGER_THAN, hint="0 MB")
                            self._fields[GrammarPrefix.SMALLER_THAN] = NamedField(
                                GrammarPrefix.SMALLER_THAN, hint="0 MB"
                            )
                            self._fields[GrammarPrefix.SMALLER_THAN].container.visible = False

                            def range_fields(model):
                                index = model.get_item_value_model().get_value_as_int()
                                if index == 1:
                                    self._fields[GrammarPrefix.LARGER_THAN].container.visible = False
                                    self._fields[GrammarPrefix.LARGER_THAN].model.set_value("")
                                else:
                                    self._fields[GrammarPrefix.LARGER_THAN].container.visible = True
                                if index == 0:
                                    self._fields[GrammarPrefix.SMALLER_THAN].container.visible = False
                                    self._fields[GrammarPrefix.SMALLER_THAN].model.set_value("")
                                else:
                                    self._fields[GrammarPrefix.SMALLER_THAN].container.visible = True

                            self._file_size_model.add_item_changed_fn(lambda m, i: range_fields(m))
                            ui.Spacer(width=5)
                        ui.Spacer(height=3)
                    if (
                        GrammarPrefix.MODIFIED_BEFORE in self._prefixes
                        and GrammarPrefix.MODIFIED_AFTER in self._prefixes
                    ):
                        with ui.HStack(spacing=SearchMenu.H_SPACING):
                            ui.Spacer(width=5)
                            ui.Label("Date", width=SearchMenu.LABEL_COLUMN_WIDTH)
                            self._calendar = CalendarController(
                                error_handler=show_error_message,
                                ok_handler=lambda m: asyncio.ensure_future(self.reset_position()),
                            )
                            self._fields[GrammarPrefix.MODIFIED_BEFORE] = self._calendar.created_before_field
                            self._fields[GrammarPrefix.MODIFIED_AFTER] = self._calendar.created_after_field
                            ui.Spacer(width=5)
                        ui.Spacer(height=3)
                    with ui.HStack(spacing=SearchMenu.H_SPACING):
                        ui.Spacer(width=150)
                        super()._build_ok_cancel_buttons()
                        ui.Spacer(width=5)
                    ui.Spacer(height=15)
                # VStack
            # ZStack
        self.hide()

    def destroy(self):
        super().destroy()
        self._calendar = None
        self._fields = None
        self._me_buttons = None

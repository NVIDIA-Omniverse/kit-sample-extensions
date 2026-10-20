# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path
from typing import Optional

import omni.client
import omni.ui as ui

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")

ITEM_SIZE = 40
ICON_SIZE = 25
SECTION_HEIGHT = 30


def _is_file_exists(filename: str):
    """Returns True if the given file exists"""
    result, stat = omni.client.stat(filename)
    return result == omni.client.Result.OK


class QuickSearchDelegate(ui.AbstractItemDelegate):
    """The default delegate for TreeView of the Quick Search window."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._flat = kwargs.pop("flat", False)
        self._item_delegate = kwargs.pop("item_delegate", None)
        self._filter_by_text: str = ""

    def build_branch(self, model, item, column_id, level, expanded):
        if item is None:
            if model.can_item_have_children(item):
                with ui.ZStack():
                    # Background Color
                    with ui.VStack():
                        ui.Spacer(height=2)
                        ui.Rectangle(height=SECTION_HEIGHT, name="section_background")
                        ui.Spacer(height=2)

                    with ui.HStack():
                        ui.Spacer(width=5)
                        with ui.VStack(width=0):
                            ui.Spacer()
                            # Collapse/Expand button
                            icon_path = "open" if expanded else "closed"
                            icon_path = ICON_PATH.joinpath(f"{icon_path}.svg")
                            ui.ImageWithProvider(
                                f"{icon_path}",
                                width=10,
                                height=10,
                                style_type_name_override="TreeView.Section.Icon",
                                name="Collapse",
                            )
                            ui.Spacer()
                        ui.Spacer(width=5)
        else:
            if self._item_delegate:
                self._item_delegate.build_branch(model, item, column_id, level, expanded)

    def build_section_widget(self, model, item, column_id, level, expanded):
        with ui.ZStack():
            # Background Color
            ui.Rectangle(height=SECTION_HEIGHT, name="section_background")
            # Section Title
            with ui.VStack():
                ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    value_model = model.get_item_value_model(item, column_id)
                    ui.Label(value_model.as_string, style_type_name_override="TreeView.Item", name="Title")
                    ui.Spacer()
                    num_childreen = len(model.get_item_children(item))
                    ui.Label(f"{num_childreen}", name="count", width=0)
                    ui.Spacer(width=30)
                ui.Spacer()

    def _get_item_icon_path(self, model, item) -> str:
        icon_path = ""
        icon_model = model.get_item_value_model(item, 2)
        if icon_model:
            icon: Optional[str] = icon_model.as_string
            icon_path = icon
        else:
            icon: Optional[str] = None
        if not icon or not _is_file_exists(icon_path):
            icon_path = ICON_PATH.joinpath("default.svg")

        return icon_path

    def build_item_widget(self, model, item, column_id, level, expanded):
        """build the widget for the items"""
        with ui.HStack():
            ui.Spacer(width=5)
            icon_path = self._get_item_icon_path(model, item)
            ui.ImageWithProvider(
                f"{icon_path}",
                width=ITEM_SIZE - 10,
                height=ITEM_SIZE - 10,
                style_type_name_override="TreeView.Section.Icon",
                name="Icon",
            )
            ui.Spacer(width=5)

            with ui.VStack(spacing=5, height=ITEM_SIZE):
                ui.Spacer()
                value_model = model.get_item_value_model(item, 0)
                description_model = model.get_item_value_model(item, 1)
                tooltip_model = model.get_item_value_model(item, 3)
                tooltip = ""
                if tooltip_model:
                    tooltip = tooltip_model.as_string

                with ui.HStack(height=0, width=0, spacing=3, tooltip=tooltip):
                    ui.Label(
                        value_model.as_string, style_type_name_override="TreeView.Item", name="Title", elidedText=True
                    )
                if description_model and description_model.as_string:
                    description = description_model.as_string.partition("\n")[0]
                    ui.Label(description, height=0, style_type_name_override="TreeView.Item", name="Description")
                ui.Spacer()

    def build_widget(self, model, item, column_id, level, expanded):
        if item is None:
            if model.can_item_have_children(item):
                # Build the section_widget
                self.build_section_widget(model, item, column_id, level, expanded)
        else:
            if self._item_delegate:
                self._item_delegate.build_widget(model, item, column_id, level, expanded)
            else:
                self.build_item_widget(model, item, column_id, level, expanded)

    def filter_by_text(self, filter_name_text: str):
        """Saves the filtering text to use it when drawing the item"""
        self._filter_by_text = filter_name_text

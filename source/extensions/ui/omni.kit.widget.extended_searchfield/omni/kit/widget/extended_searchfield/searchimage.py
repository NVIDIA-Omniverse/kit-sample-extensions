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

import carb
from omni import ui

from .utils import IMAGE_TYPES, is_omniverse_url, remove_quotes


class SearchImageButton:
    """
    Represents a search image widget, combined with a label to show the image and a close button to remove it.
    Args:
        path (str): Path to image.
    Keyword args:
        on_close_fn (callable): Function called when close button clicked. Function signature:
            void on_close_fn(widget: SearchWordButton)
    """

    SMALL_SIZE = 18
    LARGE_SIZE = 60

    def __init__(self, path: str, large: bool, on_close_fn: callable = None):
        settings = carb.settings.get_settings()
        self._theme = settings.get_as_string("/persistent/app/window/uiStyle") or "NvidiaDark"

        style = "ExtendedSearchField.LargeImage" if large else "ExtendedSearchField.Image"
        size = SearchImageButton.LARGE_SIZE if large else SearchImageButton.SMALL_SIZE
        path = remove_quotes(path) if path else ""

        self._container = ui.ZStack(width=0)
        with self._container:
            with ui.VStack():
                ui.Spacer(height=2)
                ui.Rectangle(style_type_name_override=style)
                ui.Spacer(height=2)
            with ui.HStack():
                ui.Spacer(width=5)
                if not is_omniverse_url(path) and os.path.splitext(path)[1].lower() in IMAGE_TYPES:
                    with ui.VStack():
                        ui.Spacer(height=5)
                        ui.Image(path, width=size, height=size)
                        ui.Spacer(height=5)
                filename = os.path.basename(path)
                ui.Spacer(width=5)
                ui.Label(filename, width=0, style_type_name_override=f"{style}.Label")
                ui.Spacer(width=5)
                ui.Button(
                    image_width=8,
                    style_type_name_override=f"{style}.Button",
                    clicked_fn=lambda: on_close_fn(self) if on_close_fn is not None else None,
                )
                ui.Spacer(width=5)

    @property
    def visible(self) -> None:
        """
        Widget visibility
        """
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._container.visible = value

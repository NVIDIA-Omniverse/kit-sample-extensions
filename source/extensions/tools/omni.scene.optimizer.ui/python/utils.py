# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import pathlib
from functools import partial

import omni.kit.app
import omni.ui as ui

EXT_PATH = pathlib.Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
ICON_PATH = EXT_PATH.joinpath("icons")


def get_icon(icon):
    """Get the path to an icon"""
    return str(ICON_PATH.joinpath(icon))


def show_tooltip(label):  # pragma: no cover
    """Show a tooltip.

    Use this callback to avoid issues with the tooltip inheriting style
    (in particular margin/padding) from parent widgets.
    """
    ui.Label(
        label,
        style={
            "color": 0xFF585A51,
            "background_color": 0xFFCAF5FB,
            "margin": 2,
            "padding": 4,
        },
    )
    return


class ImageAndTextButton(ui.ZStack):
    """ZStack-based button that centers an icon alongside text."""

    def __init__(self, label, width, height, image_path, image_width, image_height, mouse_pressed_fn, tooltip):

        super().__init__(width=width, height=height, style={"margin": 1, "padding": 1})

        with self:

            # Add a button with a blank space for the label - this ensures it respects the
            # height
            ui.Button(
                " ",
                width=ui.Percent(100),
                height=height,
                mouse_pressed_fn=mouse_pressed_fn,
                tooltip_fn=partial(show_tooltip, tooltip),
            )

            # HStack with an image and label
            with ui.HStack(width=ui.Percent(100)):
                ui.Spacer()
                im = ui.Image(image_path, width=image_width)
                ui.Spacer(width=ui.Pixel(4))
                ui.Label(label, width=0)
                ui.Spacer()

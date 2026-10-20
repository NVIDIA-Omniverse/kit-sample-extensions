"""Provides default UI style configurations for web deeplink components."""

import omni.ui as ui
from omni.ui import color as cl


def get_style():
    """Returns the default UI style configuration for deeplink components.

    Returns:
        dict: Style dictionary containing Button and ScrollingFrame styling properties.
    """
    return {
        "Button": {
            "margin": 4,
            "border_radius": 4,
            "padding": 4,
        },
        "ScrollingFrame": {"background_color": 0x00000000},
    }

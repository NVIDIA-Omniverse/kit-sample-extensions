# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module implements the core browser functionality for the Omniverse Kit SDK by providing data models, delegates, and widget components for managing collections, categories, and detail items, along with viewport drag and drop helper utilities."""

__all__ = [
    "AbstractBrowserModel",
    "CategoryItem",
    "CollectionItem",
    "DetailItem",
    "BrowserSearchBar",
    "BrowserWidget",
    "CategoryDelegate",
    "DetailDelegate",
    "OptionsMenu",
    "OptionMenuDescription",
    "TreeBrowserWidget",
    "TreeCategoryDelegate",
    "create_drop_helper",
]

from typing import Callable

from .models import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem
from .widgets import (
    BrowserSearchBar,
    BrowserWidget,
    CategoryDelegate,
    DetailDelegate,
    OptionMenuDescription,
    OptionsMenu,
    TreeBrowserWidget,
    TreeCategoryDelegate,
)


def get_legacy_viewport_interface():
    try:
        import omni.kit.viewport_legacy

        return omni.kit.viewport_legacy.get_viewport_interface()
    except ImportError:
        pass

    try:
        import omni.kit.viewport

        return omni.kit.viewport.get_viewport_interface()
    except ImportError:
        pass
    except AttributeError:
        pass

    return None


def create_drop_helper(
    pickable: bool = False,
    add_outline: bool = True,
    on_drop_accepted_fn: Callable = None,
    on_drop_fn: Callable = None,
    on_pick_fn: Callable = None,
    protocal: str = None,
):
    """Creates a drop helper for viewport drag and drop functionality.

    This function attempts to import a drop helper from omni.kit.viewport.window or from omni.kit.viewport.window.dragdrop. If protocal is provided, it adds the protocol to the list of ignored protocols in SceneDropDelegate. If the primary import fails due to ImportError, the function falls back to the legacy viewport interface to create the drop helper. Returns a drop helper object if available, otherwise returns None.

    Args:
        pickable (bool): Specifies if the helper is pickable.
        add_outline (bool): Specifies if a visual outline is added.
        on_drop_accepted_fn (Callable): Function invoked when drop is accepted.
        on_drop_fn (Callable): Function invoked when drop occurs.
        on_pick_fn (Callable): Function invoked when an item is picked.
        protocal (str): Protocol name to ignore in SceneDropDelegate.

    Returns:
        object: The drop helper object if created; otherwise, None.
    """
    try:
        try:
            from omni.kit.viewport.window import create_drop_helper as create_viewport_drop_helper
        except ImportError:
            from omni.kit.viewport.window.dragdrop import create_drop_helper as create_viewport_drop_helper

        if protocal is not None:
            from omni.kit.viewport.window.dragdrop.scene_drop_delegate import SceneDropDelegate

            SceneDropDelegate.add_ignored_protocol(protocal)

        return create_viewport_drop_helper(
            pickable=pickable,
            add_outline=add_outline,
            on_drop_accepted_fn=on_drop_accepted_fn,
            on_drop_fn=on_drop_fn,
            on_pick_fn=on_pick_fn,
        )

    except ImportError:
        viewport = get_legacy_viewport_interface()
        if viewport:
            return viewport.create_drop_helper(
                pickable=pickable,
                add_outline=add_outline,
                on_drop_accepted_fn=on_drop_accepted_fn,
                on_drop_fn=on_drop_fn,
                on_pick_fn=on_pick_fn,
            )
    return None

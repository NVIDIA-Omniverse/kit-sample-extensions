# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb.settings
import omni.ext
from omni.kit.viewport.menubar.core import CategoryStateItem

from .constants import METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
from .tools import get_per_viewport_setting_path


class MetricsAssemblerViewportMenu:
    """Class for managing the metrics assembler viewport menu.

    Handles registration and unregistration of viewport menu items for displaying units.
    """

    MENU_NAME: str = "Units"

    def __init__(self) -> None:
        """Initialize the viewport menu.

        Sets up settings interface and menubar instance and registers menu items.
        """
        super().__init__()
        self._settings = carb.settings.acquire_settings_interface()
        self._menubar_instance = omni.kit.viewport.menubar.display.get_instance()
        self.register()

    def destroy(self) -> None:
        """Clean up resources when destroying the menu.

        Unregisters menu items and clears references.
        """
        self.unregister()
        self._settings = None
        self._menubar_instance = None

    def register(self) -> None:
        """Register the viewport menu items.

        Creates and registers a CategoryStateItem for the Units menu.
        """
        self._viewport_item = CategoryStateItem(
            MetricsAssemblerViewportMenu.MENU_NAME,
            get_setting_path_fn=lambda vp: get_per_viewport_setting_path(
                str(vp.id), METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
            ),
        )
        self._menubar_instance.register_custom_category_item("Show By Type", self._viewport_item)

    def unregister(self) -> None:
        """Unregister the viewport menu items.

        Removes the registered menu items from the viewport.
        """
        self._menubar_instance.deregister_custom_category_item("Show By Type", self._viewport_item)

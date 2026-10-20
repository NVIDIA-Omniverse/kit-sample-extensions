# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio

import carb
import omni.ext
from omni.kit.menu.utils import MenuHelperExtensionFull

from .demo_ui.model_registry_window import ModelRegistryWindow


class IRAModelRegistryExtension(omni.ext.IExt):
    """Demo extension for the model registry system."""

    def on_startup(self, ext_id):
        carb.log_info("Model Registry Demo UI has been activated successfully.")
        self._ext_id = ext_id
        self._menu_helper = MenuHelperExtensionFull()
        # set up the UI components
        # TODO:: refine the UI component so that it can be more versatile.
        self.setup_extension_ui()
        carb.log_info("Model Registry Demo UI has been activated successfully.")

    def on_shutdown(self):
        carb.log_warn("Model Registry Demo UI has been deactivated successfully.")
        async def shutdown_menu_helper(menu_helper):
            # First make sure all windows are closed
            for i in range(len(menu_helper._window_list)):
                menu_helper.show_window(None, False, i)
            # Wait for MenuHelperExtensionFull._destroy_window_async to trigger
            await omni.kit.app.get_app().next_update_async()
            # Wait for MenuHelperExtensionFull._destroy_window_async to finish
            await omni.kit.app.get_app().next_update_async()
            # Finally we shutdown the menu
            menu_helper.menu_shutdown()

        # Keep a reference to the shutdown task to satisfy linters and avoid GC.
        self._shutdown_task = asyncio.ensure_future(shutdown_menu_helper(self._menu_helper))

        # Clean variables
        self._menu_helper = None

    def setup_extension_ui(self):
        """Set up the model registry extension."""
        # chat ira ui panel
        model_registry_panel = self._menu_helper.menu_startup(
            lambda: ModelRegistryWindow(), "Model_Registry", "Model_Registry", "Tools/Model Registry"
        )
        self._menu_helper.show_window("", False, model_registry_panel)

        # Temporary solution to trigger menu refresh
        # since menu helper doest not trigger it at start
        import omni.kit.menu.utils
        omni.kit.menu.utils.rebuild_menus()
        carb.log_info("Model Registry Demo UI has been activated successfully.")

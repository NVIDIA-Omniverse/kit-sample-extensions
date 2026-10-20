# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["ViewportLightingMenuBarExtension"]

import omni.ext


class ViewportLightingMenuBarExtension(omni.ext.IExt):
    """The Entry Point for the Lighting item in Viewport Menu Bar"""

    def __init__(self):
        super().__init__()
        self.__registered_items = []
        self.__cmds = None

    def on_startup(self, ext_id, *args, **kwargs):
        ext_name = ext_id.split("-")[0]

        from .menu_container import MenuContainer

        self.__registered_items.append(MenuContainer(ext_name))

        # Check if the light-rig should be applied even if the menu item is not visible or built
        import carb

        if carb.settings.get_settings().get("/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enableWithoutMenu"):
            self.__no_menu_setup(self.__registered_items[-1])

        from .actions import RegisteredActions

        self.__registered_items.append(RegisteredActions(ext_name))

        from .commands import register_commands

        self.__cmds = register_commands()

    def on_shutdown(self):
        if self.__registered_items:
            for item in self.__registered_items:
                item.destroy()
            self.__registered_items = None

        from .commands import unregister_commands

        cmds, self.__cmds = self.__cmds, None
        unregister_commands(cmds)

    def __no_menu_setup(self, menu_container: "MenuContainer"):
        # Create a simple delegate with the properties required to manage the auto-rig state
        class FakeViewport:
            @property
            def id(self):
                return "Viewport/Viewport0"

            @property
            def usd_context_name(self):
                return ""

            @property
            def usd_context(self):
                return omni.usd.get_context(self.usd_context_name)

        self.__registered_items.append(menu_container._create_menu_context(FakeViewport()))

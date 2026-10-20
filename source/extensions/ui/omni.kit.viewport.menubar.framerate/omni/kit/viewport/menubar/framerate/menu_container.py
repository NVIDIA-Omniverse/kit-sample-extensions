# Copyright (c) 2021-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MenuContainer"]


from typing import Any, Dict

import carb
import omni.kit.hotkeys.core as hotkeys
import omni.ui as ui
from omni.kit.actions.core import get_action_registry
from omni.kit.viewport.menubar.core import (
    IconMenuDelegate,
    SelectableMenuItem,
    SettingModel,
    ViewportMenuContainer,
    ViewportMenuDelegate,
)
from rtx.settings import get_internal_setting_string

_DEFAULT_HOTKEY_MAP = {
    "FramePacingCyclePresets": "SHIFT+ALT+P",
}


class MenuContainer(ViewportMenuContainer):
    """The menu with the list of framerate presets"""

    def __init__(self, ext_id: str):
        from .style import UI_STYLE

        self.__ext_id: str = ext_id
        self.__ext_setting_path: str = f"/exts/{ext_id}"

        super().__init__(
            name="FrameRate",
            delegate=None,
            visible_setting_path=f"{self.__ext_setting_path}/visible",
            order_setting_path=f"{self.__ext_setting_path}/order",
            style=UI_STYLE,
        )

        self._root_menus: Dict[int, ui.Menu] = {}

        # Need to rebuild menu if preset changes, or if dlss-g support changes
        self._preset_model = SettingModel("/exts/omni.kit.viewport.menubar.framerate/currentPreset")
        self.__sub_preset = self._preset_model.subscribe_value_changed_fn(self.__on_preset_changed)
        self._show_dlssg_model = SettingModel("/exts/omni.kit.viewport.menubar.framerate/showDLSSG")
        self.__sub_show_dlssg = self._show_dlssg_model.subscribe_value_changed_fn(lambda m: self.__build_presets())
        self._has_dlssg_model = SettingModel(get_internal_setting_string("/rtx-transient/internal/dlssg/supported"))
        self.__sub_has_dlssg = self._has_dlssg_model.subscribe_value_changed_fn(lambda m: self.__build_presets())

        self._prev_preset = ""
        self._rendermode_model = SettingModel("/rtx/rendermode")
        self.__sub_rendermode = self._rendermode_model.subscribe_value_changed_fn(self.__on_rendermode_changed)

        self._settings = carb.settings.get_settings()
        self._presets: Dict[str, Dict[str, Any]] = {}
        # Every preset Kit defines, including those this menu does not offer (DLSS-G "x2" presets without DLSS-G).
        self._known_presets: Dict[str, Dict[str, Any]] = {}

        self.__register_actions(self.__ext_id)
        self.__register_hotkeys(self.__ext_id)

    def __build_presets(self):
        # Load presets from rendering page, or developer page for newer Kit versions
        try:
            import omni.kit.window.preferences.scripts.pages.developer_page as presets_module
        except ImportError:
            import omni.kit.window.preferences.scripts.pages.rendering_page as presets_module

        self._presets.clear()
        self._known_presets.clear()

        if hasattr(presets_module, "THREAD_SYNC_PRESETS"):
            presets = presets_module.THREAD_SYNC_PRESETS
            for name, settings in presets:
                if not name:
                    carb.log_warn(f"Skipping preset '{name}")
                    continue

                # Cleanup names a bit in case we're using an old kit-sdk
                if name == "None":
                    continue
                elif name == "None Precise":
                    name = "No Pacing"
                self._known_presets[name] = settings
                if name == "120":
                    continue

                # Only show "x2" presets if dlss-g is available.
                show_dlssg = self._settings.get("/exts/omni.kit.viewport.menubar.framerate/showDLSSG")
                has_dlssg = self._settings.get(get_internal_setting_string("/rtx-transient/internal/dlssg/supported"))
                if (
                    name != "No Pacing"
                    and (not show_dlssg or not has_dlssg)
                    and settings.get("/rtx-transient/dlssg/enabled", False)
                ):
                    continue

                self._presets[name] = settings

        self.__on_preset_changed(self._preset_model)

    def destroy(self) -> None:
        self.__deregister_hotkeys(self.__ext_id)
        self.__deregister_actions(self.__ext_id)
        self.__sub_preset = None
        self.__sub_rendermode = None
        self.__sub_show_dlssg = None
        self.__sub_has_dlssg = None
        super().destroy()

    def build_fn(self, viewport_context: Dict):
        """Entry point for the per Viewport menu bar item"""

        # defer building presets to here to avoid an issue querying dlss-g support on startup
        if not self._presets:
            self.__build_presets()

        viewport_api_id = viewport_context["viewport_api"].id
        # Build the root level menu item per viewport context
        self._root_menus[viewport_api_id] = ui.Menu(
            self._preset_model.as_string or self.name,
            delegate=IconMenuDelegate(name=self.name, text=True, width=40),
            on_build_fn=self.__build_root_menus,
            style=self._style,
            hide_on_click=True,
            tooltip="Pacing Speed",
        )

    def __build_root_menus(self):
        # Root menu is just a flat MenuItemCollection
        ui.MenuItemCollection(on_build_fn=self.__build_preset_menu)

    def __build_preset_menu(self):
        kwargs = {"hide_on_click": False, "checkable": True, "toggle": False}

        # Do nothing if there are no presets
        if not self._presets:
            return

        ui.Separator("Pacing Speed")

        for name in self._presets.keys():
            # Create the menu item with transformed name and passes name to setting model
            SelectableMenuItem(
                name,
                delegate=ViewportMenuDelegate(),
                checked=self._preset_model.as_string == name,
                triggered_fn=lambda preset=name, *_: self._preset_model.set_value(preset),
                **kwargs,
            )

    def __apply_preset(self, model: SettingModel) -> None:
        # Apply preset settings
        preset = model.as_string
        if preset in self._presets:
            for key, value in self._presets[preset].items():
                # skip viewport tickrate, because it has no effect after viewport creation
                if key != "/persistent/app/viewport/defaults/tickRate":
                    self._settings.set(key, value)

    def __on_preset_changed(self, model: SettingModel) -> None:
        self.__apply_preset(self._preset_model)

        # Refresh menu text and sub menu items stats. With no preset selected, keep the name, as build_fn does: an
        # empty text hides the menubar button.
        for root_menu in self._root_menus.values():
            root_menu.invalidate()
            root_menu.text = self._preset_model.as_string or self.name

    def __on_rendermode_changed(self, model: SettingModel) -> None:
        if model.as_string == "PathTracing":
            if self._preset_model.as_string != "No Pacing":
                # store previous preset and force Uncapped mode
                self._prev_preset = self._preset_model.as_string
                self._preset_model.as_string = "No Pacing"
        elif self._prev_preset:
            self._preset_model.as_string = self._prev_preset
            self._prev_preset = ""

    def __register_actions(self, extension_id: str) -> None:
        action_registry = get_action_registry()
        actions_tag = "Frame Pacing Actions"

        action_registry.register_action(
            extension_id,
            "FramePacingCyclePresets",
            self.__cycle_presets,
            display_name="Frame Pacing Cycle Presets",
            description="Cycle between all available frame pacing presets",
            tag=actions_tag,
        )

    def __deregister_actions(self, extension_id) -> None:
        action_registry = get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)

    def __register_hotkeys(self, extension_id: str) -> None:
        hotkey_registry = hotkeys.get_hotkey_registry()
        action_registry = get_action_registry()
        ext_actions = action_registry.get_all_actions_for_extension(extension_id)

        for action in ext_actions:
            key = _DEFAULT_HOTKEY_MAP.get(action.id, None)
            # Not all Actions will have default hotkeys
            if not key:
                continue

            hotkey_registry.register_hotkey(
                hotkey_ext_id=extension_id,
                key=key,
                action_ext_id=action.extension_id,
                action_id=action.id,
                filter=None,
            )

    def __deregister_hotkeys(self, extension_id: str) -> None:
        hotkey_registry = hotkeys.get_hotkey_registry()
        hotkey_registry.deregister_all_hotkeys_for_extension(extension_id)

    def __next_preset(self, current_preset: str) -> str:
        names = list(self._presets.keys())
        if current_preset in names:
            return names[(names.index(current_preset) + 1) % len(names)]
        # The current preset is not offered (a DLSS-G "x2" preset kept without DLSS-G, or a custom or empty value):
        # go to the offered preset with the nearest render rate, else the first. Cycling an infinite list until it
        # found the current preset never ended here and froze the app.
        rate_key = "/app/runLoops/rendering_0/rateLimitFrequency"
        rate = self._known_presets.get(current_preset, {}).get(rate_key)
        if rate is None:
            return names[0]
        return min(names, key=lambda name: abs(self._presets[name].get(rate_key, rate) - rate))

    def __cycle_presets(self) -> None:
        # It's possible that the presets have yet to be populated.
        if not self._presets:
            self.__build_presets()

            # If there are still no available presets then just bail.
            if not self._presets:
                return

        next_preset = self.__next_preset(self._preset_model.as_string)

        self._preset_model.set_value(next_preset)
        carb.log_warn(f"Frame pacing set to: {next_preset}")

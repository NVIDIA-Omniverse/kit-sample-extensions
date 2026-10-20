# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MenuContainer"]


from functools import partial
from typing import Callable, Dict, List, Optional, Sequence, Union
from weakref import proxy

import carb
import omni.kit.commands
import omni.ui as ui
import omni.usd
from omni.kit.app import SettingChangeSubscription
from omni.kit.viewport.menubar.core import (
    IconMenuDelegate,
    MenuDisplayStatus,
    SelectableMenuItem,
    SettingModel,
    ViewportMenuContainer,
    ViewportMenuDelegate,
)
from pxr import UsdLux

from .actions import _import_light_rig, _set_lighting_mode
from .utility import (
    RefCountedUsdContextSub,
    _get_light_rig_setting_key,
    _get_rig_names_and_paths,
    _make_light_mode_setting_key,
    stage_has_api_type,
)


class MenuContext:
    def __init__(
        self,
        viewport_api,
        hide_on_click: bool,
        on_stage_opened: Callable,
        setting_key: str,
        setting_change: Callable,
        light_added_cb,
    ):
        self.__viewport_api = viewport_api
        self.__destroyables = []
        self.__hide_on_click: bool = hide_on_click
        self.__root_menu: Optional[ui.Menu] = None
        self.__import_item: Optional[ui.MenuItem] = None
        self.__menu_items: List[ui.MenuItem] = []
        self.__has_any_light: Optional[bool] = None
        self.__usd_context_sub = RefCountedUsdContextSub(
            viewport_api.usd_context_name, partial(on_stage_opened, proxy(self)), setting_key, setting_change
        )

        self.__post_do_cbs = None
        self.__light_added_cb = None
        if light_added_cb:
            self.__light_added_cb = light_added_cb
            # Watch for either CreatePrim command to check if the prim_type was a light
            self.__post_do_cbs = (
                omni.kit.commands.register_callback(
                    "CreatePrimCommand", omni.kit.commands.POST_DO_CALLBACK, self.__post_do_callback
                ),
                omni.kit.commands.register_callback(
                    "CreatePrimWithDefaultXform", omni.kit.commands.POST_DO_CALLBACK, self.__post_do_callback
                ),
            )

    def __del__(self):
        self.destroy()

    def __post_do_callback(self, cmd_dict: dict):
        if not self.__light_added_cb:
            return
        # XXX: Ideally we would have prim-path and check HasAPI(UsdLux.LightAPI) on that
        light_types = ("CylinderLight", "DiskLight", "DistantLight", "DomeLight", "RectLight", "SphereLight")
        if cmd_dict.get("prim_type") in light_types:
            self.__light_added_cb(self)

    def destroy(self):
        light_added_cb, self.__light_added_cb = self.__light_added_cb, None
        post_do_cbs, self.__post_do_cbs = self.__post_do_cbs, None
        if post_do_cbs:
            for post_do_cb in post_do_cbs:
                omni.kit.commands.unregister_callback(post_do_cb)

        menu_items, self.__menu_items = self.__menu_items, []
        for menu_item in menu_items:
            menu_item.destroy()

        destroyables, self.__destroyables = self.__destroyables, []
        for destroyable in destroyables:
            destroyable.destroy()

        if self.__import_item:
            self.__import_item.destroy()
            self.__import_item = None

        if self.__root_menu:
            self.__root_menu.destroy()
            self.__root_menu = None

        if self.__usd_context_sub:
            self.__usd_context_sub.destroy()
            self.__usd_context_sub = None

    def add_destroyable(self, destroyable):
        self.__destroyables.append(destroyable)

    def add_menu_item(self, menu_item: ui.MenuItem):
        self.__menu_items.append(menu_item)

    def invalidate(self):
        for obj in self.__destroyables:
            invalidate = getattr(obj, "invalidate", None)
            if invalidate:
                invalidate()

    @property
    def viewport_api(self):
        return self.__viewport_api

    @property
    def hide_on_click(self):
        return False

    @property
    def menu_items(self):
        return self.__menu_items

    @property
    def has_any_light(self) -> Optional[bool]:
        return self.__has_any_light

    @has_any_light.setter
    def has_any_light(self, any_lights: Optional[bool]):
        self.__has_any_light = any_lights

    @property
    def import_item(self) -> ui.MenuItem:
        return self.__import_item

    @import_item.setter
    def import_item(self, import_item: ui.MenuItem):
        if self.__import_item:
            self.__import_item.destroy()
        self.__import_item = import_item

    @property
    def delegate(self) -> ui.MenuDelegate:
        return self.root_menu.delegate

    @property
    def root_menu(self) -> ui.Menu:
        return self.__root_menu

    @root_menu.setter
    def root_menu(self, root_menu: ui.Menu):
        if self.__root_menu:
            self.__root_menu.destroy()
        self.__root_menu = root_menu


class MenuContainer(ViewportMenuContainer):
    """The menu with the list of lighting options"""

    def __init__(self, ext_id: str):
        from .style import UI_STYLE

        self.__ext_id: str = ext_id
        self.__ext_setting_path: str = f"/exts/{ext_id}"
        self.__setting_sub: Optional[Sequence[carb.settings.SubscriptionId]] = None
        self.__menu_contexts: Dict[int, MenuContext] = {}

        super().__init__(
            name="Lighting",
            delegate=None,
            visible_setting_path=f"{self.__ext_setting_path}/visible",
            order_setting_path=f"{self.__ext_setting_path}/order",
            style=UI_STYLE,
        )

        settings = carb.settings.get_settings()
        self.__setting_sub = (
            settings.subscribe_to_node_change_events(_get_light_rig_setting_key(ext_id), self.__rig_path_changed),
            settings.subscribe_to_node_change_events("/rtx/useViewLightingMode", self.__view_light_changed),
        )

    # When the directory to the rigs is changed, invalidate the MenuItemCollection to rebuild the labels
    def __rig_path_changed(self, item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            for ctx in self.__menu_contexts.values():
                ctx.invalidate()

    def destroy(self) -> None:
        setting_sub, self.__setting_sub = self.__setting_sub, tuple()
        if setting_sub:
            settings = carb.settings.get_settings()
            for sub in setting_sub:
                settings.unsubscribe_to_change_events(sub)

        menu_contexts, self.__menu_contexts = self.__menu_contexts, {}
        for ctx in menu_contexts.values():
            ctx.destroy()

        super().destroy()

    def _create_menu_context(self, viewport_api: "ViewportAPI", hide_on_click: bool = False):
        light_mode_key = _make_light_mode_setting_key(viewport_api.usd_context)
        menu_context = MenuContext(
            viewport_api,
            hide_on_click,
            self.__on_stage_open,
            light_mode_key,
            self.__on_mode_changed,
            self.__set_stage_lighting_mode,
        )
        self.__menu_contexts[viewport_api.id] = menu_context
        return menu_context

    def build_fn(self, viewport_context: Dict):
        """Entry point for the per Viewport menu bar item"""
        viewport_api = viewport_context.get("viewport_api") if viewport_context else None
        if viewport_api is None:
            carb.log_warn("Lighting menu-bar item built without a Viewport, skipping")
            return

        hide_on_click = viewport_context.get("hide_on_click", False)

        # Check for a previous context on this Viewport, and destroy it if found
        prev_menu_context = self.__menu_contexts.get(viewport_api.id)
        menu_context = self._create_menu_context(viewport_api, hide_on_click)

        # Build the root level menu ite (the selectable item and the light-toggle-button)
        menu_context.root_menu = ui.Menu(
            self.name,
            delegate=IconMenuDelegate(name=self.name, text=True, width=40),
            on_build_fn=partial(self.__build_root_menu, menu_context),
            style=self._style,
            hide_on_click=menu_context.hide_on_click,
        )

        if prev_menu_context:
            prev_menu_context.destroy()

    def __build_root_menu(self, menu_context: MenuContext):
        # Root menu is just a flat MenuItemCollection
        rig_collection = ui.MenuItemCollection(on_build_fn=lambda *args: self.__build_lighting_menu(menu_context))
        menu_context.add_destroyable(rig_collection)

    def __build_lighting_menu(self, menu_context: MenuContext):
        kwargs = {"hide_on_click": menu_context.hide_on_click, "checkable": True, "toggle": False}

        light_mode_key = _make_light_mode_setting_key(menu_context.viewport_api.usd_context)
        carb.settings.get_settings().set_default(light_mode_key, "")
        cur_value = carb.settings.get_settings().get(light_mode_key)

        def setup_item_with_model(mi: ui.MenuItem, trigered_fn: Callable, name: str):
            mi.set_triggered_fn(trigered_fn)
            menu_context.add_menu_item(mi)
            if mi.checked:
                menu_context.root_menu.text = mi.text
            mi.name = name

        # Mode to turn all lights off (passes None to __set_lighting_mode)
        mi = SelectableMenuItem("Lights Off", delegate=ViewportMenuDelegate(), checked=cur_value == "off", **kwargs)
        mi.identifier = "LightsOff"
        setup_item_with_model(mi, lambda mi=mi, *_: self.__set_lighting_mode("off", menu_context, mi), "off")

        # Mode to turn on special camera-light mode
        mi = SelectableMenuItem(
            "Camera Light", delegate=ViewportMenuDelegate(), checked=cur_value == "camera", **kwargs
        )
        mi.identifier = "CameraLight"
        setup_item_with_model(mi, lambda mi=mi, *_: self.__set_lighting_mode("camera", menu_context, mi), "camera")

        # Mode to turn all lights off (passes 'stage' to __set_lighting_mode)
        mi = SelectableMenuItem("Stage Lights", delegate=ViewportMenuDelegate(), checked=cur_value == "", **kwargs)
        mi.identifier = "StageLights"
        setup_item_with_model(mi, lambda mi=mi, *_: self.__set_lighting_mode("", menu_context, mi), "stage")

        # Do nothing if there are no rigs before or after sorting
        lighting_rigs = _get_rig_names_and_paths(self.__ext_id)
        if not bool(lighting_rigs):
            return

        ui.Separator("Light Rigs")

        index = 0
        any_rig_active = False
        for rig_name, rig_path in lighting_rigs:
            if not rig_name:
                carb.log_warn(f"Skipping rig '{rig_path}")

            this_rig_active = cur_value == rig_name
            any_rig_active = any_rig_active or this_rig_active

            # Create the menu item with transformed name and passes full-path to __set_lighting_mode
            mi = SelectableMenuItem(rig_name, delegate=ViewportMenuDelegate(), checked=this_rig_active, **kwargs)
            setup_item_with_model(
                mi, lambda lr=rig_name, mi=mi, *_: self.__set_lighting_mode(lr, menu_context, mi), rig_name
            )
            index = index + 1

        # Just to make sure it's not being used/captured unknowingly
        mi = None

        ui.Separator()

        kwargs = {}
        if carb.settings.get_settings().get("/exts/omni.kit.viewport.menubar.lighting/autoLightRig/toggleImmediate"):
            kwargs["triggered_fn"] = partial(self.__auto_rig_disabled, menu_context)

        SelectableMenuItem(
            "Use auto light rig on startup",
            SettingModel("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled"),
            tooltip="If no lights are present when you open a stage, use a default lighting rig.",
            **kwargs,
        )

        ui.Separator()

        menu_context.import_item = ui.MenuItem(
            "Add Current Light Rig to Stage",
            delegate=ViewportMenuDelegate(icon_name="Add"),
            triggered_fn=partial(self.__import_current_light_rig, menu_context),
            enabled=any_rig_active,
            hide_on_click=False,
        )

    def __get_menu_context(self, factory_args: dict) -> Optional[MenuContext]:
        """Return the MenuContext of a Viewport, or None when it has no menu (built yet or anymore)"""
        viewport_api = factory_args.get("viewport_api") if factory_args else None
        if viewport_api is None:
            return None
        return self.__menu_contexts.get(viewport_api.id)

    def get_display_status(self, factory_args: dict) -> MenuDisplayStatus:
        context = self.__get_menu_context(factory_args)
        if context and context.delegate.text_visible:
            return MenuDisplayStatus.LABEL
        else:
            return MenuDisplayStatus.MIN

    def get_require_size(self, factory_args: dict, expand: bool = False) -> float:
        context = self.__get_menu_context(factory_args)
        if context is None:
            return 0
        display_status = self.get_display_status(factory_args)
        if expand and (display_status != MenuDisplayStatus.LABEL):
            return context.delegate.text_size
        return 0

    def expand(self, factory_args: dict) -> None:
        context = self.__get_menu_context(factory_args)
        if (context is None) or context.delegate.text_visible:
            return

        context.delegate.text_visible = True
        if context.root_menu:
            context.root_menu.invalidate()

    def can_contract(self, factory_args: dict) -> bool:
        display_status = self.get_display_status(factory_args)
        return display_status == MenuDisplayStatus.LABEL

    def contract(self, factory_args: dict) -> bool:
        context = self.__get_menu_context(factory_args)
        if context is None:
            return False
        display_status = self.get_display_status(factory_args)
        if display_status == MenuDisplayStatus.LABEL:
            context.delegate.text_visible = False
            if context.root_menu:
                context.root_menu.invalidate()
            return True
        return False

    def __auto_rig_disabled(self, menu_context: MenuContext, *args, **kwargs):
        # Setting model will have handled the setting update, revert to stage lights
        viewport_api = menu_context.viewport_api
        settings = carb.settings.get_settings()
        setting_key = "/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled"
        cur_value = not bool(settings.get(setting_key))
        settings.set(setting_key, cur_value)

        viewport_api = menu_context.viewport_api
        usd_context = viewport_api.usd_context
        light_mode_setting_key = _make_light_mode_setting_key(usd_context)
        lighting_mode = settings.get(light_mode_setting_key) or ""
        if cur_value:
            if lighting_mode == "":
                self.__on_stage_open(menu_context, viewport_api.usd_context_name, usd_context)
        else:
            if (lighting_mode != "") and (lighting_mode != "off") and (lighting_mode != "camera"):
                _set_lighting_mode(lighting_mode="", viewport=viewport_api)

    def __import_current_light_rig(self, menu_context: MenuContext, *args, **kwargs):
        viewport_api = menu_context.viewport_api
        _import_light_rig(usd_context_name=viewport_api.usd_context_name)
        _set_lighting_mode(lighting_mode="", viewport=viewport_api)

    def __recheck_all_items(self, usd_context, value: str):
        import_enabled = value != "" and value != "camera" and value != "off" and value != "stage"
        if value == "":
            value = "stage"
        for viewport_api_id, other_menu_context in self.__menu_contexts.items():
            if other_menu_context.viewport_api.usd_context == usd_context:
                for other_menu_item in other_menu_context.menu_items:
                    checked = other_menu_item.name == value
                    other_menu_item.checked = checked
                    if checked:
                        other_menu_context.root_menu.text = other_menu_item.text
                import_item = other_menu_context.import_item
                if import_item:
                    import_item.enabled = import_enabled

    def __recheck_all_items_async(self, usd_context: omni.usd.UsdContext, value: str):
        async def recheck_all_items(self, usd_context: omni.usd.UsdContext, value: str):
            import omni.kit.app

            await omni.kit.app.get_app().next_update_async()
            self.__recheck_all_items(usd_context, value)

        import asyncio

        asyncio.ensure_future(recheck_all_items(self, usd_context, value))

    def __set_lighting_mode(
        self, lighting_mode: Union[str, int], menu_context: MenuContext, menu_item: Optional[ui.MenuItem] = None
    ):
        # XXX: Need this to fight omni.ui.MenuItem auto-toggle
        if menu_item:
            self.__recheck_all_items_async(menu_context.viewport_api.usd_context, lighting_mode)

        _set_lighting_mode(lighting_mode=lighting_mode, viewport=menu_context.viewport_api)

    def __set_stage_lighting_mode(self, menu_context: MenuContext):
        settings = carb.settings.get_settings()
        if not settings.get("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled"):
            return

        rig_applied, lighting_mode = self.__get_lighting_mode(menu_context.viewport_api.usd_context, settings)
        if rig_applied:
            self.__set_lighting_mode("", menu_context)

    def __on_mode_changed(self, usd_context: omni.usd.UsdContext, value: str):
        self.__recheck_all_items_async(usd_context, value)

    # Keep /rtx/useViewLightingMode and the lighting-mode menu in sync
    # Since this setting is global, we adjust all menus everywhere
    def __view_light_changed(self, item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return

        settings = carb.settings.get_settings()
        light_mode_on = settings.get("/rtx/useViewLightingMode")
        reset_lightin_mode = {}
        # Gather all the per-context lighting modes and possibly reset to a value that better represents
        # the /rtx/useViewLightingMode being enabled
        for viewport_api_id, menu_context in self.__menu_contexts.items():
            usd_context = menu_context.viewport_api.usd_context
            ctx_key = _make_light_mode_setting_key(usd_context)
            # If already have data for this key, move on
            if ctx_key in reset_lightin_mode:
                continue
            # Get the current value of the lighting-mode
            lighting_mode = settings.get(ctx_key)
            if light_mode_on and lighting_mode != "camera":
                reset_lightin_mode[usd_context] = "camera"
                # useViewLightingMode ON but not in camera mode, move to camera
            elif (not light_mode_on) and (lighting_mode == "camera"):
                # useViewLightingMode OFF but in camera mode, move to none/stage
                reset_lightin_mode[usd_context] = ""

        # Set all the per-context lighting modes
        for usd_context, lighting_mode in reset_lightin_mode.items():
            _set_lighting_mode(lighting_mode=lighting_mode, usd_context=usd_context)

    def __post_notification(self, msg: str, warn: bool = False):
        duration = carb.settings.get_settings().get("/exts/omni.kit.viewport.menubar.lighting/notificationDuration")
        if duration > 0:
            try:
                from omni.kit.notification_manager import NotificationStatus, post_notification

                post_notification(
                    msg, duration=duration, status=NotificationStatus.WARNING if warn else NotificationStatus.INFO
                )
                return
            except ImportError:
                pass
            try:
                from omni.kit.viewport.utility import get_active_viewport_window, post_viewport_message

                viewport_window = get_active_viewport_window()
                if viewport_window:
                    post_viewport_message(viewport_window, msg, duration)
                    return
            except ImportError:
                pass

        carb.log_warn(msg)

    def __get_is_rig_and_lighting_mode(self, lighting_mode: str):
        rig_applied = bool(
            lighting_mode and (lighting_mode != "off") and (lighting_mode != "camera") and (lighting_mode != "stage")
        )
        return rig_applied, lighting_mode

    def __get_lighting_mode(self, usd_context: omni.usd.UsdContext, settings: carb.settings.ISettings):
        light_mode_setting_key = _make_light_mode_setting_key(usd_context)
        lighting_mode = settings.get(light_mode_setting_key) or ""
        return self.__get_is_rig_and_lighting_mode(lighting_mode)

    async def __adjust_render_settings(
        self,
        adjust_rules: List[str],
        has_any_light: Optional[bool],
        search_from_dflt: bool,
        usd_context: omni.usd.UsdContext,
    ):
        stage = usd_context.get_stage()
        if not stage:
            return

        # import omni.kit.app
        # app = omni.kit.app.get_app()
        # for _ in range(1):
        #     await app.next_update_async()

        settings = carb.settings.get_settings()

        if "force" not in adjust_rules:

            def is_empty_after_remove(item: str):
                adjust_rules.remove(item)
                return len(adjust_rules) == 0

            # If the setting is already 0, then do nothing
            # amb_light_intensity = settings.get("/rtx/sceneDb/ambientLightIntensity")
            # if amb_light_intensity == 0:
            #     return False

            # Test against rigapplied in settings, and whether a rig was actually applied
            if "rigapplied" in adjust_rules:
                # Figure out if a rig was applied
                light_mode_setting_key = _make_light_mode_setting_key(usd_context)
                lighting_mode = settings.get(light_mode_setting_key) or ""
                rig_applied, _ = self.__get_lighting_mode(usd_context, settings)
                # If it wasn't applied and rigapplied is in rules, then do nothing
                if (not rig_applied) and is_empty_after_remove("rigapplied"):
                    return False

            # If rules mode has nolights and there are in fact stage lights, do nothing
            if "nolights" in adjust_rules:
                # May need to scan for lights now if not done before
                if has_any_light is None:
                    has_any_light = stage_has_api_type(stage, UsdLux.LightAPI, search_from_dflt)
                # If stage has lights and nolights in rule, do nothing
                if has_any_light and is_empty_after_remove("nolights"):
                    return False

            render_settings = stage.GetMetadataByDictKey("customLayerData", "renderSettings")
            if render_settings is not None:
                # adjust_rules mode is newscene and renderSettings existed, then its not a new scene, do nothing
                if "newscene" in adjust_rules and is_empty_after_remove("newscene"):
                    return False
            else:
                render_settings = {}

            amb_light_intensity = render_settings.get("rtx:sceneDb:ambientLightIntensity", None)
            # If ambientAdjust is notset and there is a user saved value in the dict, do nothing
            if "notset" in adjust_rules and (amb_light_intensity is not None):
                if is_empty_after_remove("notset"):
                    return False
            elif amb_light_intensity is None:
                # Wan't set, put it to default of 1 to make check below easier to read
                amb_light_intensity = 1

            # If ambientAdjust is notdefault and there is a user saved value other than 1, do nothing
            if "notdefault" in adjust_rules and (amb_light_intensity != 1):
                if is_empty_after_remove("notdefault"):
                    return False

        if len(adjust_rules) == 0:
            return False

        msg = []
        cur_amb = settings.get("/rtx/sceneDb/ambientLightIntensity")
        cur_gi = settings.get("/rtx/indirectDiffuse/enabled")
        if cur_amb != 0:
            settings.set("/rtx/sceneDb/ambientLightIntensity", 0)
            msg.append(f"RTX ambientLightIntensity of {amb_light_intensity} was reset to 0.")
        if cur_gi != True:
            settings.set("/rtx/indirectDiffuse/enabled", True)
            msg.append("Indirect Diffuse GI was enabled.")
        if msg:
            self.__post_notification("\n".join(msg))

    def __run_render_settings_adjustments(
        self,
        menu_context: MenuContext,
        search_from_dflt: bool,
        usd_context: omni.usd.UsdContext,
        settings: carb.settings.ISettings,
    ):
        adjust_rules = settings.get("/exts/omni.kit.viewport.menubar.lighting/ambientAdjust") or ""
        adjust_rules = [a.lower().lstrip().rstrip() for a in adjust_rules.split(",")]
        # If setting is disabled do nothing at all
        if not adjust_rules or (adjust_rules[0] == "" and len(adjust_rules) == 1):
            return

        import asyncio

        has_any_light, menu_context.has_any_light = menu_context.has_any_light, None
        asyncio.ensure_future(self.__adjust_render_settings(adjust_rules, has_any_light, search_from_dflt, usd_context))

    def __on_stage_open(
        self, menu_context: MenuContext, usd_context_name: str, usd_context: omni.usd.UsdContext, prev_mode: str
    ):
        stage = usd_context.get_stage()
        if not stage:
            return

        end_activity = False
        try:
            import omni.activity.core as activity_core

            stage_opened_activity = f"Stage|Opened|Viewport Menubar Lighting"
            activity_core.began(stage_opened_activity)
            end_activity = True
        except ImportError:
            pass

        settings = carb.settings.get_settings()
        search_from_dflt = settings.get(
            "/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/searchFromDefaultPrim"
        )

        lighting_mode = ""
        ignore_pattern = settings.get("/exts/omni.kit.viewport.menubar.lighting/defaultRigIgnorePattern")
        if ignore_pattern:
            import re

            if re.match(ignore_pattern, stage.GetRootLayer().identifier) is not None:
                lighting_mode = "stage"

        auto_rig_enbled = settings.get("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled")
        if auto_rig_enbled:
            # Check if the opened stage has 0 lights, and if so, apply the default-rig
            has_any_light = stage_has_api_type(stage, UsdLux.LightAPI, search_from_dflt)
            menu_context.has_any_light = has_any_light
            if (lighting_mode == "") and (not has_any_light):
                # Convert the defaultRig setting to an index, and error if can't convert to int or not ""
                # Note rig_index != "" fallthrough for defaultRig="" which will default to stage-lighting
                rig_applied, lighting_mode = self.__get_is_rig_and_lighting_mode(prev_mode)
                prserve_active_rig = bool(settings.get("/exts/omni.kit.viewport.menubar.lighting/preserveActiveRig"))
                if (not rig_applied) or (lighting_mode is None) or (not prserve_active_rig):
                    lighting_mode = settings.get("/exts/omni.kit.viewport.menubar.lighting/defaultRig")
                # Early exit if nothing can be done
                if lighting_mode is None:
                    self.__post_notification("No lights found in stage, but no default light rig is set.")
                    if end_activity:
                        omni.activity.core.ended(stage_opened_activity)
                    return
        else:
            light_mode_setting_key = _make_light_mode_setting_key(usd_context)
            lighting_mode = settings.get(light_mode_setting_key) or ""
            # When light-mode is camera, go back to stage lights on open
            if lighting_mode == "camera":
                lighting_mode = ""

        success, result = omni.kit.commands.execute(
            "SetLightingMenuModeCommand", lighting_mode=lighting_mode, usd_context_name=usd_context_name
        )
        if success:
            lighting_mode, prev_mode = result

        if auto_rig_enbled:
            if not success:
                self.__post_notification(
                    f"No lights found in stage, but couldn't apply default lighting: '{lighting_mode}'."
                    + "Falling back to Stage lighting.",
                    True,
                )
                _set_lighting_mode("", usd_context=usd_context)
            elif lighting_mode != "":
                self.__post_notification(
                    f"No lights found in stage, applying lighting: '{lighting_mode}'." + "\nThis action is undoable."
                )
        elif lighting_mode:
            self.__post_notification(
                f"Auto light rig is disabled, but '{lighting_mode.capitalize()}' was applied since it is selected."
            )

        self.__run_render_settings_adjustments(menu_context, search_from_dflt, usd_context, settings)
        if end_activity:
            omni.activity.core.ended(stage_opened_activity)

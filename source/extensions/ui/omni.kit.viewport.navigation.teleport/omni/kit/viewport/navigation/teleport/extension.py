import weakref

import carb.eventdispatcher
import carb.input
import carb.settings
import carb.tokens
import omni.ext
import omni.ui as ui
import omni.usd
from omni.kit.tool.teleport import Teleport
from omni.kit.viewport.navigation.core import (
    IMAGE_SIZE,
    NAVIGATION_TOOL_OPERATION_ACTIVE,
    ViewportNavigationButton,
    get_navigation_bar,
)

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.teleport/"


class Extension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        self._show_arc = False
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        navigaiton_bar = get_navigation_bar()

        self._settings = carb.settings.get_settings()

        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")
        true_image = icon_path + "navTeleport_active_dark.svg"
        false_image = icon_path + "navTeleport_dark.svg"
        order_setting = SETTINGS_ROOT + "order"
        visible_setting = SETTINGS_ROOT + "visible"
        name = "teleport"
        style = {
            "Navigation.Button.Image::" + f"{name}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name}:checked": {"image_url": f"{true_image}"},
        }
        with navigaiton_bar:
            self._button = ViewportNavigationButton(
                name,
                IMAGE_SIZE,
                visible_setting_path=visible_setting,
                order_setting_path=order_setting,
                clicked_fn=self._on_click,
                build_tooltip_fn=self._build_teleport_tooltip,
                style=style,
            )
            self._button.set_state(False)

        self._teleport = Teleport.get_instance()

        # FIXME: This extension only works on the default UsdContext
        usd_context = omni.usd.get_context()
        event_dispatcher = carb.eventdispatcher.get_eventdispatcher()
        self._stage_subs = (
            event_dispatcher.observe_event(
                observer_name="omni.kit.viewport.navigation.teleport.StageOpened",
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
                on_event=lambda _: self._teleport.set_active(False),
            ),
            event_dispatcher.observe_event(
                observer_name="omni.kit.viewport.navigation.teleport.StageClosing",
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.CLOSING),
                on_event=lambda _: self._teleport.set_active(False),
            ),
        )

        self._input = carb.input.acquire_input_interface()
        self._input_sub_id = self._input.subscribe_to_input_events(self._on_input_event, order=0)
        self._active_operation_setting_sub = omni.kit.app.SettingChangeSubscription(
            NAVIGATION_TOOL_OPERATION_ACTIVE, lambda *_: self._on_operation_active_changed()
        )

        def on_bar_hover_changed(item, evt_type, _self=weakref.ref(self)):
            if self := _self():
                active_operation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
                if active_operation == "teleport":
                    self._teleport.set_active(not item.get_dict())

        self._hover_changed_evt = self._settings.subscribe_to_node_change_events(
            "/exts/omni.kit.viewport.navigation.core/hovered", on_bar_hover_changed
        )

    def _on_operation_active_changed(self):
        active_operation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
        if active_operation == "teleport":
            self._button.set_state(True)
            self._teleport.set_active(True)
        else:
            self._button.set_state(False)
            self._teleport.set_active(False)

    def _build_teleport_tooltip(self):
        TOOLTIP_SIDE_SPACE = 5
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label(
                    "Left click on viewport to teleport instantly to that location\n"
                    + "upon on mouse release. Left click, and drag will alter the\n"
                    + "orientation that you face after you've been teleported.\n"
                    + "This is indicated by a pointer on the ring of the teleport gizmo.\n"
                    + "press U key to switch beam visibility on/off",
                    alignment=ui.Alignment.CENTER,
                    name="shortcut",
                )
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (343, 69)

    def _on_input_event(self, event: carb.input.InputEvent, *_):
        if event.deviceType == carb.input.DeviceType.KEYBOARD:
            if self._settings.get_as_bool("/omni/kit/hotkey/core/hotkeys_enabled"):
                if event.event.input == carb.input.KeyboardInput.Y:
                    if event.event.type == carb.input.KeyboardEventType.KEY_PRESS:
                        self._set_operation("teleport")
                    if event.event.type == carb.input.KeyboardEventType.KEY_RELEASE:
                        self._set_operation("none")
            active_operation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
            if active_operation == "teleport":
                if event.event.input == carb.input.KeyboardInput.U:
                    if event.event.type == carb.input.KeyboardEventType.KEY_PRESS:
                        if self._teleport:
                            self._show_arc = not self._show_arc
                            self._teleport.show_arc(show=self._show_arc)
        return True

    def _set_operation(self, op):
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, op)

    def _on_click(self, *_):
        active_operation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
        if active_operation == "teleport":
            self._set_operation("none")
        else:
            self._set_operation("teleport")

    def on_shutdown(self):
        self._button.destroy()
        self._button = None
        self._show_arc = False
        self._stage_subs = None

        self._active_operation_setting_sub = None
        if self._hover_changed_evt is not None:
            self._settings.unsubscribe_to_change_events(self._hover_changed_evt)
            self._hover_changed_evt = None

        if self._input_sub_id is not None:
            self._input.unsubscribe_to_input_events(self._input_sub_id)
            self._input_sub_id = None

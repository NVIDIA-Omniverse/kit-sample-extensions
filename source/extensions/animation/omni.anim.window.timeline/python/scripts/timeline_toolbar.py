import asyncio
from functools import partial
from typing import List

import carb

# import carb.eventdispatcher
import carb.settings
import carb.tokens
import omni.kit.actions.core
import omni.kit.app
import omni.kit.menu.utils
import omni.kit.ui
import omni.timeline
from omni import ui
from omni.kit.menu.utils import MenuItemDescription

from .live_session import TimelineLiveSession
from .timeline_control import TimelineControlWidget
from .timeline_widget import TimelineWidget


class TimelineToolbar:
    WINDOW_NAME = "Timeline toolbar"
    MENU_PATH = "Window/Animation/Timeline"
    SETTINGS_SHOW_TIMELINE = "/exts/omni.anim.window.timeline/show"

    def __init__(self, ext_id):
        self._ext_id = ext_id
        self._toolbar = None
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_widget = None
        self._control_widget = None
        # self._last_width = 0
        self._moving = False
        self._start_y = 0

        self._docked_window = None
        self._play_hotkey = None
        self._pre_hotkey = None
        self._next_hotkey = None

        self._live_session = TimelineLiveSession()

        self._toolbar = ui.ToolBar(
            self.WINDOW_NAME,
            padding_x=0,
            padding_y=0,
            noTabBar=False,  # OM-91660: show the triangle on left-top again
            dockPreference=ui.DockPreference.LEFT_BOTTOM,
        )

        if ui.Workspace.get_window("DockSpace"):
            self._toolbar.deferred_dock_in("DockSpace")

        self._build_ui()

        ui.Workspace.set_show_window_fn(TimelineToolbar.WINDOW_NAME, partial(self._show, None))

        # Register Window/Animation/Timeline via omni.kit.menu.utils
        self._menu_items = [
            MenuItemDescription(
                name="Animation",
                sub_menu=[
                    MenuItemDescription(
                        name="Timeline",
                        ticked=True,
                        ticked_fn=self._on_ticked_fn,
                        onclick_fn=self._on_click_fn,
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_items, "Window")

        self._toolbar.set_visibility_changed_fn(self._on_visibility_changed)
        self._toolbar.set_width_changed_fn(self._on_width_changed)
        self._task = asyncio.ensure_future(self.__wait_for_the_viewport())

        # Actions and HotKeys
        self._action_registry = None
        self._hotkey_registry = None
        self._hotkey_filter_by_window = None
        self._build_actions()
        # subscribe to omni.kit.hotkeys.core on/off
        ext_manager = omni.kit.app.get_app().get_extension_manager()
        # Please note that, upon subscription (when the next line is executed), if the ext is on, on_enable_fn func will be called immediately.
        # However, if it's off, on_disable_fn func will NOT be called immediately.
        # So you don't have to exam the extension state explicitly for the CURRENT time. Instead, you can assume it's off.
        self.hooks = ext_manager.subscribe_to_extension_enable(
            lambda _: self._build_hotkeys(),
            lambda _: self._clear_hotkeys(),
            ext_name="omni.kit.hotkeys.core",
            hook_name="omni.anim.window.timeline-hotkeys",
        )

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._task:
            self._task.cancel()
            self._task = None

        ui.Workspace.set_show_window_fn(TimelineToolbar.WINDOW_NAME, None)

        if self._toolbar:
            self._toolbar.frame.clear()
            self._toolbar = None
        self._timeline = None
        if self._control_widget:
            self._control_widget.destroy()
            self._control_widget = None
        if self._timeline_widget:
            self._timeline_widget.destroy()
            self._timeline_widget = None
        # Unregister menu items
        try:
            if hasattr(self, "_menu_items") and self._menu_items:
                omni.kit.menu.utils.remove_menu_items(self._menu_items, "Window")
        finally:
            self._menu_items = None
        self._menu = None
        self._update_sub = None
        self._live_session = None

        # De-register all hotkeys & actions
        self._clear_hotkeys()
        if self._action_registry:
            self._action_registry.deregister_all_actions_for_extension("omni.anim.window.timeline")

    async def __wait_for_the_viewport(self):
        await omni.kit.app.get_app().next_update_async()
        if not ui.Workspace.get_window("Viewport"):
            self._task = asyncio.ensure_future(self.__wait_for_the_viewport())
        else:
            self._task = asyncio.ensure_future(self.__viewport_ready())

    async def __viewport_ready(self):
        self._task = None
        # here need wait a more frame for viewport window finish init
        await omni.kit.app.get_app().next_update_async()

        settings = carb.settings.get_settings()
        settings.set_default_bool(self.SETTINGS_SHOW_TIMELINE, True)
        show = settings.get_as_bool(self.SETTINGS_SHOW_TIMELINE)
        # force trigger
        self._show(self.MENU_PATH, not show)
        await omni.kit.app.get_app().next_update_async()
        self._show(self.MENU_PATH, show)

        # self._update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
        #     event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
        #     on_event=lambda _: self._on_update(),
        #     observer_name="timeline_toolbar:update",
        # )

    def _show(self, menu, value):
        self._toolbar.visible = value
        if value:
            # docking to 'dockspace' will fail on debug mode
            if carb.tokens.get_tokens_interface().resolve("${config}") == "debug":
                self._docked_window = ui.Workspace.get_window("Viewport")
            else:
                self._docked_window = ui.Workspace.get_window("DockSpace")
            if self._docked_window is not None:
                self._toolbar.dock_in(self._docked_window, ui.DockPosition.BOTTOM)
                # self._last_width = self._docked_window.width
            self._timeline_widget.resize_width()

    def _on_ticked_fn(self):
        return self._toolbar.visible if self._toolbar else False

    def _on_click_fn(self):
        self._show(self.MENU_PATH, not self._toolbar.visible)

    def _build_ui(self):
        rec_style = {
            "Rectangle": {"background_color": 0x00000000, "margin": 0, "padding": 0},
            "Rectangle:hovered": {"background_color": 0xFFB07030},
        }

        with self._toolbar.frame:
            with ui.VStack():
                # ui.Toolbar don't support resize, use a rectangle to do it
                ui.Rectangle(
                    style=rec_style,
                    height=3,
                    mouse_pressed_fn=self._on_mouse_pressed,
                    mouse_moved_fn=self._on_mouse_moved,
                    mouse_released_fn=self._on_mouse_released,
                )

                with ui.HStack():
                    with ui.VStack(width=0, style={"padding": 2, "margin_height": 2, "margin_width": 0}):
                        ui.Button(
                            "",
                            width=0,
                            image_url="resources/icons/Close.png",
                            image_width=10,
                            image_height=10,
                            style={
                                "Button": {"background_color": 0x00606060},
                                "Button:hovered": {"background_color": 0xFF222222},
                            },
                            clicked_fn=lambda v=False: self._show(self.MENU_PATH, v),
                        )
                        with ui.HStack():
                            ui.Spacer()
                            line_style = {"color": 0xFF707070, "margin_width": 2, "margin_height": 0}
                            ui.Line(width=3, alignment=ui.Alignment.LEFT, style=line_style)
                            ui.Line(width=3, alignment=ui.Alignment.LEFT, style=line_style)
                            ui.Line(width=3, alignment=ui.Alignment.LEFT, style=line_style)
                            ui.Spacer()

                    self._timeline_widget = TimelineWidget(self._toolbar)
                    self._timeline_widget.set_live_session(self._live_session)
                    self._control_widget = TimelineControlWidget(self._timeline_widget)
                    self._control_widget.set_live_session(self._live_session)

    def _build_actions(self):
        ext_id = "omni.anim.window.timeline"
        self._action_registry = omni.kit.actions.core.get_action_registry()

        # Copy Key, Ctrl+C
        self._action_registry.register_action(
            ext_id, "copy_key", self._timeline_widget._on_copy_key, "Copy Key", "Copy Key"
        )
        # Paste Key, Ctrl+V
        self._action_registry.register_action(
            ext_id, "paste_key", self._timeline_widget._on_paste_key, "Paste Key", "Paste Key"
        )
        # Add Key, ALT+S, move the define in anim.curve
        # self._action_registry.register_action(ext_id, "add_key", self._timeline_widget._on_add_key, "Add Key", "Add Key")
        # Delete Key, Delete
        self._action_registry.register_action(
            ext_id, "delete_key", self._timeline_widget._on_delete_key, "Delete Key", "Delete Key"
        )
        # Previous Key, Alt+Left
        self._action_registry.register_action(
            ext_id,
            "previous_key",
            self._control_widget._on_button_previous_key_frame,
            "Previous Key",
            "Go to the previous key frame",
        )
        # Next Key, Alt+Right
        self._action_registry.register_action(
            ext_id, "next_key", self._control_widget._on_button_next_key_frame, "Next Key", "Go to the next key frame"
        )
        # Play/Pause, SPACE
        self._action_registry.register_action(
            ext_id, "play_pause", self._control_widget.on_button_play, "Play/Pause", "Toggle Play/Pause"
        )

        # Auto Key, Ctrl+S
        def _on_button_auto():
            self._control_widget._autoframe_btn.checked = not self._control_widget._autoframe_btn.checked
            self._control_widget._on_button_auto()

        self._action_registry.register_action(
            ext_id, "auto_key", _on_button_auto, "Auto Key (Toggle)", "Toggle Auto Key"
        )

        # The origin global hotkeys
        # Previous Frame, ALT+COMMA
        self._action_registry.register_action(
            ext_id,
            "previous_frame",
            self._control_widget.on_button_previous_frame,
            "Previous Frame",
            "Go to the previous frame",
        )
        # Next Frame, ALT+PERIOD
        self._action_registry.register_action(
            ext_id, "next_frame", self._control_widget.on_button_next_frame, "Next Frame", "Go to the next frame"
        )

    def _build_hotkeys(self):
        try:
            import omni.kit.hotkeys.core
        except ImportError:
            carb.log_warn("Failed to register hotkeys.")
            return

        ext_id = "omni.anim.window.timeline"
        self._hotkey_registry = omni.kit.hotkeys.core.get_hotkey_registry()
        self._hotkey_filter_by_window = omni.kit.hotkeys.core.filter.HotkeyFilter(windows=[self.WINDOW_NAME])

        # Copy Key, Ctrl+C
        self._hotkey_registry.register_hotkey(ext_id, "CTRL + C", ext_id, "copy_key", self._hotkey_filter_by_window)
        # Paste Key, Ctrl+V
        self._hotkey_registry.register_hotkey(ext_id, "CTRL + V", ext_id, "paste_key", self._hotkey_filter_by_window)
        # Add Key, ALT+S, move the define in anim.curve
        # self._hotkey_registry.register_hotkey(ext_id, "ALT + S", ext_id, "add_key", self._hotkey_filter_by_window)
        # Delete Key, Delete
        self._hotkey_registry.register_hotkey(ext_id, "DEL", ext_id, "delete_key", self._hotkey_filter_by_window)
        # Previous Key, Alt+Left
        self._hotkey_registry.register_hotkey(
            ext_id, "ALT + LEFT", ext_id, "previous_key", self._hotkey_filter_by_window
        )
        # Next Key, Alt+Right
        self._hotkey_registry.register_hotkey(ext_id, "ALT + RIGHT", ext_id, "next_key", self._hotkey_filter_by_window)
        # Play/Pause, SPACE, global - There is already an existing one
        # self._hotkey_registry.register_hotkey(ext_id, "SPACE", ext_id, "play_pause")
        # Auto Key, Ctrl+S
        self._hotkey_registry.register_hotkey(ext_id, "CTRL + S", ext_id, "auto_key", self._hotkey_filter_by_window)
        # The origin global hotkeys
        # Previous Frame, ALT+COMMA
        self._hotkey_registry.register_hotkey(ext_id, "ALT + COMMA", ext_id, "previous_frame")
        # Next Frame, ALT+PERIOD
        self._hotkey_registry.register_hotkey(ext_id, "ALT + PERIOD", ext_id, "next_frame")

    def _clear_hotkeys(self):
        if self._hotkey_registry:
            self._hotkey_registry.deregister_all_hotkeys_for_extension("omni.anim.window.timeline")
        self._hotkey_registry = None
        self._hotkey_filter_by_window = None

    def _on_visibility_changed(self, visible):
        omni.kit.menu.utils.refresh_menu_items("Window")

    # def _on_update(self, dt):
    #     if not self._toolbar.visible:
    #         return

    #     if self._docked_window is not None:
    #         if abs(self._last_width - self._docked_window.width) > 5:
    #             self._last_width = self._docked_window.width
    #             self._timeline_widget.resize()

    # Notice: used upper method because I'd seen toolbar flashing(resize forever) issue.
    # but looks can't reproduce it now, so use this again to fix om-48227
    def _on_width_changed(self, changed):
        self._timeline_widget.resize_width()

    def _on_mouse_pressed(self, x, y, button_index, mod):
        if button_index == 0:
            self._moving = True
            self._last_y = y

    def _on_mouse_moved(self, x: float, y: float, m: int, pressed: bool):
        if self._moving:
            delta = self._last_y - y
            self._last_y = y
            self._timeline_widget.resize_height(delta)

    def _on_mouse_released(self, x, y, button_index, mod):
        self._moving = False

    def get_FPS_list(self) -> List[str]:
        if self._control_widget:
            return self._control_widget.get_FPS_list()
        else:
            return []

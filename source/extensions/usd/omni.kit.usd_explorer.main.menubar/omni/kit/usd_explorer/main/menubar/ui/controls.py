import asyncio
from typing import Any, Callable, Dict, Optional, Tuple

import carb
import carb.events
import carb.settings
import omni.kit.app
import omni.kit.notification_manager as nm
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.usd_explorer.render import get_render_preset_instance
from omni.kit.usd_explorer.tooltip import set_usd_explorer_tooltip
from omni.kit.viewport.utility import disable_selection, get_active_viewport
from omni.kit.widgets.custom import COLORS, DarkColors, FontSize  # type: ignore
from omni.ui import color

MENUBAR_HEIGHT = 20
SETTINGS_APPLICATION_MODE_PATH = "/app/application_mode"
SETTINGS_INCLUDE_PRESENT_MODE_PATH = "/exts/omni.kit.usd_explorer.main.menubar/include_present_mode"
SETTINGS_INCLUDE_MODIFY_MODE_PATH = "/exts/omni.kit.usd_explorer.main.menubar/include_modify_mode"
SETTINGS_INCLUDE_APPROVE_MODE_PATH = "/exts/omni.kit.usd_explorer.main.menubar/include_approve_mode"
SETTINGS_SWITCH_TO_PRESENT_ON_OPEN = "/exts/omni.kit.usd_explorer.main.menubar/switch_to_present_on_open"
MAX_MODE_COUNT = 4
RENDERER_CHANGED_EVT = carb.events.type_from_string("render_settings.renderer.CHANGED")
RENDERER_CHANGED_EVENT_NAME = "render_settings.renderer.CHANGED"
RENDERER_EVT_PAYLOAD_KEY = "renderer"


class LabelButton:
    txt_color = color.shade(DarkColors.Text, light=DarkColors.TextDisabled)
    STYLE = {
        "Rectangle::label_button": {
            "background_color": COLORS.TRANSPARENT,
            "border_width": 1,
            "border_color": COLORS.TRANSPARENT,
            "border_radius": 3.0,
        },
        "Rectangle::label_button:hovered": {
            "background_color": COLORS.TRANSPARENT,
            "border_width": 1,
            "border_color": COLORS.TEXT_SELECTED,
            "border_radius": 3.0,
        },
        "Label::label_button": {
            "color": txt_color,
            "background_color": COLORS.TRANSPARENT,
            "font_size": FontSize.XXLarge,
        },
        "Label::label_button:selected": {"color": COLORS.TEXT_SELECTED},
    }

    @property
    def screen_position(self) -> Tuple[float, float]:
        return (self._rect.screen_position_x, self._rect.screen_position_y)

    def __init__(
        self, text: str, on_clicked_fn: Optional[Callable] = None, tooltip: str = "", identifier: str = ""
    ) -> None:
        self._on_clicked_fn = on_clicked_fn
        self._id = text
        self._selected = False
        with ui.ZStack(width=0, height=MENUBAR_HEIGHT, spacing=0, style=self.STYLE):
            with ui.Placer(offset_x=0, offset_y=0):
                self._rect = ui.Rectangle(name="label_button", identifier=identifier)
            with ui.Placer(offset_x=0, offset_y=0):
                self._label = ui.Label(text.title(), name="label_button")
            self._rect.set_mouse_pressed_fn(lambda x, y, btn, a: self._on_mouse_pressed())
            if tooltip:
                set_usd_explorer_tooltip(self._rect, tooltip)

    def set_mouse_pressed_fn(self, on_clicked_fn: Optional[Callable]) -> None:
        self._on_clicked_fn = on_clicked_fn

    def _on_mouse_pressed(self) -> None:
        if self._on_clicked_fn:
            self._on_clicked_fn(self._id)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self._label.selected = value


class TabedGroup:
    def __init__(self) -> None:
        self._selected = ""
        self._list: Dict[str, LabelButton] = {}

    @property
    def children(self) -> Dict[str, LabelButton]:
        return self._list

    def add_child(self, name: str, child: LabelButton, selected: bool = False) -> None:
        self._list[name] = child
        if selected:
            self.select(name)
        else:
            child.selected = False

    def select(self, name: str) -> None:
        if self._selected:
            self._list[self._selected].selected = False
            self._selected = ""
        if name and name in self._list:
            self._list[name].selected = True
            self._selected = name

    def get_selected(self) -> str:
        return self._selected


class ThickSeparator:
    STYLE = {"Line::separator": {"color": COLORS.LINE_SEPARATOR_THICK, "border_width": 1}}

    def __init__(self) -> None:
        with ui.VStack(width=0, height=24, style=self.STYLE):
            ui.Spacer()
            ui.Line(name="separator", width=1, height=12, alignment=ui.Alignment.LEFT)
            ui.Spacer()


class RenderModeControl:  # pragma: no cover -- test framework is not mature enough to test this.
    def __init__(self) -> None:
        self._settings = carb.settings.get_settings()
        self._render_preset = get_render_preset_instance()

        self._renderer_active_key = "/renderer/active"
        self._render_mode_key = "/rtx/rendermode"
        self._iray_render_mode_key = "/rtx/iray/rendermode"
        self._render_modes = ("draft", "preview", "photo")
        self._render_values = ("RaytracedLighting", "PathTracing", "iray")
        self._render_dict = dict(zip(self._render_modes, self._render_values))
        self._render_buttons = TabedGroup()
        omni.kit.app.register_event_alias(RENDERER_CHANGED_EVT, RENDERER_CHANGED_EVENT_NAME)
        self._renderer_changed_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.usd_explorer.main.menubar:RenderModeControl",
            event_name=RENDERER_CHANGED_EVENT_NAME,
            on_event=self._on_render_mode_changed_outside,
        )

        self._renderer_to_preset = {
            "real-time": self._render_modes[0],
            "interactive (path tracing)": self._render_modes[1],
            "accurate (iray)": self._render_modes[2],
        }

        self._preset_to_engine_data = {
            self._render_modes[0]: ("rtx", self._render_values[0]),
            self._render_modes[1]: ("rtx", self._render_values[1]),
            self._render_modes[-1]: (self._render_values[-1], self._render_values[-1]),
        }

        ui.Spacer(width=5)
        with ui.VStack(width=120, height=0):
            with ui.HStack(spacing=5, height=0):
                ui.Spacer()
                self.build_buttons()

        self._changing_render_mode = False
        self._current_render_mode = self._render_modes[0]
        self._render_buttons.select(self._current_render_mode)
        self._render_preset.update_menu_bar(self)

    # singleton model, to ensure set once , use in everywhere
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @property
    def button_group(self) -> TabedGroup:
        return self._render_buttons

    def build_buttons(self):
        tooltips = [
            "Render the viewport with the Real-Time renderer.",
            "Render the viewport with the Interactive (Path Tracing) renderer.",
            "Render the viewport with the Accurate (Iray) renderer.",
        ]
        for i, render in enumerate(self._render_modes):
            with ui.ZStack(width=0):
                ui.Spacer()
                label_button = LabelButton(
                    render,
                    self.set_render,
                    tooltip=f"tname:{tooltips[i]}",
                    identifier=f"_render_mode_control_{render}_btn",
                )
                ui.Spacer()
            self._render_buttons.add_child(render, label_button)

            ui.Spacer(width=2)
            if render == self._render_modes[-1]:
                continue
            ThickSeparator()
            ui.Spacer(width=2)

    def _on_render_mode_changed_outside(self, event):
        # OM-81967: don't allow to reload render mode except stage loading.
        if self._changing_render_mode:
            return

        renderer = event[RENDERER_EVT_PAYLOAD_KEY] or self._render_modes[0]
        new_mode = self._renderer_to_preset.get(renderer.lower(), self._render_modes[0])
        self._render_buttons.select(new_mode)

    def _set_iray(self, render_type: str) -> None:
        self._render_buttons.select(render_type)
        self._settings.set(self._render_mode_key, self._render_dict[render_type])
        iray_key = self._render_values[-1] if render_type.lower() == self._render_modes[-1] else ""
        self._settings.set(self._iray_render_mode_key, iray_key)
        self._switch_viewport_hydra_engine(render_type)
        self._current_render_mode = render_type
        self._render_preset.set_value(render_type)

    def _switch_viewport_hydra_engine(self, render_type: str) -> None:
        viewport_api = get_active_viewport()
        if viewport_api:
            # render_type = "draft", "preview", or "photo"
            # need to map those to "RayracedLighting", "PathTracing", and "iray"
            engine_data = self._preset_to_engine_data.get(render_type, ("rtx", "RaytracedLighting"))
            viewport_api.set_hd_engine(*engine_data)

    def set_render(self, render_type: str) -> None:
        self._changing_render_mode = True
        if render_type in self._render_dict:
            # OM-100908 Warn user if switching to Photo / Iray
            if render_type.lower() == self._render_modes[-1]:
                message = "Switching to the Iray renderer will consume large amounts of system resources and affect application performance.\n\nContinue?"
                buttons = [
                    nm.NotificationButtonInfo("OK", lambda: self._set_iray(render_type)),
                    nm.NotificationButtonInfo("Cancel", None),
                ]
                nm.post_notification(
                    message, status=nm.NotificationStatus.INFO, hide_after_timeout=False, button_infos=buttons
                )
            else:
                self._render_buttons.select(render_type)
                # Renderer
                self._settings.set(self._render_mode_key, self._render_dict[render_type])
                self._switch_viewport_hydra_engine(render_type)
                self._current_render_mode = render_type
                self._render_preset.set_value(render_type)
        self._changing_render_mode = False

    # OM-39605: should also deal with custom render type
    def get_render(self):
        render_type = self._render_buttons.get_selected()
        if not render_type:
            return self._render_preset.get_current_render()
        return render_type


class ApplicationModeControl:
    __selection_disabler = None
    __selection_update_requested = False

    @classmethod
    async def async_update_selection_state(cls, frame_delay: int = 1):
        if cls.__selection_update_requested is not None:
            for _ in range(frame_delay):
                await omni.kit.app.get_app().next_update_async()
            cls.__selection_update_requested = False
            mode = carb.settings.get_settings().get_as_string(SETTINGS_APPLICATION_MODE_PATH)
            if mode.lower() in ("review", "present"):
                omni.usd.get_context().get_selection().clear_selected_prim_paths()
                if cls.__selection_disabler is None and cls._instance:
                    cls.__selection_disabler = disable_selection(get_active_viewport())
            elif cls.__selection_disabler is not None:
                cls.__selection_disabler = None

    @classmethod
    def request_update_selection_state(cls):
        if cls.__selection_update_requested is not None:
            if not cls.__selection_update_requested:
                cls.__selection_update_requested = True
                asyncio.ensure_future(cls.async_update_selection_state())

    @classmethod
    def shutdown(cls):
        cls.__selection_update_requested = None
        cls.__selection_disabler = None
        cls._instance = None

    def __init__(self) -> None:
        self._settings = carb.settings.get_settings()
        self._modes = ["review"]
        if self._settings.get_as_bool(SETTINGS_INCLUDE_PRESENT_MODE_PATH):
            self._modes.insert(0, "present")
        if self._settings.get_as_bool(SETTINGS_INCLUDE_MODIFY_MODE_PATH):
            self._modes.append("layout")
        if self._settings.get_as_bool(SETTINGS_INCLUDE_APPROVE_MODE_PATH):
            self._modes.append("approve")
        self._sub_stage = get_eventdispatcher().observe_event(
            observer_name="omni.kit.usd_explorer.main.menubar:ApplicationModeControl",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_event,
        )
        self._settings.set_default(SETTINGS_APPLICATION_MODE_PATH, self._modes[0])
        self._settings.subscribe_to_node_change_events(
            SETTINGS_APPLICATION_MODE_PATH, self._on_application_mode_changed
        )
        self._buttons: TabedGroup = TabedGroup()

        ui.Spacer(width=5)
        with ui.VStack(width=120, height=MENUBAR_HEIGHT):
            with ui.HStack(spacing=5, height=MENUBAR_HEIGHT):
                ui.Spacer()
                self.build_buttons()

        self._on_application_mode_changed()

    def __new__(cls, *args: Any, **kwargs: Dict[str, Any]) -> "ApplicationModeControl":
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @property
    def button_group(self) -> TabedGroup:
        return self._buttons

    def build_buttons(self) -> None:
        if len(self._modes) < MAX_MODE_COUNT:
            ui.Spacer(width=30 * (MAX_MODE_COUNT - len(self._modes)))
        for mode, tooltip in zip(
            self._modes,
            ("Show a scene", "Annotate a scene", "Explore and Modify a scene", "Approve changes to a scene"),
        ):
            tooltip_name = f"tname:{tooltip}"
            with ui.ZStack(width=0):
                ui.Spacer()
                label_button = LabelButton(
                    mode, self._set_mode, tooltip=tooltip_name, identifier=f"_application_mode_control_{mode}_btn"
                )
                ui.Spacer()
            if isinstance(self._buttons, TabedGroup):
                self._buttons.add_child(mode, label_button)

            ui.Spacer(width=2)
            if mode == self._modes[-1]:
                continue
            ThickSeparator()
            ui.Spacer(width=2)

    def destroy(self) -> None:
        self._buttons = None
        self._sub_stage = None

    def _on_stage_event(self, event) -> None:
        if self._settings.get_as_bool(SETTINGS_SWITCH_TO_PRESENT_ON_OPEN):
            self._set_mode(self._modes[0])

    def _on_application_mode_changed(self, *args) -> None:
        mode = self._settings.get_as_string(SETTINGS_APPLICATION_MODE_PATH)
        if self._buttons:
            self._buttons.select(mode)
        ApplicationModeControl.request_update_selection_state()

    def _has_markups(self) -> bool:
        from omni.kit.markup.core import get_instance as get_markup_instance

        return bool(get_markup_instance().get_markups())

    def _set_mode(self, mode: str) -> None:
        mode = mode.lower()
        current_mode = self._settings.get_as_string(SETTINGS_APPLICATION_MODE_PATH).lower()
        if mode == current_mode:
            return

        if mode == "approve":
            # Check if the file is read only. If so, notify user and exit early.
            if not omni.usd.get_context().is_writable():
                message = f"Current file is read-only. Staying in {current_mode.title()} mode."
                nm.post_notification(message, status=nm.NotificationStatus.INFO, hide_after_timeout=True, duration=3)
                return

            # Check if any Markups exist in the stage. If there are none, notify user
            # and exit early retaining the current mode state.
            if not self._has_markups():
                message = f"No items found for approval. Staying in {current_mode.title()} mode."
                nm.post_notification(message, status=nm.NotificationStatus.INFO, hide_after_timeout=True, duration=3)
                return

        if not isinstance(self._buttons, TabedGroup):
            return

        # Set in prefs so other tools can key off of the mode.
        self._settings.set_string(SETTINGS_APPLICATION_MODE_PATH, mode)
        self._buttons.select(mode)

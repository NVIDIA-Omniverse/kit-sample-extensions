import asyncio
import math

import carb
import omni.kit.notification_manager as nm
import omni.timeline
from carb.input import KEYBOARD_MODIFIER_FLAG_ALT, KEYBOARD_MODIFIER_FLAG_SHIFT
from omni import ui
from omni.kit.commands import execute
from omni.kit.widget.options_button import OptionsButton
from omni.kit.widget.options_menu import OptionCustom, OptionItem, OptionRadios, OptionSeparator, SettingModel

from .timeline_widget import TimelineWidget
from .utils import (
    AUTO_KEY_ALL_XFORM_SETTING,
    COMPENSATE_PLAY_DELAY_IN_SECS_SETTING,
    SNAP_TO_FRAME_SETTING,
    SUB_STEPPING_SETTING_MAX,
    SUB_STEPPING_SETTING_MIN,
    TIME_DISPLAY_SETTING,
    TimeDisplay,
)

PLAY_STEP_SETTING_PATH = "/app/player/useFixedTimeStepping"
PLAY_ANIMATIONS_SETTING = "/app/player/playAnimations"
PLAY_AUDIO_SETTING = "/app/player/audio/enabled"
PLAY_SIMULATIONS_SETTING = "/app/player/playSimulations"
PLAY_COMPUTEGRAPH_SETTING = "/app/player/playComputegraph"


class PlayEveryFrameModel(ui.AbstractValueModel):
    def __init__(self):
        self._timeline = omni.timeline.get_timeline_interface()
        self._play_every_frame_model = ui.SimpleBoolModel(self.play_every_frame)

        def __on_play_every_frame_changed(model):
            # Set real value
            self.play_every_frame = model.as_bool

        self.__sub_play_every_frame = self._play_every_frame_model.subscribe_value_changed_fn(
            __on_play_every_frame_changed
        )

        super().__init__()

    def destroy(self):
        self.__sub_play_every_frame = None

    def get_value_as_bool(self) -> bool:
        return self._play_every_frame_model.as_bool

    def set_value(self, value: bool) -> None:
        if value != self._timeline.get_play_every_frame():
            self.play_every_frame = value
            self._play_every_frame_model.set_value(value)
            self._value_changed()

    @property
    def play_every_frame(self) -> bool:
        return self._timeline.get_play_every_frame()

    @play_every_frame.setter
    def play_every_frame(self, value: bool) -> None:
        self._timeline.set_play_every_frame(value)
        self._play_every_frame_model.set_value(value)
        # Notification item model changed to update dirty
        self._value_changed()


class ModifierModel(ui.AbstractValueModel):
    def __init__(self, timeline_widget: TimelineWidget):
        self._timeline_widget = timeline_widget
        self._modifier_to_strings = {
            KEYBOARD_MODIFIER_FLAG_ALT: "Alt",
            KEYBOARD_MODIFIER_FLAG_SHIFT: "Shift",
        }
        self._string_to_modifiers = {v: k for k, v in self._modifier_to_strings.items()}
        super().__init__()

    def get_value_as_string(self) -> bool:
        value = self._modifier_to_strings.get(self._timeline_widget.modifier, "")
        return value

    def set_value(self, modifier: str) -> None:
        value = self._string_to_modifiers.get(modifier, KEYBOARD_MODIFIER_FLAG_ALT)
        if value != self._timeline_widget.modifier:
            self._timeline_widget.modifier = self._string_to_modifiers.get(modifier, KEYBOARD_MODIFIER_FLAG_ALT)
            self._value_changed()


class CompensationItem(OptionItem):
    def __init__(self):
        self._compensation_model = SettingModel(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING)
        self._compensation_default = 0.0

        def __on_compensation_changed(_):
            # Notification item model changed to update dirty
            self.model._value_changed()

        self.__sub_compensation_model = self._compensation_model.subscribe_value_changed_fn(__on_compensation_changed)
        super().__init__("Delay compensation", default=False, checkable=False)

    def destroy(self):
        self.__sub_compensation_model = None
        super().destroy()

    def build_custom_widget(self, item: ui.MenuItem):
        ui.Spacer(width=30)
        with ui.HStack(
            content_clipping=True, width=0
        ):  # need content_clipping so that input into the drag field doesn't click through into menu
            ui.FloatDrag(model=self._compensation_model, width=40, min=0.0, max=100.0, step=0.1)

    def on_triggered(self):
        pass

    @property
    def dirty(self) -> bool:
        """
        Flag of item value changed.
        """
        return not math.isclose(self._compensation_model.as_float, self._compensation_default)

    def reset(self) -> None:
        self._compensation_model.set_value(self._compensation_default)


class SubStepItem(OptionItem):
    def __init__(self):
        self._timeline = omni.timeline.get_timeline_interface()
        self._sub_step_model = ui.SimpleIntModel()
        self._sub_step_default = 1

        def __on_sub_step_changed(model):
            # Set real value
            self.sub_step = model.as_int

        self.__sub_sub_step_model = self._sub_step_model.subscribe_value_changed_fn(__on_sub_step_changed)
        super().__init__("Sub-step", default=False, checkable=False)

    def destroy(self):
        self.__sub_sub_step_model = None
        super().destroy()

    def build_custom_widget(self, item: ui.MenuItem):
        ui.Spacer()
        with ui.HStack(
            content_clipping=True, width=0
        ):  # need content_clipping so that input into the drag field doesn't click through into menu
            ui.IntDrag(
                model=self._sub_step_model,
                width=40,
                min=SUB_STEPPING_SETTING_MIN,
                max=SUB_STEPPING_SETTING_MAX,
                step=1,
            )
            self._sub_step_model.set_value(self.sub_step)

    def on_triggered(self):
        pass

    @property
    def dirty(self) -> bool:
        """
        Flag of item value changed.
        """
        return self._sub_step_model.as_int != self._sub_step_default

    def reset(self) -> None:
        if self.dirty:
            self._sub_step_model.set_value(self._sub_step_default)

    def refresh(self):
        self._sub_step_model.set_value(self.sub_step)

    @property
    def sub_step(self) -> int:
        sub_stepping = self._timeline.get_ticks_per_frame()
        if sub_stepping < SUB_STEPPING_SETTING_MIN or sub_stepping > SUB_STEPPING_SETTING_MAX:
            carb.log_warn(f"Sub-Stepping setting is outside of the allowed range: {sub_stepping}")
            # falback to default if setting is not recognized
            sub_stepping = max(SUB_STEPPING_SETTING_MIN, sub_stepping)
            sub_stepping = min(SUB_STEPPING_SETTING_MAX, sub_stepping)
        return sub_stepping

    @sub_step.setter
    def sub_step(self, value: int) -> None:
        if isinstance(value, int):
            if value < SUB_STEPPING_SETTING_MIN or value > SUB_STEPPING_SETTING_MAX:
                carb.log_warn(f"Invalid Sub-Stepping: {value}.")
                value = max(SUB_STEPPING_SETTING_MIN, value)
                value = min(SUB_STEPPING_SETTING_MAX, value)
            if value != self.sub_step:
                self._timeline.set_ticks_per_frame(value)
                self._sub_step_model.set_value(value)
                # Notification item model changed to update dirty
                self.model._value_changed()
        else:
            raise ValueError(f"Invalid Sub-Stepping type: {value}.")


class TimelineOptionsButton(OptionsButton):
    def __init__(self, timeline_widget: TimelineWidget):
        self._play_every_frame_model = PlayEveryFrameModel()
        self._modifier_model = ModifierModel(timeline_widget)
        self._substep_item = SubStepItem()

        cog_char = omni.kit.ui.get_custom_glyph_code("${glyphs}/cog.svg")
        option_items = [
            OptionItem("Snap Timeslider to frames", setting_path=SNAP_TO_FRAME_SETTING),
            OptionItem("Autokey all transforms", setting_path=AUTO_KEY_ALL_XFORM_SETTING),
            OptionSeparator(),
            OptionRadios(
                [TimeDisplay.FRAMES, TimeDisplay.SECONDS, TimeDisplay.SMPTE],
                default=TimeDisplay.FRAMES,
                setting_path=TIME_DISPLAY_SETTING,
                tooltips=[
                    "Display the time in frames",
                    "Display the time in seconds",
                    "Display the time in Hour:Minute:Second:Frame",
                ],
            ),
            OptionSeparator(title="Playback Settings"),
            OptionItem("FixedTimeStepping", default=True, setting_path=PLAY_STEP_SETTING_PATH),
            OptionItem("Play Every Frame", model=self._play_every_frame_model),
            CompensationItem(),
            self._substep_item,
            OptionSeparator(title="Filter"),
            OptionItem("Animation", default=True, setting_path=PLAY_ANIMATIONS_SETTING),
            OptionItem("Audio", default=True, setting_path=PLAY_AUDIO_SETTING),
            OptionItem("Simulations", default=True, setting_path=PLAY_SIMULATIONS_SETTING),
            OptionItem("Computegraph", default=True, setting_path=PLAY_COMPUTEGRAPH_SETTING),
            OptionCustom(
                build_fn=lambda: ui.MenuItem("Select All", triggered_fn=self._select_all, hide_on_click=False)
            ),
            OptionSeparator(title="Modifier"),
            OptionRadios(["Alt", "Shift"], model=self._modifier_model),
            OptionSeparator(),
            OptionCustom(
                build_fn=lambda: ui.MenuItem(
                    f"Animation Preferences {cog_char}", triggered_fn=self._show_animation_preferences
                )
            ),
        ]
        super().__init__(
            option_items,
            width=24,
            height=30,
            style={
                "OptionsButton:hovered": {"background_color": 0xFF333333},
                "margin_height": 2,
                "margin_width": 0,
            },
        )

    def _show_options_menu(self):
        # Manuall refresh some models
        self._play_every_frame_model._value_changed()
        self._modifier_model._value_changed()
        # self._substep_item._sub_step_model._value_changed()
        self._substep_item.refresh()

        super()._show_options_menu()

    def _select_all(self) -> None:
        all_play_settings_paths = [
            PLAY_ANIMATIONS_SETTING,
            PLAY_AUDIO_SETTING,
            PLAY_SIMULATIONS_SETTING,
            PLAY_COMPUTEGRAPH_SETTING,
        ]
        execute("ToolbarPlayFilterSelectAll", settings=all_play_settings_paths)

    def _show_animation_preferences(self):
        try:
            from omni.kit.window.preferences import get_page_list, select_page, show_preferences_window

            show_preferences_window()
            for page in get_page_list():
                if page.get_title() == "Animation Preferences":
                    select_page(page)
        except ImportError:
            message = "Please load omni.kit.window.preferences extension."
            nm.post_notification(
                message,
                hide_after_timeout=True,
                duration=2,
                status=nm.NotificationStatus.WARNING,
            )
            carb.log_info(message)

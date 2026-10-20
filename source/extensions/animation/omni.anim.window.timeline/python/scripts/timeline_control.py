import math
from typing import List

import carb
import carb.eventdispatcher
import carb.settings
import omni.anim.curve.core
import omni.ext
import omni.kit.app
import omni.kit.notification_manager as nm
import omni.timeline
import omni.ui as ui
import omni.usd
from carb.input import KEYBOARD_MODIFIER_FLAG_ALT, KEYBOARD_MODIFIER_FLAG_SHIFT
from omni.kit.commands import execute

from .autokey import AutoKeyGenerator
from .keyframe_listener import KeyFrameListener
from .live_session import TimelineLiveSession
from .timeline_value_model import TimelineFPSModel, TimelineValueModel, WeakMethod
from .timeline_widget import TimelineWidget
from .TimelineMenuDelegate import CompensationMenuItemDelegate, SubstepMenuItemDelegate, TimelineMenuDelegate
from .utils import (
    SUB_STEPPING_SETTING_MAX,
    SUB_STEPPING_SETTING_MIN,
    TIME_DISPLAY_SETTING,
    TimeDisplay,
    add_xform_keys,
    get_auto_key_all_xform,
    get_compensate_play_delay_in_secs,
    get_icon_path,
    get_snap_to_frame,
    get_time_display,
    set_auto_key_all_xform,
    set_compensate_play_delay_in_secs,
    set_snap_to_frame,
    set_time_display,
)


class TimelineControlWidget:
    BUTTON_SIZE = 16
    MARGIN_SIZE = 4
    PLAY_ANIMATIONS_SETTING = "/app/player/playAnimations"
    PLAY_AUDIO_SETTING = "/app/player/audio/enabled"
    PLAY_SIMULATIONS_SETTING = "/app/player/playSimulations"
    PLAY_COMPUTEGRAPH_SETTING = "/app/player/playComputegraph"

    PLAY_STEP_SETTING_PATH = "/app/player/useFixedTimeStepping"

    AUTO_BTN_OFF_TOOLTIP = "Auto keyframing of the selected prims. You must add a keyframe to a prim before autokey can function on that prim"
    AUTO_BTN_DISABLED_TOOLTIP = "You must add a keyframe to a prim before autokey can function on that prim"
    AUTO_BTN_ON_TOOLTIP = "An animation key will be automatically added whenever the user changes a value."

    all_play_settings_paths = [
        PLAY_ANIMATIONS_SETTING,
        PLAY_AUDIO_SETTING,
        PLAY_SIMULATIONS_SETTING,
        PLAY_COMPUTEGRAPH_SETTING,
    ]

    def __init__(self, timeline_widget: TimelineWidget):
        self._timeline_widget = timeline_widget
        self._app = omni.kit.app.get_app_interface()
        self._usd_context = omni.usd.get_context()
        self._timeline = omni.timeline.get_timeline_interface()
        self._settings = carb.settings.get_settings()
        self._keyframe_listener = KeyFrameListener.get_instance()
        self._curve_plugin = omni.anim.curve.core.acquire_interface()
        # Subscribe to USD stage events using Events 2.0
        ed = carb.eventdispatcher.get_eventdispatcher()
        self._stage_subs = [
            ed.observe_event(
                observer_name="timeline_control:stage_closing",
                event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.CLOSING),
                on_event=lambda e: self._on_stage_closing(),
            ),
            ed.observe_event(
                observer_name="timeline_control:selection_changed",
                event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.SELECTION_CHANGED),
                on_event=lambda e: self._on_stage_selection_changed(),
            ),
        ]
        self._is_playing = -1
        self._play_pause_button = None
        self._fps_combo = None
        self._fps_combo_cb = None
        self._fps_model = TimelineFPSModel()
        self._loop = None
        self._autoframe_btn = None
        self._auto_framekey = None

        self._live_session = None
        self._user_circle = None
        self._short_user_name = None
        self._user_name = None

        self._keyframe_listener.add_curve_update_fn(self._on_keyframe_evt)
        self._time_setting_sub = omni.kit.app.SettingChangeSubscription(
            TIME_DISPLAY_SETTING, on_change=self._on_time_display_settings_change
        )

        self._build_events()
        self._build_ui()

    def __del__(self):
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._timeline_widget = None
        self._app = None
        self._timeline = None
        self._play_pause_button = None
        self._app_update_sub = None
        self._timeline_change_sub = None
        self._stage_subs = None
        self._settings = None
        self._keyframe_listener = None
        self._autoframe_btn = None
        self._time_setting_sub = None

        if self._live_session:
            self._live_session.deregister_status_changed_fn(self._on_live_session)
            self._live_session = None

        if self._loop:
            self._loop.destroy()
            self._loop = None

        if self._fps_combo:
            self._fps_combo.model.get_item_value_model().remove_value_changed_fn(self._fps_combo_cb)
            self._fps_combo_cb = None
            self._fps_combo = None
            self._fps_model = None

        if self._auto_framekey:
            self._auto_framekey.destroy()
            self._auto_framekey = None

        self._current_time_model = None
        self._current_time_field = None

    def _build_ui(self):
        button_style = {
            "Button": {"background_color": 0x00000000},
            "Button:hovered": {"background_color": 0xFF333333},
            "margin_height": 2,
            "margin_width": 0,
        }
        with ui.ZStack(width=0):
            self._listener_stack = ui.HStack(width=0)
            with self._listener_stack:
                # show presenter info
                with ui.ZStack(width=55, height=54):
                    self._user_circle = ui.Circle(
                        radius=20,
                        size_policy=ui.CircleSizePolicy.FIXED,
                        style={"background_color": 0xFF000000},
                        alignment=ui.Alignment.CENTER,
                    )
                    self._short_user_name = ui.Label("", alignment=ui.Alignment.CENTER)
                with ui.VStack(width=210):
                    ui.Label("Timeline is current presenter by")
                    self._user_name = ui.Label("unknown@nvidia.com")
            self._controll_stack = ui.VStack(width=0)
            with self._controll_stack:
                ui.Spacer()
                with ui.HStack(width=0, height=0):
                    ui.Spacer(width=6)

                    self._current_time_model = TimelineValueModel(omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED)
                    self._current_time_field = ui.StringField(
                        self._current_time_model,
                        alignment=ui.Alignment.LEFT_CENTER,
                        width=80,
                        height=self.BUTTON_SIZE,
                        style={"margin_height": 4},
                    )

                    ui.Spacer(width=2)
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("first_frame.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self.on_button_first_frame,
                        tooltip="Moves the playhead to the first frame",
                        style=button_style,
                    )
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("previous_frame.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self.on_button_previous_frame,
                        tooltip="Moves the playhead to the previous frame",
                        style=button_style,
                    )
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("previous_keyframe.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self._on_button_previous_key_frame,
                        tooltip="Moves the playhead to the previous keyframe",
                        style=button_style,
                    )
                    self._play_pause_button = ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("play.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self.on_button_play,
                        tooltip="Begins playback of the timeline, if already playing this will pause playback",
                        style=button_style,
                    )
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("next_keyframe.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self._on_button_next_key_frame,
                        tooltip="Moves the playhead to the the next keyframe",
                        style=button_style,
                    )
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("next_frame.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self.on_button_next_frame,
                        tooltip="Moves the playhead to the next frame",
                        style=button_style,
                    )

                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("last_frame.svg"),
                        image_width=self.BUTTON_SIZE,
                        image_height=self.BUTTON_SIZE,
                        clicked_fn=self.on_button_last_frame,
                        tooltip="Moves the playhead to the last frame",
                        style=button_style,
                    )

                    # loop icon show in ui.Button are squashed, werid?
                    with ui.VStack():
                        ui.Spacer(height=3)
                        self._loop = ImageButton(
                            "loop",
                            22,
                            19,
                            get_icon_path("loop.svg"),
                            self._on_button_looping,
                            tooltip="If toggled on, will loop the playback of the designated frame range",
                        )
                        self._loop.create()
                        self._loop.activate(self._timeline.is_looping())
                        ui.Spacer()

                    ui.Spacer(width=4)

                ui.Spacer()
                with ui.HStack(width=0, height=0):
                    ui.Spacer(width=6)
                    with ui.ZStack():
                        self._fps_combo = ui.ComboBox(
                            True,
                            "24",
                            "25",
                            "29.97",
                            "30",
                            "60",
                            "120",
                            width=60,
                            tooltip="Selects a desired FPS(Frames Per Second) playback rate",
                            style={"margin_height": 2},
                            identifier="edit_combobox",
                        )
                        with ui.ZStack(width=0, content_clipping=True):
                            ui.StringField(self._fps_model, width=43, height=20, style={"margin_height": 2})

                    ui.Label(
                        "FPS",
                        width=0,
                        alignment=ui.Alignment.LEFT_CENTER,
                    )

                    ui.Spacer(width=10)
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("Add_Key.svg"),
                        image_width=self.BUTTON_SIZE + 2,
                        image_height=self.BUTTON_SIZE + 2,
                        clicked_fn=self._on_button_add_xform_keys,
                        style=button_style,
                        tooltip="To animate an object - Set keyframe on all transform attributes. The hotkey is ALT+S",
                    )

                    ui.Spacer(width=10)

                    auto_style = {
                        "Button::AutoFrame": {"background_color": 0xFF31312F, "margin": 4, "padding": 2},
                        "Button::AutoFrame:checked": {"background_color": 0xFF6060AA},
                    }

                    self._autoframe_btn = ui.ToolButton(
                        text="Auto",
                        width=0,
                        height=0,
                        clicked_fn=self._on_button_auto,
                        tooltip=self.AUTO_BTN_OFF_TOOLTIP,
                        style=auto_style,
                        name="AutoFrame",
                    )

                    ui.Spacer(width=10)
                    ui.Line(
                        width=3,
                        alignment=ui.Alignment.LEFT,
                        style={"color": 0xFF707070, "margin_height": self.MARGIN_SIZE},
                    )
                    ui.Spacer(width=10)

                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("sequencer.svg"),
                        image_width=self.BUTTON_SIZE,
                        style=button_style,
                        tooltip="Launches the Movie Capture tool",
                        clicked_fn=self._on_button_sequencer,
                    )
                    ui.Button(
                        "",
                        width=0,
                        image_url=get_icon_path("Record_4.svg"),
                        image_width=self.BUTTON_SIZE,
                        style=button_style,
                        tooltip="Launches the Stage recorder tool",
                        clicked_fn=self._on_button_recorder,
                    )
                    try:
                        # OptionsButton only available in latest kit 105.2
                        from .timeline_options import TimelineOptionsButton

                        self._options_btn = TimelineOptionsButton(self._timeline_widget)
                    except Exception:
                        ui.Button(
                            "",
                            name="options",
                            width=0,
                            image_url="resources/icons/details_options.png",
                            image_width=self.BUTTON_SIZE,
                            clicked_fn=self._on_button_options_menu,
                            style=button_style,
                        )
                ui.Spacer()
            self._fps_combo_cb = self._fps_combo.model.get_item_value_model().add_value_changed_fn(
                lambda m, model=self._fps_combo.model, s=self: s._on_fps_combo_value_changed(model)
            )

        if self._live_session:
            is_sync = self._live_session.is_sync_enabled()
            is_presenter = self._live_session.am_i_presenter()
            self._on_live_session(is_presenter, is_sync)
        else:
            self._listener_stack.visible = False
            self._controll_stack.visible = True

    def get_FPS_list(self) -> List[str]:
        fps_list = []
        if self._fps_combo:
            model = self._fps_combo.model
            for item in model.get_item_children():
                fps_value = model.get_item_value_model(item).get_value_as_string()
                fps_list.append(fps_value)
        return fps_list

    def _update_fps_combo(self, fps: float):
        model = self._fps_combo.model
        fps_items = self._fps_combo.model.get_item_children()
        selected_item = fps_items[model.get_item_value_model().get_value_as_int()]
        current_value = model.get_item_value_model(selected_item).get_value_as_string()

        try:
            v = float(current_value)
            if math.isclose(v, fps, abs_tol=0.01):
                return

            fps_item_found = False
            for i, item in enumerate(fps_items):
                item_value = model.get_item_value_model(item).get_value_as_string()
                v = float(item_value)
                if math.isclose(v, fps, abs_tol=0.01):
                    fps_item_found = True
                    model.get_item_value_model().set_value(i)
                    break
            if not fps_item_found:
                model.append_child_item(None, ui.SimpleStringModel("{0:g}".format(fps)))
                model.get_item_value_model().set_value(i + 1)

        except ValueError:
            return

    def _build_events(self):
        # App update via Events 2.0
        self._app_update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=WeakMethod(self._on_update_event),
            observer_name="omni.anim.window.timeline:update",
        )
        # Keep timeline stream subscription (no Events 2.0 replacement published here yet)
        self._timeline_change_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
            WeakMethod(self._on_timeline_changed)
        )

    def _on_update_event(self, evt):
        playing = self._timeline.is_playing()
        if self._is_playing != playing and self._play_pause_button is not None:
            if playing:
                self._play_pause_button.image_url = "resources/glyphs/timeline_pause.svg"
            else:
                self._play_pause_button.image_url = get_icon_path("play.svg")
            self._is_playing = playing

    def _on_time_display_settings_change(self, value, event_type: carb.settings.ChangeEventType):
        self._timeline_widget.rebuild()
        self._current_time_model._value_changed()

    def _on_timeline_changed(self, evt):
        if evt.type == int(omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED):
            if self._fps_combo is None:
                return
            fps = self._timeline.get_time_codes_per_seconds()
            self._update_fps_combo(fps)

    def _on_keyframe_evt(self, path, **kwargs):
        self._update_auto_button_style()

    def _on_fps_combo_value_changed(self, model):
        origin_fps = self._timeline.get_time_codes_per_seconds()
        selected_item = model.get_item_children()[model.get_item_value_model().get_value_as_int()]
        fps_combo_value = model.get_item_value_model(selected_item).get_value_as_string()
        new_fps = float(fps_combo_value)
        if not math.isclose(origin_fps, new_fps, abs_tol=0.01):
            self._timeline.set_time_codes_per_second(new_fps)

    def on_button_first_frame(self):
        start = self._timeline.get_zoom_start_time()
        self._timeline.set_current_time(start)
        self._timeline.pause()

    def on_button_previous_frame(self):
        self._timeline.rewind_one_frame()
        self._timeline.pause()

    def _on_button_previous_key_frame(self):
        pre_key_time = self._timeline_widget.get_previous_key_time()
        if pre_key_time is not None:
            self._timeline.set_current_time(pre_key_time)
        self._timeline.pause()

    def on_button_play(self):
        if self._timeline.is_playing():
            self._timeline.pause()
        else:
            self._timeline.play()

    def on_button_next_frame(self):
        self._timeline.forward_one_frame()
        self._timeline.pause()

    def _on_button_next_key_frame(self):
        next_key_time = self._timeline_widget.get_next_key_time()
        if next_key_time is not None:
            self._timeline.set_current_time(next_key_time)
        self._timeline.pause()

    def on_button_last_frame(self):
        end = self._timeline.get_zoom_end_time()
        self._timeline.set_current_time(end)
        self._timeline.pause()

    def _on_button_looping(self):
        value = not self._loop.is_activated()
        self._loop.activate(value)
        self._timeline.set_looping(value)

    def _on_button_add_xform_keys(self):
        stage = self._usd_context.get_stage()
        if not stage:
            message = "Try to add animation keys while the scene stage is invalid."
            nm.post_notification(
                message,
                hide_after_timeout=True,
                duration=2,
                status=nm.NotificationStatus.WARNING,
            )
            carb.log_info(message)
            return
        selection = self._usd_context.get_selection()
        prim_paths = selection.get_selected_prim_paths()
        add_xform_keys(prim_paths, stage)

    def _on_button_auto(self):
        if self._auto_framekey is None:
            self._auto_framekey = AutoKeyGenerator()
            carb.log_info("[Anim.Timeline] Auto Framekey start")
        else:
            self._auto_framekey.destroy()
            self._auto_framekey = None
            carb.log_info("[Anim.Timeline] Auto Framekey stop")
        self._update_auto_button_style()

    def _update_auto_button_style(self):
        if self._autoframe_btn is None:
            return
        if not self._autoframe_btn.checked:
            self._autoframe_btn.set_tooltip(self.AUTO_BTN_OFF_TOOLTIP)
        else:
            cur_style = self._autoframe_btn.style
            if self._can_auto_key():
                cur_style.update(
                    {
                        "Button::AutoFrame:checked": {"background_color": 0xFF6060AA},
                    }
                )
                self._autoframe_btn.set_tooltip(self.AUTO_BTN_ON_TOOLTIP)
            else:
                cur_style.update(
                    {
                        "Button::AutoFrame:checked": {"background_color": 0xFF60AAAA},
                    }
                )
                self._autoframe_btn.set_tooltip(self.AUTO_BTN_DISABLED_TOOLTIP)
            self._autoframe_btn.set_style(cur_style)

    def _can_auto_key(self, prim_paths=None):
        stage = omni.usd.get_context().get_stage()
        # if, by default, the prim_paths is None, use selected prim paths
        if prim_paths is None:
            selection = omni.usd.get_context().get_selection()
            if selection and stage:
                prim_paths = selection.get_selected_prim_paths()
        if prim_paths and len(prim_paths) > 0:
            for prim_path in prim_paths:
                curves = self._curve_plugin.get_curves(prim_path)
                if curves:
                    return True

        return False

    def _on_button_sequencer(self):
        try:
            from omni.kit.window.movie_capture import MovieCaptureExtension

            movie_ext = MovieCaptureExtension().get_instance()
            movie_ext.show_window(None, True)
        except ImportError:
            message = "Please load omni.kit.window.movie_capture extension."
            nm.post_notification(
                message,
                hide_after_timeout=True,
                duration=2,
                status=nm.NotificationStatus.WARNING,
            )
            carb.log_info(message)

    def _on_button_recorder(self):
        ui.Workspace.show_window("Stage Recorder", True)
        window = ui.Workspace.get_window("Stage Recorder")
        if not window:
            message = "Please load omni.kit.stagerecorder extension."
            nm.post_notification(
                message,
                hide_after_timeout=True,
                duration=2,
                status=nm.NotificationStatus.WARNING,
            )
            carb.log_info(message)

    def _on_button_options_menu(self):
        # keyboard modifier
        def set_modifier(value):
            self._timeline_widget.modifier = value

        def do_nothing(value):
            pass

        def is_second(value):
            return get_time_display() == TimeDisplay.SECONDS

        def is_frame(value):
            return get_time_display() == TimeDisplay.FRAMES

        def is_smpte(value):
            return get_time_display() == TimeDisplay.SMPTE

        menu_delegate = TimelineMenuDelegate()
        compensation_item_delegate = CompensationMenuItemDelegate(
            "Delay compensation", get_compensate_play_delay_in_secs(), set_compensate_play_delay_in_secs
        )
        sub_step_item_delegate = SubstepMenuItemDelegate("Sub-step", self.get_sub_stepping(), self.set_sub_stepping)
        menu_delegate.add_item_delegate(compensation_item_delegate)
        menu_delegate.add_item_delegate(sub_step_item_delegate)
        cog_char = omni.kit.ui.get_custom_glyph_code("${glyphs}/cog.svg")

        context_menu = omni.kit.context_menu.get_instance()
        settings = carb.settings.get_settings()
        objects = {"widget_name": "Timeline Opition", "main_toolbar": False}
        menu_list = [
            {
                "name": "Snap Timeslider to frames",
                "onclick_fn": lambda obj: set_snap_to_frame(not get_snap_to_frame()),
                "checked_fn": lambda obj: get_snap_to_frame(),
            },
            {
                "name": "Autokey all transforms",
                "onclick_fn": lambda obj: set_auto_key_all_xform(not get_auto_key_all_xform()),
                "checked_fn": lambda obj: get_auto_key_all_xform(),
            },
            {
                "name": "",
            },
            {
                "name": "Frames",
                "checked_fn": is_frame,
                "onclick_fn": lambda obj: set_time_display(TimeDisplay.FRAMES),
                "additional_kwargs": {"tooltip": "Display the time in frames"},
            },
            {
                "name": "Seconds",
                "checked_fn": is_second,
                "onclick_fn": lambda obj: set_time_display(TimeDisplay.SECONDS),
                "additional_kwargs": {"tooltip": "Display the time in seconds"},
            },
            {
                "name": "SMPTE",
                "checked_fn": is_smpte,
                "onclick_fn": lambda obj: set_time_display(TimeDisplay.SMPTE),
                "additional_kwargs": {"tooltip": "Display the time in Hour:Minute:Second:Frame"},
            },
            {
                "name": "",
            },
            {
                "name": "Playback Settings",
                "enabled_fn": lambda object: False,
            },
            {
                "name": "FixedTimeStepping",
                "onclick_fn": lambda object: self._toggle_setting(TimelineControlWidget.PLAY_STEP_SETTING_PATH),
                "checked_fn": lambda object: settings.get_as_bool(TimelineControlWidget.PLAY_STEP_SETTING_PATH),
            },
            {
                "name": "Play Every Frame",
                "checked_fn": lambda obj: self.get_play_every_frame(),
                "onclick_fn": lambda obj: self.set_play_every_frame(not self.get_play_every_frame()),
            },
            {
                "name": compensation_item_delegate.name,
                "onclick_fn": do_nothing,
            },
            {
                "name": sub_step_item_delegate.name,
                "onclick_fn": do_nothing,
            },
            {
                "name": "",
            },
            {
                "name": "Filter",
                "enabled_fn": lambda object: False,
            },
            {
                "name": "Animation",
                "checked_fn": lambda obj: settings.get_as_bool(self.PLAY_ANIMATIONS_SETTING),
                "onclick_fn": lambda obj: self._on_filter_changed(self.PLAY_ANIMATIONS_SETTING),
            },
            {
                "name": "Audio",
                "checked_fn": lambda obj: settings.get_as_bool(self.PLAY_AUDIO_SETTING),
                "onclick_fn": lambda obj: self._on_filter_changed(self.PLAY_AUDIO_SETTING),
            },
            {
                "name": "Simulations",
                "checked_fn": lambda obj: settings.get_as_bool(self.PLAY_SIMULATIONS_SETTING),
                "onclick_fn": lambda obj: self._on_filter_changed(self.PLAY_SIMULATIONS_SETTING),
            },
            {
                "name": "Computegraph",
                "checked_fn": lambda obj: settings.get_as_bool(self.PLAY_COMPUTEGRAPH_SETTING),
                "onclick_fn": lambda obj: self._on_filter_changed(self.PLAY_COMPUTEGRAPH_SETTING),
            },
            {"name": "Select All", "onclick_fn": lambda obj: self._select_all()},
            {
                "name": "",
            },
            {
                "name": "Modifier",
                "enabled_fn": lambda object: False,
            },
            {
                "name": "Alt",
                "checked_fn": lambda obj: self._timeline_widget.modifier == KEYBOARD_MODIFIER_FLAG_ALT,
                "onclick_fn": lambda obj: set_modifier(KEYBOARD_MODIFIER_FLAG_ALT),
            },
            {
                "name": "Shift",
                "checked_fn": lambda obj: self._timeline_widget.modifier == KEYBOARD_MODIFIER_FLAG_SHIFT,
                "onclick_fn": lambda obj: set_modifier(KEYBOARD_MODIFIER_FLAG_SHIFT),
            },
            {
                "name": "",
            },
            {
                "name": f"Animation Preferences {cog_char}",
                "onclick_fn": self._show_animation_preferences,
            },
        ]

        context_menu.show_context_menu("Timeline Opition", objects, menu_list, delegate=menu_delegate)

    def _toggle_setting(self, path: str):
        settings = carb.settings.get_settings()
        value = settings.get_as_bool(path)
        execute("ChangeSetting", path=path, value=not value)

    def _on_filter_changed(self, filter_setting):
        settings = carb.settings.get_settings()
        value = settings.get_as_bool(filter_setting)
        execute("ToolbarPlayFilterChecked", setting_path=filter_setting, enabled=not value)

    def _select_all(self):
        execute("ToolbarPlayFilterSelectAll", settings=self.all_play_settings_paths)

    def get_play_every_frame(self) -> bool:
        return self._timeline.get_play_every_frame()

    def set_play_every_frame(self, value: bool):
        self._timeline.set_play_every_frame(value)

    def get_sub_stepping(self) -> int:
        sub_stepping = self._timeline.get_ticks_per_frame()
        if sub_stepping < SUB_STEPPING_SETTING_MIN or sub_stepping > SUB_STEPPING_SETTING_MAX:
            carb.log_warn(f"Sub-Stepping setting is outside of the allowed range: {sub_stepping}")
            # falback to default if setting is not recognized
            sub_stepping = max(SUB_STEPPING_SETTING_MIN, sub_stepping)
            sub_stepping = min(SUB_STEPPING_SETTING_MAX, sub_stepping)
        return sub_stepping

    def set_sub_stepping(self, value: int):
        if isinstance(value, int):
            if value < SUB_STEPPING_SETTING_MIN or value > SUB_STEPPING_SETTING_MAX:
                carb.log_warn(f"Invalid Sub-Stepping: {value}.")
                value = max(SUB_STEPPING_SETTING_MIN, value)
                value = min(SUB_STEPPING_SETTING_MAX, value)
            self._timeline.set_ticks_per_frame(value)
        else:
            raise ValueError(f"Invalid Sub-Stepping type: {value}.")

    def _show_animation_preferences(self, item):
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

    def _on_stage_closing(self):
        self._autoframe_btn.model.set_value(False)
        if self._auto_framekey:
            self._auto_framekey.destroy()
            self._auto_framekey = None

    def _on_stage_selection_changed(self):
        self._update_auto_button_style()

    def set_live_session(self, live_session: TimelineLiveSession):
        self._live_session = live_session
        self._live_session.register_status_changed_fn(self._on_live_session)

    def _on_live_session(self, is_presenter: bool, is_sync: bool):
        self._listener_stack.visible = is_sync and not is_presenter
        self._controll_stack.visible = not self._listener_stack.visible
        if self._listener_stack.visible:
            self._user_circle.style = {"background_color": self._live_session.get_presenter_user_color()}
            self._short_user_name.text = self._live_session.get_presenter_user_short_name()
            self._user_name.text = self._live_session.get_presenter_user_name()


class ImageButton:
    MOUSE_LEFT = 0
    UI_STYLES = {
        "ImageButton": {"background_color": 0x0000000, "border_width": 0, "border_radius": 2.0},
        "ImageButton:hovered": {"background_color": 0xFF333333},
        "ImageButton:pressed": {"background_color": 0xFF333333},
        "ImageButton:selected": {"background_color": 0xFF222222},
        "ImageButton:disabled": {"background_color": 0xFFE0E0E0, "color": 0xFFE0E0E0},
    }

    def __init__(
        self,
        name,
        width,
        height,
        image,
        clicked_fn,
        tooltip=None,
        visible=True,
        enabled=True,
        activated=False,
        tooltip_fn=None,
    ):
        self._name = name
        self._width = width
        self._height = height
        self._tooltip = tooltip
        self._tooltip_fn = tooltip_fn
        self._visible = visible
        self._enabled = enabled
        self._image = image
        self._clicked_fn = clicked_fn
        self._activated = activated
        self._bkground_widget = None
        self._image_widget = None

        self._mouse_x = 0
        self._mouse_y = 0

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._bkground_widget:
            self._bkground_widget = None
        if self._image_widget:
            self._image_widget.destroy()
            self._image_widget = None
        self._tooltip_fn = None
        self._clicked_fn = None

    def create(self, style=None, padding_x=2, padding_y=2):
        ww = self.get_width()
        hh = self.get_height()
        if style is None:
            style = ImageButton.UI_STYLES
        with ui.ZStack(spacing=0, width=ww, height=hh, style=style):
            with ui.Placer(offset_x=0, offset_y=0):
                self._bkground_widget = ui.Rectangle(
                    name=self._name, style_type_name_override="ImageButton", width=ww, height=hh
                )
            self._bkground_widget.visible = self._visible and self._enabled

            with ui.Placer(offset_x=padding_x, offset_y=padding_y):
                self._image_widget = ui.Image(
                    self._image,
                    width=ww - padding_x * 2,
                    height=hh - padding_y * 2,
                    fill_policy=ui.FillPolicy.STRETCH,
                    mouse_pressed_fn=(lambda x, y, key, m: self._on_mouse_pressed(x, y, key)),
                    mouse_released_fn=(lambda x, y, key, m: self._on_mouse_released(x, y, key)),
                    opaque_for_mouse_events=True,
                    style_type_name_override="ImageButton",
                )

        if self._bkground_widget is None or self._image_widget is None:
            return

        if self._tooltip:
            self._image_widget.set_tooltip(self._tooltip)
        if self._tooltip_fn:
            self._tooltip_fn(self._image_widget, self._tooltip)

        if not self._enabled:
            self._bkground_widget.enabled = False
            self._image_widget.enabled = False

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self.enable(value)

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height

    def get_widget_pos(self):
        x = self._bkground_widget.screen_position_x
        y = self._bkground_widget.screen_position_y
        return (x, y)

    def enable(self, enabled):
        if self._enabled != enabled:
            self._enabled = enabled

            self._bkground_widget.visible = enabled and self._visible
            self._image_widget.enabled = enabled
        return False

    def set_tooltip(self, tooltip):
        self._tooltip = tooltip
        if self._image_widget is not None:
            self._image_widget.set_tooltip(self._tooltip)

    def set_tooltip_fn(self, tooltip_fn: callable):
        self._tooltip_fn = tooltip_fn
        if self._image_widget is not None:
            self._image_widget.set_tooltip_fn(lambda w=self._image_widget, name=self._tooltip: tooltip_fn(w, name))

    def is_visible(self):
        return self._visible

    def set_visible(self, visible=True):
        if self._visible != visible:
            self._visible = visible
            self._bkground_widget.visible = visible and self._enabled
            self._image_widget.visible = visible

    def identify(self, name):
        return self._name == name

    def get_name(self):
        return self._name

    def is_activated(self):
        return self._activated

    def activate(self, activated=True):
        if self._activated == activated:
            return False

        self._activated = activated
        self._bkground_widget.selected = activated

    def set_image(self, image):
        if self._image != image:
            self._image = image
            self._image_widget.source_url = image
        return False

    def _on_mouse_pressed(self, x, y, key):
        if not self._enabled:
            return

        # For left button, we do trigger the click event on mouse_released.
        # For other buttons, we trigger the click event right now since Widget will never has
        # mouse_released event for any buttons other than left.
        if key != self.MOUSE_LEFT:
            self._clicked_fn()
        else:
            self._mouse_x = x
            self._mouse_y = y

    def _on_mouse_released(self, x, y, key):
        if self._enabled:
            if key == self.MOUSE_LEFT:
                self._clicked_fn()

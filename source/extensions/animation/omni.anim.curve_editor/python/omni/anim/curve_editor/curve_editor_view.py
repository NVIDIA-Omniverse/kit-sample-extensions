import asyncio
import functools
import math
import os
import weakref

import carb
import omni.kit.actions.core
import omni.kit.menu.utils
import omni.kit.notification_manager as nm
import omni.kit.ui
import omni.timeline
import omni.usd
from omni import ui
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.widget.timeline import WeakMethod

from .curve_editor import SingletonCurveEditor
from .curve_editor_abstract_model import *
from .curve_editor_globals import CurveInfinityTypes
from .curve_editor_prim_panel import *
from .curve_editor_timeline import CurveEditorTimeline
from .curve_editor_utilities_menu import CurveEditorUtilitiesMenu
from .live_session import TimelineLiveSession
from .timeline_merge_globals import *
from .timeline_merge_style import TimelineMergeStyle

CURVE_EDITOR_MENU_PATH = "Window/Animation/Curve Editor"
SETTINGS_SHOW_WINDOW = "/exts/omni.anim.curve_editor/show_window"
TOOLBAR_BUTTON_SIZE = 40

_curve_window_instance = None


def get_window():
    return None if not _curve_window_instance else _curve_window_instance()


class CurveEditorWindow:
    def on_startup(self, ext_id):
        self._usd_context = omni.usd.get_context()
        self._selection = self._usd_context.get_selection()
        self._events = self._usd_context.get_stage_event_stream()
        self._ext_id = ext_id
        self._curveEditorWindow = None
        settings = carb.settings.get_settings()
        settings.set_default_bool(SETTINGS_SHOW_WINDOW, False)
        self._show_window = settings.get_as_bool(SETTINGS_SHOW_WINDOW)
        self._view = CurveEditorView(self)

        # build floating work place window.
        self.build_window()

        # Register menu via omni.kit.menu.utils under Window/Animation
        self._sub_menu = [
            MenuItemDescription(
                name="Animation",
                sub_menu=[
                    MenuItemDescription(
                        name="Curve Editor",
                        ticked=True,
                        ticked_fn=self._on_ticked_fn,
                        onclick_fn=self._on_click_fn,
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._sub_menu, "Window")

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
            hook_name="omni.anim.curve_editor-hotkeys",
        )

    def on_shutdown(self):
        # remove menu
        omni.kit.menu.utils.remove_menu_items(self._sub_menu, "Window")
        self._sub_menu = None
        self._events = None
        self._stage_event_sub = None
        self._view._timeline_event_sub = None
        self._curveEditorWindow = None

        # De-register all hotkeys & actions
        self._clear_hotkeys()
        if self._action_registry:
            self._action_registry.deregister_all_actions_for_extension("omni.anim.curve_editor")

    def _on_ticked_fn(self):
        return self._curveEditorWindow.visible if self._curveEditorWindow else False

    def _on_click_fn(self):
        if self._curveEditorWindow:
            self._curveEditorWindow.visible = not self._curveEditorWindow.visible
            self._curveEditorWindow.deferred_dock_in("Content")

    def _visibility_changed_fn(self, visible):
        # Mark the Window menu dirty so its ticked state updates safely
        omni.kit.menu.utils.refresh_menu_items("Window")

    def _build_view_ui(self):
        with self._curveEditorWindow.frame:
            self._view.build_ui()

    def _window_build_fn(self):
        # _window_build_fn_called and raise_special_refit_flag work together to workaround the problem of first selecting a prim and then toggle on the window visibility from the menu
        # the root problem is TimelineView does not expose meaningful uix when window size is 0 (window invisible), then get key time from uix is wrong, then fit is wrong.
        # now the solution is just a hack. Do another time refit after the window is shown.
        if self._window_build_fn_called == False:
            self._window_build_fn_called = True
            self._view._timeline_view._curve_editor_bottom._curve_list_view.raise_special_refit_flag()

        self._view.update_ui()

    def build_window(self):
        global _curve_window_instance

        windowFlags = ui.WINDOW_FLAGS_NO_COLLAPSE
        windowFlags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        windowFlags |= ui.WINDOW_FLAGS_NO_SCROLL_WITH_MOUSE

        self._curveEditorWindow = ui.Window(
            "Curve Editor",
            flags=windowFlags,
            width=600,
            height=300,
            visible=self._show_window,
            add_to_menu=False,
            raster_policy=ui.RasterPolicy.NEVER,
        )
        self._curveEditorWindow.deferred_dock_in("Content")
        self._curveEditorWindow.set_visibility_changed_fn(self._visibility_changed_fn)

        _curve_window_instance = weakref.ref(self._curveEditorWindow)

        self._window_build_fn_called = False
        self._curveEditorWindow.frame.set_build_fn(self._window_build_fn)
        self._curveEditorWindow.frame.set_computed_content_size_changed_fn(
            lambda: self._curveEditorWindow.frame.rebuild()
        )

        self._build_view_ui()

    def _build_actions(self):
        ext_id = "omni.anim.curve_editor"
        self._action_registry = omni.kit.actions.core.get_action_registry()

        # Frame All, Ctrl+F
        self._action_registry.register_action(ext_id, "frame_all", self._view._on_fit_all, "Frame All", "Frame All")
        # Frame Selected, F
        self._action_registry.register_action(
            ext_id,
            "frame_conditionally",
            self._view._on_fit_conditionally,
            "Frame Selected or All",
            "Frame Selected or All",
        )
        # Looping, L
        self._action_registry.register_action(
            ext_id, "looping", self._view._on_button_looping, "Looping", "Toggle the timeline loop"
        )
        # Add Key, ALT+A
        self._action_registry.register_action(
            ext_id,
            "add_key",
            lambda: self._view._on_add_key(self._view.get_current_time_code()),
            "Add Key",
            "add keys to the selected curves only",
        )
        # Delete Key, Delete
        self._action_registry.register_action(
            ext_id, "delete_key", self._view._on_delete_key, "Delete Key", "delete the selected keys"
        )
        # Copy Key, Ctrl+C
        self._action_registry.register_action(
            ext_id, "copy_key", self._view._on_copy_key, "Copy Key", "copy the selected keys"
        )
        # Paste Key, Ctrl+V
        self._action_registry.register_action(
            ext_id,
            "paste_key",
            lambda: self._view._on_paste_key(self._view.get_current_time_code()),
            "Paste Key",
            "paste the copied keys",
        )
        # Previous Key, Alt+Left
        self._action_registry.register_action(
            ext_id, "previous_key", self._view._on_button_previous_key_frame, "Previous Key", "Previous Key"
        )
        # Next Key, Alt+Right
        self._action_registry.register_action(
            ext_id, "next_key", self._view._on_button_next_key_frame, "Next Key", "Next Key"
        )

    def _build_hotkeys(self):
        try:
            import omni.kit.hotkeys.core
        except ImportError:
            carb.log_warn("Failed to register hotkeys.")
            return

        ext_id = "omni.anim.curve_editor"
        self._hotkey_registry = omni.kit.hotkeys.core.get_hotkey_registry()
        self._hotkey_filter_by_window = omni.kit.hotkeys.core.filter.HotkeyFilter(windows=["Curve Editor"])

        # Frame All, Ctrl+F
        self._hotkey_registry.register_hotkey(ext_id, "CTRL + F", ext_id, "frame_all", self._hotkey_filter_by_window)
        # Frame Selected, F
        self._hotkey_registry.register_hotkey(ext_id, "F", ext_id, "frame_conditionally", self._hotkey_filter_by_window)
        # Looping, L
        self._hotkey_registry.register_hotkey(ext_id, "L", ext_id, "looping", self._hotkey_filter_by_window)
        # Add Key, ALT+A
        self._hotkey_registry.register_hotkey(ext_id, "ALT + A", ext_id, "add_key", self._hotkey_filter_by_window)
        # Delete Key, Delete
        self._hotkey_registry.register_hotkey(ext_id, "DEL", ext_id, "delete_key", self._hotkey_filter_by_window)
        # Copy Key, Ctrl+C
        self._hotkey_registry.register_hotkey(ext_id, "CTRL + C", ext_id, "copy_key", self._hotkey_filter_by_window)
        # Paste Key, Ctrl+V
        self._hotkey_registry.register_hotkey(ext_id, "CTRL + V", ext_id, "paste_key", self._hotkey_filter_by_window)
        # Previous Key, Alt+Left
        self._hotkey_registry.register_hotkey(
            ext_id, "ALT + LEFT", ext_id, "previous_key", self._hotkey_filter_by_window
        )
        # Next Key, Alt+Right
        self._hotkey_registry.register_hotkey(ext_id, "ALT + RIGHT", ext_id, "next_key", self._hotkey_filter_by_window)

    def _clear_hotkeys(self):
        if self._hotkey_registry:
            self._hotkey_registry.deregister_all_hotkeys_for_extension("omni.anim.curve_editor")
        self._hotkey_registry = None
        self._hotkey_filter_by_window = None

    # At least for TimelineView call
    def get_window_width(self):  # pragma: no cover    Unused code
        return self._curveEditorWindow.width

    # At least for TimelineView call
    def get_view(self):  # pragma: no cover    Unused code
        return self._view


# TEMP relam - Needs to be data-driven - "magic numbers" = bad
SPLITTER_WIDTH = 10


class InfinityTypeMenu(ui.Window):
    def __init__(self, parent_view):
        # disable menu_compatibility so that hide_on_click=False works.
        super().__init__(
            "Push menu for infinity types",
            flags=ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR,
            visible=False,
            width=160,
            height=20 * 10 + 15 + 10,  # 5*2 menu items + seperator + padding,
        )
        self._curve_editor_view_wp = weakref.ref(parent_view)
        self._icon_path = parent_view._icon_path

        self._pre_collection = ui.RadioCollection()
        self._post_collection = ui.RadioCollection()

        self._pre_token_friendly_name_mapping = {
            "constant": "Pre-Constant",
            "cycle": "Pre-Cycle",
            "cycleRelative": "Pre-Cycle - Offset",
            "linear": "Pre-Cycle - Linear",
            "oscillate": "Pre-Cycle - Oscillate",
        }
        self._post_token_friendly_name_mapping = {
            "constant": "Post-Constant",
            "cycle": "Post-Cycle",
            "cycleRelative": "Post-Cycle - Offset",
            "linear": "Post-Cycle - Linear",
            "oscillate": "Post-Cycle - Oscillate",
        }

        self._init_items()

    def show_at(self, x, y):
        self.position_x = x
        self.position_y = y
        self.visible = True

    def check_pre_infinity_type(self, pre_infinity_type):
        self._pre_collection.model.set_value(pre_infinity_type)

    def check_post_infinity_type(self, post_infinity_type):
        self._post_collection.model.set_value(post_infinity_type)

    def _set_pre_infinity_type(self, pre_infinity_type):
        self.check_pre_infinity_type(pre_infinity_type)
        self._curve_editor_view_wp().command_set_infinity_type(pre_infinity_type, is_pre_infinity=True)

    def _set_post_infinity_type(self, post_infinity_type):
        self.check_post_infinity_type(post_infinity_type)
        self._curve_editor_view_wp().command_set_infinity_type(post_infinity_type, is_pre_infinity=False)

    def _get_pre_infinity_type_friendly_name(self, index):
        token_name = CurveInfinityTypes.InfinityType.to_infinity_type_token(index)
        return self._pre_token_friendly_name_mapping[token_name]

    def _get_post_infinity_type_friendly_name(self, index):
        token_name = CurveInfinityTypes.InfinityType.to_infinity_type_token(index)
        return self._post_token_friendly_name_mapping[token_name]

    def _init_items(self):
        _check_box_style = {
            "": {
                "background_color": 0x0,
                "image_url": f"{self._icon_path}/radio_off_infinity.svg",
            },
            ":checked": {"image_url": f"{self._icon_path}/radio_on_infinity.svg"},
        }

        with self.frame:
            with ui.VStack():
                for i in range(len(CurveInfinityTypes.InfinityTypeTokens)):
                    with ui.HStack(
                        height=20,
                        style=_check_box_style,
                        mouse_pressed_fn=(lambda x, y, b, m, index=i: self._set_pre_infinity_type(index)),
                    ):
                        ui.Label(self._get_pre_infinity_type_friendly_name(i), width=130)
                        ui.RadioButton(radio_collection=self._pre_collection, aligment=ui.Alignment.RIGHT)

                # vertical seperator
                ui.Line(
                    name="sep",
                    height=15,
                    alignment=ui.Alignment.V_CENTER,
                    style={"color": 0xFF707070, "border_width": 2, "margin": 2},
                )

                for i in range(len(CurveInfinityTypes.InfinityTypeTokens)):
                    with ui.HStack(
                        height=20,
                        style=_check_box_style,
                        mouse_pressed_fn=(lambda x, y, b, m, index=i: self._set_post_infinity_type(index)),
                    ):
                        ui.Label(self._get_post_infinity_type_friendly_name(i), width=130)
                        ui.RadioButton(radio_collection=self._post_collection, aligment=ui.Alignment.RIGHT)


class CurveEditorView:
    def __init__(self, _parent_window):
        self._list_panel = None
        self._timeline = omni.timeline.get_timeline_interface()
        self._usd_context = omni.usd.get_context()
        self._selection = self._usd_context.get_selection()
        self._style = TimelineMergeStyle.get_instance()
        self._user_track_list_width = TRACKLIST_MIN_WIDTH

        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(_parent_window._ext_id)
        self._icon_path = os.path.join(ext_path, "icons")

        self._live_session = TimelineLiveSession()
        self._timeline_view = CurveEditorTimeline(self, _parent_window)
        self._timeline_view.set_live_session(self._live_session)

        self._timeline_event_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
            WeakMethod(self._on_timeline_event)
        )

        self._utilities_menu = CurveEditorUtilitiesMenu(self._timeline_view)
        self._infinity_type_pushed_menu = InfinityTypeMenu(self)

        # Instance attributes should be defined in __init__
        self._selection_in_tangent_type_buttons = []
        self._selection_out_tangent_type_buttons = []
        self._selection_tangent_broken_buttons = []
        self._selection_tangent_weighted_buttons = []

        self._selection_value_model = SelectionKeyValueModel(self)
        self._selection_time_model = SelectionKeyTimeModel(self)
        self._selection_in_tangent_type_button_model = RadioButtonInTangentTypeModel(self)
        self._selection_out_tangent_type_button_model = RadioButtonOutTangentTypeModel(self)
        self._selection_tangent_broken_button_model = RadioButtonTangentBrokenModel(self)
        self._selection_tangent_weighted_button_model = RadioButtonTangentWeightedModel(self)
        self._key_movement_direction_combo_model = KeyMovementDirectionModel(self)

        SingletonCurveEditor.get_instance().set_ui_worker(self)

    def get_internal_usd_edit_scope(self):
        return SingletonCurveEditor.get_instance().usd_edit_scope()

    def get_omni_timeline_start_time_code(self):
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            selected_path = self._selection.get_selected_prim_paths()[0]
            node = omni.graph.core.get_node_by_path(selected_path)
            if node:
                return 0
            else:
                # this is a case by case fallback solution when saving scene. node is None
                pass

        return self._timeline.get_start_time() * self._timeline.get_time_codes_per_seconds()

    def get_omni_timeline_end_time_code(self):
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            selected_path = self._selection.get_selected_prim_paths()[0]
            node = omni.graph.core.get_node_by_path(selected_path)
            if node:
                length = node.get_attribute("inputs:length").get()
                frame_rate = node.get_attribute("inputs:framerate").get()
                return length * frame_rate
            else:
                # this is a case by case fallback solution when saving scene. node is None
                pass

        return self._timeline.get_end_time() * self._timeline.get_time_codes_per_seconds()

    def get_current_time_code(self):
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            return self._timeline_view._current_time
        else:
            return self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()

    def _on_timeline_event(self, evt):
        if evt.type == int(omni.timeline.TimelineEventType.START_TIME_CHANGED) or evt.type == int(
            omni.timeline.TimelineEventType.END_TIME_CHANGED
        ):
            self._get_curve_list_view()._update_omni_time_range()

    def _on_splitter_changed_x(self, xperc, frame):
        if self._timeline_view._scrubber._scrubber_top.dragging:
            self._splitter.offset_x.value = self._last_splitter_offset_x
            return

        self._last_splitter_offset_x = frame.offset_x.value
        x = xperc.value
        if x < TRACKLIST_MIN_WIDTH:
            frame.offset_x = TRACKLIST_MIN_WIDTH
        self._user_track_list_width = frame.offset_x
        self._search_bar_frame.width = frame.offset_x
        self._update_ui_timeline_view()

    def get_timeline_padding(self):  # pragma: no cover    Unused code
        if self._timeline_frame:
            padding = self._timeline_frame.screen_position_x
        else:
            padding = 0
            carb.log_warn("get_timeline_padding is not expected to be used now")

        return padding

    def get_style(self):
        return self._style.get_style()

    def get_curve_color(self, name: str):
        # find entry like "Curve.xformOp:scale:x" : {"color": 0xFF6060AA}, in the style file.
        style = self.get_style()
        if style.__contains__("Curve." + name):
            style = style["Curve." + name]
        elif style.__contains__("CurveGeneralColor"):
            style = style["CurveGeneralColor"]
        else:
            style = None

        if style and style.__contains__("color"):
            color = style["color"]
        else:
            # If there is no corresponding entry, cook a color from the name.
            color = int(hash(name))

            # Some colors that should be avoided
            bg_left_panel = 0xFF23211F
            bg_right_bright = 0xFF5C5C5C
            bg_right_dark = 0xFF454545

            # try to avoid color collision with background.
            threshold = 30.0
            while True:

                def color_difference(color0, color1):
                    r0 = color0 & 0x000000FF
                    g0 = (color0 & 0x0000FF00) >> 8
                    b0 = (color0 & 0x00FF0000) >> 16
                    r1 = color1 & 0x000000FF
                    g1 = (color1 & 0x0000FF00) >> 8
                    b1 = (color1 & 0x00FF0000) >> 16
                    rd = float(r0) - float(r1)
                    gd = float(g0) - float(g1)
                    bd = float(b0) - float(b1)
                    d = math.sqrt(rd * rd + gd * gd + bd * bd)
                    return d

                if (
                    (color_difference(color, bg_left_panel) > threshold)
                    and (color_difference(color, bg_right_bright) > threshold)
                    and (color_difference(color, bg_right_dark) > threshold)
                ):
                    break
                else:
                    # avoid dead loop anyway, even there might still be a color collsion theoretically.
                    threshold = threshold - 1.0
                    # hash the previous hash
                    color = int(hash(str(color)))

            # make a legal color value.
            color = (color & 0xFFFFFF) | 0xFF000000

        return color

    def get_current_user_prims(self):
        # temptest. might be removed.
        stage = self._usd_context.get_stage()
        if stage is None:
            return []
        return [
            stage.GetPrimAtPath(prim_path_str)
            for prim_path_str in SingletonCurveEditor.get_instance()._get_tracks_cache().get_users()
        ]

    def _update_with_timeline_node_mode(self):
        timeline_node_mode = self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode()

        self._timeline_view._scrubber_frame.visible = not timeline_node_mode

        self._new_curve_button.visible = timeline_node_mode
        self._add_key_button.visible = not timeline_node_mode
        self._copy_key_button.visible = not timeline_node_mode
        self._paste_key_button.visible = not timeline_node_mode

    def _update_ui_timeline_view(self):
        self._timeline_view.update_ui()

    def _retained_update(self, stage):
        self._timeline_view._retained_update(stage)

    def _ui_update_track_visibility(self, track, is_visible: bool):
        self._timeline_view._ui_update_track_visibility(track, is_visible)

    def _ui_raise_refit_and_update_flag(self):
        self._timeline_view._ui_raise_refit_and_update_flag()

    def _ui_add_track(self, stage, track):
        self._timeline_view._ui_add_track(stage, track)

    def _ui_remove_track(self, track):
        self._timeline_view._ui_remove_track(track)

    def update_ui(self):
        # ui update. left panel ui update is not here but implemented in PrimPanel.
        self._update_ui_timeline_view()

    def build_ui(self):
        with ui.VStack(style=self.get_style()):
            # Top: build the toolbar in a frame with clipping so it doesn't determine minimum size of the stack
            with ui.Frame(horizontal_clipping=True, build_fn=self._build_toolbar_as_build_fn):
                # do _build_toolbar immediately for the first time so that things like _update_ui_clear_selection() handle solid ui widgets.
                self._build_toolbar()
            # Bottom: the prim panel and the timeline
            with ui.HStack():
                with ui.ZStack(width=0):
                    # Left panel
                    self._build_ui_left_panel()
                    # Draggable splitter
                    placer = ui.Placer(draggable=True, drag_axis=ui.Axis.X, offset_x=self._user_track_list_width)
                    self._last_splitter_offset_x = placer.offset_x.value
                    self._splitter = placer
                    with placer:
                        ui.Rectangle(width=SPLITTER_WIDTH, name="Splitter")
                    placer.set_offset_x_changed_fn(lambda x, frame=placer: self._on_splitter_changed_x(x, frame))
                # Right panel
                self._build_ui_timeline_frame()

        self.update_ui()

    def _build_ui_left_panel(self):
        # Side panel with the table of contents
        self._list_panel = PrimPanel(self)

    def _get_curve_list_view(self):
        return self._timeline_view._get_curve_list_view()

    def _on_fit_all(self):
        self._timeline_view._on_fit_all()

    def _on_fit_selection(self):
        self._timeline_view._on_fit_selection()

    def _on_fit_conditionally(self):
        self._timeline_view._on_fit_conditionally()

    def _on_delete_key(self):
        self._get_curve_list_view()._command_delete_key()

    def _on_add_key(self, timecode):
        self._get_curve_list_view()._command_add_key(timecode)

    def _on_copy_key(self):
        self._get_curve_list_view()._command_copy_key()

    def _on_paste_key(self, timecode):
        self._get_curve_list_view()._command_paste_key(timecode)

    def _on_new_curve(self):
        def close_window():
            new_curve_dialog.visible = False

        def do_new_curve():
            if self._get_curve_list_view()._command_new_curve(get_ui_string(), get_ui_number()) == True:
                close_window()
            else:
                nm.post_notification("Can not create curve attribute", status=nm.NotificationStatus.WARNING, duration=5)

        def get_ui_string() -> str:
            return new_name_widget.model.get_value_as_string()

        def get_ui_number() -> int:
            return new_components_number.model.get_item_value_model().get_value_as_int() + 1

        new_curve_dialog = ui.Window(
            "New Curve",
            width=200,
            height=100,
            flags=ui.WINDOW_FLAGS_NO_RESIZE | ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_MODAL,
        )

        with new_curve_dialog.frame:
            with ui.VStack(
                height=0,
                spacing=5,
                name="top_level_stack",
                style={"VStack::top_level_stack": {"margin": 5}, "Button": {"margin": 0}},
            ):
                with ui.HStack(spacing=5):
                    new_name_widget = ui.StringField(tooltip="Curve Name")
                    new_name_widget.focus_keyboard()

                    # components. x or xy or xyz or xyzw
                    with ui.VStack(width=45):
                        new_components_number = ui.ComboBox(0, "1", "2", "3", "4", tooltip="Components Number")

                ui.Spacer(width=5, height=5)
                with ui.HStack(spacing=5):
                    ui.Button("Ok", clicked_fn=do_new_curve)
                    ui.Button("Cancel", clicked_fn=close_window)

    def command_set_key_movement_direction(self, key_movement_type: int):
        self._get_curve_list_view()._command_set_key_movement_direction(key_movement_type)

    def command_set_tangent_broken(self, is_tangent_broken: bool):
        self._get_curve_list_view()._command_set_tangent_broken(is_tangent_broken)

    def command_set_tangent_weighted(self, is_tangent_weighted: bool):
        self._get_curve_list_view()._command_set_tangent_weighted(is_tangent_weighted)

    def command_set_infinity_type(self, infinity_type, is_pre_infinity: bool):
        self._get_curve_list_view()._command_set_infinity_type(infinity_type, is_pre_infinity)

    def command_set_in_tangent_type(self, type: int):
        self._get_curve_list_view()._command_set_in_tangent_type(type)

    def command_set_out_tangent_type(self, type: int):
        self._get_curve_list_view()._command_set_out_tangent_type(type)

    def command_set_selection_value(self, value: float):
        self._get_curve_list_view()._command_set_selection_value(value)

    def command_set_selection_time(self, time: float):
        self._get_curve_list_view()._command_set_selection_time(time)

    def show_selection_value(self, value: float):
        self._selection_value_model.set_selected_value(True, value)

    def show_selection_time(self, time: float):
        self._selection_time_model.set_selected_time(True, time)

    # type can be None for special case to hide it.
    def show_in_tangent_type(self, type: int):
        if type == None:
            visible = False
            self._selection_in_tangent_type_button_model.set_value_none()
        else:
            self._selection_in_tangent_type_button_model.set_value(type)
            visible = True

        for radio_button in self._selection_in_tangent_type_buttons:
            radio_button.visible = visible

    # type can be None for special case to hide it.
    def show_out_tangent_type(self, type: int):
        if type == None:
            visible = False
            self._selection_out_tangent_type_button_model.set_value_none()
        else:
            self._selection_out_tangent_type_button_model.set_value(type)
            visible = True

        for radio_button in self._selection_out_tangent_type_buttons:
            radio_button.visible = visible

    # index can be None for special case to hide it.
    def show_tangent_broken(self, index: int):
        if index == None:
            visible = False
            self._selection_tangent_broken_button_model.set_value_none()
        else:
            self._selection_tangent_broken_button_model.set_value(index)
            visible = True

        for radio_button in self._selection_tangent_broken_buttons:
            radio_button.visible = visible

    # index can be None for special case to hide it.
    def show_tangent_weighted(self, index: int):
        if index == None:
            visible = False
            self._selection_tangent_weighted_button_model.set_value_none()
        else:
            self._selection_tangent_weighted_button_model.set_value(index)
            visible = True

        for radio_button in self._selection_tangent_weighted_buttons:
            radio_button.visible = visible

    def show_pre_infinity_type(self, infinity_type):
        self._infinity_type_button.enabled = True
        self._infinity_type_pushed_menu.check_pre_infinity_type(infinity_type)

    def show_post_infinity_type(self, infinity_type):
        self._infinity_type_button.enabled = True
        self._infinity_type_pushed_menu.check_post_infinity_type(infinity_type)

    def _build_vertical_separator(self, name: str):
        ui.Line(
            name=name,
            width=15,
            alignment=ui.Alignment.H_CENTER,
            style={"color": 0xFF707070, "border_width": 2, "margin": 2},
        )

    def _build_tangent_type_buttons(self):
        # Start with a lable
        with ui.HStack(alignment=ui.Alignment.LEFT):
            ui.Label("Edit Tangent")

            in_collection = ui.RadioCollection(self._selection_in_tangent_type_button_model)
            out_collection = ui.RadioCollection(self._selection_out_tangent_type_button_model)

            # paired names and resources
            names = ["Auto", "Smooth", "Flat", "Fixed", "Linear", "Step"]
            resources = [
                "auto_tangent.svg",
                "smooth_tangent.svg",
                "flat_tangent.svg",
                "fixed_tangent.svg",
                "linear_tangent.svg",
                "step_tangent.svg",
            ]

            # on image is translucent. off image is transparent.
            radio_button_style = {
                "": {"background_color": 0x0, "image_url": f"{self._icon_path}/radio_off.svg"},
                ":checked": {"image_url": f"{self._icon_path}/radio_on.svg"},
            }

            # radio button on top of icon button. The effective layout after experiment.
            for i in range(len(names)):
                # hide Fixed tangent type button according to designer's request. The button works if it is not hidden.
                button_invisible = i == 3 and names[i] == "Fixed"

                with ui.ZStack(width=TOOLBAR_BUTTON_SIZE, alignment=ui.Alignment.LEFT, visible=not button_invisible):
                    self._build_toolbar_button(
                        names[i],
                        lambda x, y, button, modifier, type=i: self._on_button_tangent_type(type),
                        f"{self._icon_path}/" + resources[i],
                    )
                    self._selection_in_tangent_type_buttons.append(
                        ui.RadioButton(
                            radio_collection=in_collection,
                            width=TOOLBAR_BUTTON_SIZE,
                            height=TOOLBAR_BUTTON_SIZE,
                            style=radio_button_style,
                            alignment=ui.Alignment.LEFT,
                        )
                    )
                    self._selection_out_tangent_type_buttons.append(
                        ui.RadioButton(
                            radio_collection=out_collection,
                            width=TOOLBAR_BUTTON_SIZE,
                            height=TOOLBAR_BUTTON_SIZE,
                            style=radio_button_style,
                            alignment=ui.Alignment.LEFT,
                        )
                    )

    def _build_tangent_broken_buttons(self):
        with ui.HStack():
            # Add a Label per design doc
            collection = ui.RadioCollection(self._selection_tangent_broken_button_model)

            # paired names and resources
            names = ["Unbroken", "Broken"]
            resources = ["Unbroken_tangent.svg", "Broken_tangent.svg"]

            # on image is translucent. off image is transparent.
            radio_button_style = {
                "": {"background_color": 0x0, "image_url": f"{self._icon_path}/radio_off.svg"},
                ":checked": {"image_url": f"{self._icon_path}/radio_on.svg"},
            }

            # radio button on top of icon button. The effective layout after experiment.
            for i in range(len(names)):
                with ui.ZStack(width=TOOLBAR_BUTTON_SIZE, alignment=ui.Alignment.LEFT):
                    self._build_toolbar_button(
                        names[i],
                        lambda x, y, button, modifier, index=i: self._on_button_tangent_broken(index),
                        f"{self._icon_path}/" + resources[i],
                    )
                    self._selection_tangent_broken_buttons.append(
                        ui.RadioButton(
                            radio_collection=collection,
                            width=TOOLBAR_BUTTON_SIZE,
                            height=TOOLBAR_BUTTON_SIZE,
                            style=radio_button_style,
                            alignment=ui.Alignment.LEFT,
                        )
                    )
            ui.Spacer()

    def _build_tangent_weighted_buttons(self):
        collection = ui.RadioCollection(self._selection_tangent_weighted_button_model)

        # paired names and resources
        names = ["Non-weighted", "Weighted"]
        resources = ["non_weighted_tangent.svg", "weighted_tangent.svg"]

        # on image is translucent. off image is transparent.
        radio_button_style = {
            "": {"background_color": 0x0, "image_url": f"{self._icon_path}/radio_off.svg"},
            ":checked": {"image_url": f"{self._icon_path}/radio_on.svg"},
        }

        # radio button on top of icon button. The effective layout after experiment.
        for i in range(len(names)):
            with ui.ZStack(width=TOOLBAR_BUTTON_SIZE, alignment=ui.Alignment.LEFT):
                self._build_toolbar_button(
                    names[i],
                    lambda x, y, button, modifier, index=i: self._on_button_tangent_weighted(index),
                    f"{self._icon_path}/" + resources[i],
                )
                self._selection_tangent_weighted_buttons.append(
                    ui.RadioButton(
                        radio_collection=collection,
                        width=TOOLBAR_BUTTON_SIZE,
                        height=TOOLBAR_BUTTON_SIZE,
                        style=radio_button_style,
                        alignment=ui.Alignment.LEFT,
                    )
                )

    def _build_toolbar_button(self, text, mouse_pressed_fn, icon_path=None):
        style = {
            "Button": {
                "stack_direction": ui.Direction.LEFT_TO_RIGHT,
                "alignment": ui.Alignment.LEFT,
            },
            "Button.Image": {
                # "color": 0xFFFFCC99,
                "image_url": f"{icon_path}",
                "alignment": ui.Alignment.CENTER,
            },
            "Button.Label": {"alignment": ui.Alignment.CENTER},
        }

        return ui.Button(
            text="",
            style=style,
            width=TOOLBAR_BUTTON_SIZE,
            height=TOOLBAR_BUTTON_SIZE,
            mouse_pressed_fn=mouse_pressed_fn,
            tooltip=text,
            alignment=ui.Alignment.LEFT,
            name=text,
        )

    def _on_button_tangent_type(self, type):
        with omni.kit.undo.group():
            self._selection_in_tangent_type_button_model.command_set_value(type)
            self._selection_out_tangent_type_button_model.command_set_value(type)

    def _on_button_tangent_broken(self, index):
        self._selection_tangent_broken_button_model.command_set_value(index)

    def _on_button_tangent_weighted(self, index):
        self._selection_tangent_weighted_button_model.command_set_value(index)

    def _on_button_previous_frame(self):  # pragma: no cover    Unused code
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            self._timeline_view._timeline_event_set_time(self._timeline_view._current_time - 1)
        else:
            playing = self._timeline.is_playing()
            time = self._timeline.get_tentative_time()
            new_time = time - (1.0 / self._timeline.get_time_codes_per_seconds())
            self._timeline.set_current_time(new_time)
            if playing:
                self._timeline.pause()

    def _on_button_next_frame(self):  # pragma: no cover    Unused code
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            self._timeline_view._timeline_event_set_time(self._timeline_view._current_time + 1)
        else:
            playing = self._timeline.is_playing()
            time = self._timeline.get_tentative_time()
            new_time = time + (1.0 / self._timeline.get_time_codes_per_seconds())
            self._timeline.set_current_time(new_time)
            if playing:
                self._timeline.pause()

    def _on_button_previous_key_frame(self):
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            # do not know what to do exactly.
            pass
        else:
            playing = self._timeline.is_playing()
            time_code = self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()
            new_time_code = self._get_curve_list_view()._get_previous_key_time(time_code)
            self._timeline.set_current_time(new_time_code / self._timeline.get_time_codes_per_seconds())
            if playing:
                self._timeline.pause()

    def _on_button_next_key_frame(self):
        if self._timeline_view._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            # do not know what to do exactly.
            pass
        else:
            playing = self._timeline.is_playing()
            time_code = self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()
            new_time_code = self._get_curve_list_view()._get_next_key_time(time_code)
            self._timeline.set_current_time(new_time_code / self._timeline.get_time_codes_per_seconds())
            if playing:
                self._timeline.pause()

    def _on_button_play(self):  # pragma: no cover    Unused code
        if self._timeline.is_playing():
            self._timeline.pause()
        else:
            self._timeline.play()

    def _on_button_looping(self):
        self._timeline.set_looping(not self._timeline.is_looping())

    def _on_button_infinity_type(self):
        if not self._infinity_type_button.enabled:
            return  # do nothing

        # toggle menu show/hide, by clicking on the button again
        if self._infinity_type_pushed_menu.visible:
            self._infinity_type_pushed_menu.visible = False
        else:
            self._infinity_type_pushed_menu.show_at(
                int(self._infinity_type_button.screen_position_x),
                int(self._infinity_type_button.screen_position_y + self._infinity_type_button.computed_content_height),
            )

    def _on_button_simplify(self):  # pragma: no cover    Unused code
        self._get_curve_list_view()._command_simplify_curves()

    def _on_button_utilities_menu(self):  # pragma: no cover    Unused code
        self._utilities_menu.show()
        return

    def _on_search_bar_changed(self, _):
        self._togle_search_bar_tip_visibility()
        hack_event = SelectionChangedEvent()
        hack_event.search_bar_text = self._search_bar.model.get_value_as_string().strip()
        self._list_panel._on_stage_event(hack_event)

    def _togle_search_bar_tip_visibility(self, hovered: bool = False):
        search_bar_text: str = self._search_bar.model.get_value_as_string()
        if hovered:
            self._search_bar_tip.visible = False

        else:
            if search_bar_text:
                self._search_bar_tip.visible = False
            else:
                self._search_bar_tip.visible = True

    def _clear_search_bar(self):  # pragma: no cover    Unused code
        self._search_bar.model.set_value("")

    def _build_toolbar(self):
        with ui.HStack(height=32, margin=0):
            with ui.HStack(height=32, margin=0):
                """
                ToolBar Part 1: Search bar
                """
                self._search_bar_frame = ui.VStack(width=self._user_track_list_width)
                with self._search_bar_frame:
                    ui.Spacer(height=10)  # Adjust the vertical padding
                    with ui.ZStack():
                        self._search_bar = ui.StringField(
                            tooltip="Search Bar",
                            mouse_hovered_fn=self._togle_search_bar_tip_visibility,
                            height=16,
                            name="Search Bar",
                        )
                        self._search_bar_tip = ui.Label(
                            "   Search",
                            mouse_hovered_fn=self._togle_search_bar_tip_visibility,
                            height=20,
                            name="Search Bar Tip",
                        )
                        # self._search_bar_clear_btn = ui.Button(text='x', clicked_fn=self._clear_search_bar)
                        self._search_bar.model.add_value_changed_fn(self._on_search_bar_changed)

                self._build_vertical_separator("SearchBarSeparator")

                self._new_curve_button = self._build_toolbar_button(
                    "New Float Curve Then RMB on the graph to add a key at the mouse pointers location",
                    lambda x, y, button, modifier: self._on_new_curve(),
                    f"{self._icon_path}/create_curve_dark.svg",
                )
                ui.Spacer(width=10)

                """
                ToolBar Part 2: Time and Value
                """
                ui.Label("Frame", width=40)
                with ui.VStack(width=60):
                    ui.Spacer(height=10)
                    self._time_string = ui.StringField(
                        self._selection_time_model,
                        width=60,
                        height=16,
                        style_type_name_override="Tools.TextField",
                        tooltip="Key's time",
                    )

                ui.Spacer(width=5)
                ui.Label("Value", width=40)
                with ui.VStack(width=60):
                    ui.Spacer(height=10)
                    self._value_string = ui.StringField(
                        self._selection_value_model,
                        width=60,
                        height=16,
                        style_type_name_override="Tools.TextField",
                        tooltip="Key's value",
                    )

                """
                ToolBar Part 3: buttons
                """

                self._add_key_button = self._build_toolbar_button(
                    "add keys to the selected curves",
                    lambda x, y, button, modifier: self._on_add_key(self.get_current_time_code()),
                    f"{self._icon_path}/Add_Key.svg",
                )
                self._del_key_button = self._build_toolbar_button(
                    "delete the selected keys",
                    lambda x, y, button, modifier: self._on_delete_key(),
                    f"{self._icon_path}/Delete_Key.svg",
                )
                self._copy_key_button = self._build_toolbar_button(
                    "copy the selected keys",
                    lambda x, y, button, modifier: self._on_copy_key(),
                    f"{self._icon_path}/Copy_Key.svg",
                )
                self._paste_key_button = self._build_toolbar_button(
                    "paste the copied keys",
                    lambda x, y, button, modifier: self._on_paste_key(self.get_current_time_code()),
                    f"{self._icon_path}/Paste_Key.svg",
                )

                self._build_vertical_separator("FirstSeparator")

                self._build_tangent_type_buttons()

                self._build_vertical_separator("SecondSeparator")

                self._build_tangent_weighted_buttons()

                self._build_vertical_separator("ThirdSeparator")

                self._build_tangent_broken_buttons()

                self._build_vertical_separator("ForthSeparator")

            with ui.HStack(height=32, margin=0):
                ui.Spacer(width=10)
                with ui.VStack(width=100):
                    ui.Spacer(height=10)
                    # Hey, it's a ComboBox, but we only use its appearance.
                    self._infinity_type_button = ui.ComboBox(
                        0, "Cycle", enabled=False, tooltip="Set selected curve(s) cycle options"
                    )
                # The actual menu is a ui.Window
                self._infinity_type_button.set_mouse_pressed_fn(
                    lambda x, y, button, modifier: self._on_button_infinity_type()
                )

                self._build_vertical_separator("FifthSeparator")
                # navigation buttons
                self._build_toolbar_button(
                    "Frame All(CTRL+F)",
                    lambda x, y, button, modifier: self._on_fit_all(),
                    f"{self._icon_path}/frame_all.svg",
                )
                self._build_toolbar_button(
                    "Frame Selected(F)",
                    lambda x, y, button, modifier: self._on_fit_conditionally(),
                    f"{self._icon_path}/frame_selection.svg",
                )

                ui.Spacer()
                with ui.VStack(width=80):
                    ui.Spacer(height=10)
                    self._key_movement_direction_combo = ui.ComboBox(
                        self._key_movement_direction_combo_model,
                        alignment=ui.Alignment.RIGHT,
                        visible=True,
                        tooltip="Key Movement Constraint",
                        name="Key Movement Constraint Menu",
                    )
                button_style = {
                    # "Button": {"background_color": 0x00000000},
                    # "Button:hovered": {"background_color": 0xFF333333},
                    "margin_height": 2,
                    "margin_width": 0,
                    "alignment": ui.Alignment.CENTER_BOTTOM,
                }
                ui.Spacer(width=2)
                self._option_button = ui.Button(
                    "",
                    name="options button",
                    width=24,
                    height=32,
                    image_url="resources/icons/details_options.png",
                    image_width=14,
                    clicked_fn=self._utilities_menu.show,
                    style=button_style,
                    alignment=ui.Alignment.CENTER_BOTTOM,
                )

    # I am not sure when _build_toolbar_as_build_fn is called( for example, toggle "Curve Editor" window visibility). In order to not miss _update_with_timeline_node_mode, just force _update_with_timeline_node_mode after _build_toolbar.
    def _build_toolbar_as_build_fn(self):
        self._build_toolbar()
        self._update_with_timeline_node_mode()

    # just follow sequencer's timeline use.
    def _build_ui_timeline_frame(self):
        with ui.VStack(content_clipping=True):
            self._timeline_frame = ui.Frame(separate_window=True)
            with self._timeline_frame:
                with ui.HStack(content_clipping=True):
                    self._timeline_view.build_ui()

    def _update_ui_clear_selection(self):
        self._selection_value_model.set_selected_value(False, 0.0)
        self._selection_time_model.set_selected_time(False, 0.0)
        self.show_in_tangent_type(None)
        self.show_out_tangent_type(None)
        self.show_tangent_broken(None)
        self.show_tangent_weighted(None)
        self._infinity_type_button.enabled = False

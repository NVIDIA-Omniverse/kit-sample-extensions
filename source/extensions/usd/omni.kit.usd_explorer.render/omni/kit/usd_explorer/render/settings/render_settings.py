import asyncio
import webbrowser
from collections import OrderedDict
from typing import Union

import carb
import omni.kit
import omni.kit.menu.utils
import omni.kit.ui
import omni.ui as ui
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.widgets.custom import (
    COLORS,
    DarkColors,
    EditEventIntModel,
    FloatSliderEx,
    FloatSpinner,
    FontSize,
    LightColors,
    MouseKey,
    SpaceComboBox,
    Switch,
    SwitchOrCheckbox,
    UpdateEventHelper,
    delay_execute_by_frame,
    get_ui_style,
)
from omni.ui import color as cl

from ..common import ICON_PATH
from ..preset import get_render_preset_instance
from .window_base import WindowBase

EXTENSION_NAME = "Design Render Settings"
WIDGET_WIDTH = 185
WIDGET_HEIGHT = 28

COLLAPSED_FRAMES = False


class RenderItemType:
    COMBO = 0
    SWITCH = 1
    SWITCH_COMBO = 2
    SWITCH_DRAG = 3
    SPIN = 4
    FIELD = 5
    SWITCH_FIELD = 6


class RenderItemInfo:
    def __init__(
        self,
        name: str,
        item_type: RenderItemType,
        switch_path: str,
        value_path: Union[str, list],
        drag_step: float,
        drag_min: float,
        drag_max: float,
        combo_list: list = [],
        readonly: bool = False,
    ):
        self.name = name
        self.item_type = item_type
        self.switch_path = switch_path
        self.value_path = value_path
        self.drag_step = drag_step
        self.drag_min = drag_min
        self.drag_max = drag_max
        self.combo_list = combo_list
        if len(combo_list) > 0 and combo_list[0].find(": ") > 0:
            # Each of the value in combo_list is:
            # setting_value[: display_value]
            self.combo_list_display = []
            self.combo_list = []
            for i in range(len(combo_list)):
                key_value_pair = combo_list[i].split(": ")
                self.combo_list.append(key_value_pair[0])
                if len(key_value_pair) > 1:
                    self.combo_list_display.append(key_value_pair[1])
                else:
                    self.combo_list_display.append(key_value_pair[0])

        else:
            self.combo_list_display = combo_list

        self.readonly = readonly


class RenderItem:
    FONT_SIZE = 14
    BORDER_RADIUS = 3
    PADDING = 5
    cl.shade(0xFFE6E6E6, light=0xFFD6D6D6, name="render_setting_text")
    cl.shade(0xFF444444, light=0xFF444444, name="render_setting_disable_text")
    cl.shade(0xFF24211F, light=0xFF545454, name="render_setting_background")
    cl.shade(0xFF545454, light=0xFF545454, name="render_setting_green")
    STYLE = {
        "ComboBox": {
            "font_size": FONT_SIZE,
            "color": cl.render_setting_text,
            "background_color": cl.render_setting_background,
            "border_radius": BORDER_RADIUS,
            "secondary_padding": PADDING,
        },
        "Slider": {
            "font_size": FONT_SIZE,
            "color": cl.render_setting_text,
            "border_radius": BORDER_RADIUS,
            "background_color": cl.render_setting_background,
            "secondary_color": cl.render_setting_green,
            "draw_mode": ui.SliderDrawMode.FILLED,
        },
        "Slider:disabled": {
            "font_size": FONT_SIZE,
            "color": cl.render_setting_disable_text,
            "border_radius": BORDER_RADIUS,
            "background_color": cl.render_setting_background,
            "secondary_color": cl.render_setting_green,
            "draw_mode": ui.SliderDrawMode.FILLED,
        },
        "Field": {"background_color": cl.render_setting_background, "color": cl.render_setting_text},
        "Label::unit": {"color": cl.render_setting_disable_text, "font_size": 16},
    }

    def __init__(self, info: RenderItemInfo, pick_combo=None, switch_change=None, slider_change=None):
        self._info = info
        self._combo_width = WIDGET_WIDTH
        self._combobox = None
        self._slider = None
        self._spin = None
        self._field = None
        self._switch = None
        self._pick_combo_cb = pick_combo
        self._on_switch_fn_cb = switch_change
        self._on_slider_changed_cb = slider_change
        self._settings = carb.settings.get_settings()
        self._preset = get_render_preset_instance()
        self._is_camobo_int = False
        with ui.HStack(height=WIDGET_HEIGHT, style=RenderItem.STYLE):
            with ui.HStack(width=ui.Percent(40)):
                ui.Spacer(width=15)
                ui.Label(info.name, width=150, height=WIDGET_HEIGHT, alignment=ui.Alignment.LEFT_CENTER)
            with ui.HStack():
                ui.Spacer(width=15)
                if info.item_type == RenderItemType.COMBO:
                    ui.Spacer(width=3, height=WIDGET_HEIGHT)
                    self._build_combo()
                    self._combobox.enabled = not self._info.readonly
                if info.item_type == RenderItemType.SWITCH:
                    self._build_switch()
                    self._switch.enabled = not self._info.readonly
                if info.item_type == RenderItemType.SWITCH_COMBO:
                    self._build_switch_cambo()
                    self._switch.enabled = not self._info.readonly
                    self._combobox.enabled = self._combobox.enabled and not self._info.readonly
                if info.item_type == RenderItemType.SWITCH_FIELD:
                    self._build_switch_field()
                    self._switch.enabled = not self._info.readonly
                    self._field.enabled = self._field.enabled and not self._info.readonly
                if info.item_type == RenderItemType.SWITCH_DRAG:
                    self._build_switch_drag()
                    self._switch.enabled = not self._info.readonly
                    self._slider.enabled = self._slider.enabled and not self._info.readonly
                if info.item_type == RenderItemType.SPIN:
                    self._build_spin()
                    self._spin.enabled = not self._info.readonly
                if info.item_type == RenderItemType.FIELD:
                    self._build_field()
                    self._field.enabled = not self._info.readonly

                ui.Spacer(width=10)

    def _build_switch_field(self):
        enabled = self._build_switch()
        ui.Spacer(width=8, height=WIDGET_HEIGHT)
        self._build_field(enabled)

    def _build_field(self, enabled=True):
        with ui.ZStack(height=WIDGET_HEIGHT):
            self._field_model = EditEventIntModel(self._on_field_changed_begin, self._on_field_changed_end)
            value = self._settings.get(self._info.value_path)
            self._field_model.set_value(value)
            self._field = ui.IntField(self._field_model, height=WIDGET_HEIGHT, alignment=ui.Alignment.LEFT_CENTER)
            self._field.enabled = enabled
            new_style = {"Field": {"background_color": cl.render_setting_background, "color": cl.render_setting_text}}
            new_style["Field"]["color"] = cl.render_setting_background
            self._field.set_style(new_style)
            with ui.HStack(height=WIDGET_HEIGHT):
                ui.Spacer(width=5)
                self._field_value_label = ui.Label(
                    str(value), name="value", height=WIDGET_HEIGHT, alignment=ui.Alignment.LEFT_CENTER
                )
            with ui.HStack(height=WIDGET_HEIGHT):
                self._field_unit_label = ui.Label(
                    "per Pixel", name="unit", height=WIDGET_HEIGHT, alignment=ui.Alignment.RIGHT_CENTER
                )
                ui.Spacer(width=5)

    def _on_field_changed_begin(self, model):
        self._field_value_label.text = ""
        new_style = self._field.style
        new_style["Field"]["color"] = cl.render_setting_text
        self._field.set_style(new_style)

    def _on_field_changed_end(self, model):
        value = model.as_int
        self._field_value_label.text = str(value)
        new_style = self._field.style
        new_style["Field"]["color"] = cl.render_setting_background
        self._field.set_style(new_style)
        if self._info.value_path:
            self.update_setting_value(self._info.value_path, value)

    def update_setting_value(self, path, value):
        # OM-39875: iray is special, we update it in _pick_render
        if value == "iray" and self._info.value_path == "/rtx/rendermode":
            return
        if path != "/rtx/renderpreset":
            self._preset.update_current_value(path, value)
        if self._settings.get(path) != value:
            self._settings.set(path, value)

    def _build_spin(self):
        with ui.HStack(height=WIDGET_HEIGHT):
            ui.Spacer(width=40, height=WIDGET_HEIGHT)
            value = 0
            if self._info.value_path:
                if isinstance(self._info.value_path, list):
                    value = self._settings.get(self._info.value_path[0])
                if isinstance(self._info.value_path, str):
                    value = self._settings.get(self._info.value_path)
            self._spin = FloatSpinner(self._on_spin_field_changed, value=value, step=self._info.drag_step, height=24)
            ui.Spacer(width=5, height=WIDGET_HEIGHT)
            ui.Label("per Pixel", width=22, height=WIDGET_HEIGHT, alignment=ui.Alignment.LEFT_CENTER)

    def _on_spin_field_changed(self, value):
        if value < self._info.drag_min:
            value = self._info.drag_min
            self._spin._float_widget.model.set_value(value)
        if value > self._info.drag_max:
            value = self._info.drag_max
            self._spin._float_widget.model.set_value(value)

        # self._settings.set(self._info.value_path, int(value))
        self.update_setting_value(self._info.value_path, int(value))

    def on_update(self, dt):
        if self._spin:
            self._spin.on_update(dt)
        return True

    def _build_combo(self, width=WIDGET_WIDTH, enabled=True):
        select_index = 0
        if self._info.combo_list and self._info.combo_list[0] != "None" and self._info.value_path:
            value = self._settings.get(self._info.value_path)
            # Must consider two type of combo values
            if isinstance(value, int):
                select_index = value
                self._is_camobo_int = True
            if isinstance(value, str):
                select_index = self._info.combo_list.index(value)
        with ui.VStack(height=WIDGET_HEIGHT):
            self._combobox = SpaceComboBox(
                int(select_index),
                *self._info.combo_list_display,
                # width=width,
                height=WIDGET_HEIGHT,
                alignment=ui.Alignment.LEFT_CENTER,
            )
            self._combobox.model.add_item_changed_fn(self._pick_combo)
            self._combobox.enabled = enabled

    def _pick_combo(self, *_):
        idx = self._combobox.model.get_item_value_model().as_int
        value = self._info.combo_list[idx]
        if self._info.value_path:
            if self._is_camobo_int:
                # self._settings.set(self._info.value_path, idx)
                self.update_setting_value(self._info.value_path, idx)
            else:
                # self._settings.set(self._info.value_path, value)
                self.update_setting_value(self._info.value_path, value)
        if self._pick_combo_cb:
            self._pick_combo_cb(value)

    def _build_switch(self):
        switch_status = True
        if self._info.switch_path:
            switch_status = self._settings.get(self._info.switch_path)
        self._switch = SwitchOrCheckbox(switch_status, self._on_switch_changed)
        return switch_status

    def change_switch_status(self, status):
        if self._switch:
            self._switch.status = status

    def _build_switch_cambo(self):
        enabled = self._build_switch()
        ui.Spacer(width=8, height=WIDGET_HEIGHT)
        self._build_combo(self._combo_width - 35, enabled)

    def _build_switch_drag(self):
        if self._info.value_path:
            if isinstance(self._info.value_path, list):
                # OM-39606: since onle one value displayed, set others with same value
                for index, path in enumerate(self._info.value_path):
                    if index == 0:
                        value = self._settings.get(path)
                    else:
                        self._settings.set(path, value)
            if isinstance(self._info.value_path, str):
                value = self._settings.get(self._info.value_path)
        else:
            value = 0

        enabled = self._build_switch()
        ui.Spacer(width=8, height=WIDGET_HEIGHT)
        with ui.VStack(height=WIDGET_HEIGHT):
            ui.Spacer()
            self._slider = ui.FloatSlider(
                min=self._info.drag_min, max=self._info.drag_max, step=self._info.drag_step, height=WIDGET_HEIGHT - 5
            )
            ui.Spacer()
        self._slider.model.set_value(value)
        self._slider.model.add_value_changed_fn(self._on_slider_changed)
        self._slider.enabled = enabled

    def _on_slider_changed(self, model):
        value = model.get_value_as_float()
        if self._info.value_path:
            if isinstance(self._info.value_path, str):
                # self._settings.set(self._info.value_path, value)
                self.update_setting_value(self._info.value_path, value)
            if isinstance(self._info.value_path, list):
                for path in self._info.value_path:
                    # self._settings.set(path, value)
                    self.update_setting_value(path, value)
        if self._on_slider_changed_cb:
            self._on_slider_changed_cb(value)

    def _on_switch_changed(self, status):
        if self._info.switch_path:
            self.update_setting_value(self._info.switch_path, status)
        if self._on_switch_fn_cb:
            self._on_switch_fn_cb(status)
        if self._slider is not None:
            self._slider.enabled = status
        if self._combobox is not None:
            self._combobox.enabled = status
        if self._field is not None:
            self._field.enabled = status


class RenderSettingWindow(WindowBase):
    MENU_PATH = f"Window/Render Settings"
    WINDOW_WIDTH = 0
    WINDOW_HEIGHT = 190

    def __init__(self):
        self._option_menu = None
        self._frame = None
        self._preset = get_render_preset_instance()  # RenderPreset()
        self._preset.update_setting_panel(self)
        self._settings = carb.settings.get_settings()
        self._current_navigation = False
        self._need_rebuild = False
        self._spins = []
        super().__init__(
            EXTENSION_NAME,  # Title & window name
            ui.DockPreference.DISABLED,  # Dock
            0,  # Width
            RenderSettingWindow.WINDOW_HEIGHT,  # Height
            True,  # Resizable
        )
        self._window.set_visibility_changed_fn(self._on_visibility_changed)
        self._exposure_control = None
        self._exposure_changed_sub = self._settings.subscribe_to_node_change_events(
            "/rtx/post/histogram/enabled", self._on_exposure_enable_setting_changed
        )
        UpdateEventHelper.get_instance().register_update(self)
        self._prev_render_mode = None

        self.__register_menu()

    def destroy(self):
        self.__deregister_menu()
        self._exposure_changed_sub = None
        self._exposure_control = None

    def hide(self, *_):
        self.show(False)

    # This function will dock this panel window (according to its dock preference)
    # Now unused.
    def dock(self, position):
        return True

    def _delay_rebuild(self):
        if self._frame:
            self._frame.clear()
            with self._frame:
                self._add_items()

        # Refresh menu
        omni.kit.menu.utils.rebuild_menus()

        return True

    # update fast nvigation
    def on_update(self, dt):
        for spin in self._spins:
            spin.on_update(dt)
        navigation = self._settings.get("/renderer/eco_mode_enable")
        if navigation == self._current_navigation:
            return True
        self._current_navigation = navigation
        self.rebuild()
        return True

    # don't do any ui change operation in call back function
    def _pick_preset(self, value):
        self._preset.set(value)

    def _pick_render(self, value):
        self._preset.update_custom_value("/rtx/rendermode", value)
        setting = carb.settings.get_settings()
        viewport_api = get_active_viewport(omni.usd.get_context())
        if value == "iray":
            self._prev_render_mode = setting.get_as_string("/rtx/rendermode")
            # self._preset.set("Custom")
            if viewport_api:
                viewport_api.set_hd_engine("iray")
            setting.set("/rtx/rendermode", "iray")
            setting.set("/iray/rendermode", "iray")
            # setting.set("/renderer/active", "iray")
        else:
            if self._prev_render_mode:
                # We are switching away from iray
                setting.set("/rtx/rendermode", self._prev_render_mode)
                if viewport_api:
                    viewport_api.set_hd_engine("rtx")
                self._prev_render_mode = None
            else:
                # setting.set("/renderer/active", "rtx")
                setting.set("/rtx/rendermode", value)

    def rebuild(self):
        delay_execute_by_frame(2, self._delay_rebuild, "rebuild")

    def _add_items(self):
        with ui.VStack(WIDGET_HEIGHT=400):
            combo_info = RenderItemInfo(
                "Preset",
                RenderItemType.COMBO,
                None,
                "/rtx/renderpreset",
                0,
                0,
                0,
                ["Draft", "Preview", "Photo", "Custom"],
            )
            RenderItem(combo_info, self._pick_preset)
            ui.Spacer(height=3)
            render_mode_list = [
                "RaytracedLighting: RTX - Real-Time",
                "PathTracing: RTX - Interactive(Path Tracing)",
                "RealTimePathTracing: RTX - Real-Time 2.0",
            ]
            settings = carb.settings.get_settings()
            enabled_renderers = settings.get_as_string("/renderer/enabled")
            if enabled_renderers is not None and enabled_renderers.find("iray") != -1:
                render_mode_list.append("iray: RTX - Accurate(Iray)")

            combo_info2 = RenderItemInfo(
                "Render",
                RenderItemType.COMBO,
                None,
                "/rtx/rendermode",
                0,
                0,
                0,
                render_mode_list,  # ["RaytracedLighting", "PathTracing", "iray"],
            )
            RenderItem(combo_info2, self._pick_render)

            cur_gpu_count = settings.get_as_int("/renderer/multiGpu/currentGpuCount")
            if cur_gpu_count < 2:
                settings.set_int("/rtx/pathtracing/mgpu/enabled", False)
                readonly = True
            else:
                readonly = False
            switch_info = RenderItemInfo(
                "Multi GPU", RenderItemType.SWITCH, "/rtx/pathtracing/mgpu/enabled", None, 0, 0, 0, readonly=readonly
            )
            RenderItem(switch_info)

            switch_fast_navi = RenderItemInfo(
                "Fast Navigation", RenderItemType.SWITCH, "/renderer/eco_mode_enable", None, 0, 0, 0
            )
            RenderItem(switch_fast_navi)

            self._build_separator()

            current_render = self._settings.get("/rtx/rendermode")
            if current_render == "RaytracedLighting":
                self._add_ray_trace_items()

            if current_render == "PathTracing":
                self._add_path_trace_items()

            self._build_separator()

            combo_info3 = RenderItemInfo(
                "Tone Mapping",
                RenderItemType.COMBO,
                None,
                "/rtx/post/tonemap/op",
                0,
                0,
                0,
                ["Clamp", "Linear", "Reinhard", "Reinhard (modified)", "HejiHableAlu", "HableUc2", "ACES", "Iray"],
            )
            RenderItem(combo_info3)
            ui.Spacer(height=3)

            combo_info4 = RenderItemInfo(
                "Color Correction",
                RenderItemType.SWITCH_COMBO,
                "/rtx/post/colorcorr/enabled",
                "/rtx/post/colorcorr/outputMode",
                0,
                0,
                0,
                ["sRGBLinear", "ACEScg"],
            )
            RenderItem(combo_info4)
            ui.Spacer(height=3)

            combo_info5 = RenderItemInfo(
                "Color Grading",
                RenderItemType.SWITCH_COMBO,
                "/rtx/post/colorgrad/enabled",
                "/rtx/post/colorgrad/outputMode",
                0,
                0,
                0,
                ["sRGBLinear", "ACEScg"],
            )
            RenderItem(combo_info5)

            self._build_separator()
            with ui.HStack():
                ui.Spacer()
                ui.Button(
                    "Reset to Render Defaults",
                    width=190,
                    height=22,
                    clicked_fn=self._reset_render,
                    alignment=ui.Alignment.CENTER,
                )
                ui.Spacer()

    def _reset_render(self, *_):
        self._preset.reset()

    def _switch_dof(self, value):
        self._settings.set("/rtx/post/dof/overrideEnabled", not value)
        self._preset.update_current_value("/rtx/post/dof/overrideEnabled", not value)
        self._settings.set("/rtx/post/dof/enabled", value)
        self._preset.update_current_value("/rtx/post/dof/enabled", value)

    def _add_ray_trace_items(self):
        switch_info2 = RenderItemInfo("Reflection", RenderItemType.SWITCH, "/rtx/reflections/enabled", "", 0, 0, 0)
        RenderItem(switch_info2)

        switch_info3 = RenderItemInfo("Shadows", RenderItemType.SWITCH, "/rtx/shadows/enabled", "", 0, 0, 0)
        RenderItem(switch_info3)

        switch_info4 = RenderItemInfo("Translucency", RenderItemType.SWITCH, "/rtx/translucency/enabled", "", 0, 0, 0)
        RenderItem(switch_info4)

        switch_drag_info = RenderItemInfo(
            "Ambient Occlusion",
            RenderItemType.SWITCH_DRAG,
            "/rtx/ambientOcclusion/enabled",
            "/rtx/ambientOcclusion/temporalSqrtLength",
            0.01,
            1,
            5,
        )
        RenderItem(switch_drag_info)

        switch_info5 = RenderItemInfo(
            "Global Illumniation", RenderItemType.SWITCH, "/rtx/indirectDiffuse/enabled", "", 0, 0, 0
        )
        RenderItem(switch_info5)

        switch_drag_info2 = RenderItemInfo(
            "Bloom",
            RenderItemType.SWITCH_DRAG,
            "/rtx/post/lensFlares/enabled",
            "/rtx/post/lensFlares/flareScale",
            0.01,
            0,
            2.0,
        )
        RenderItem(switch_drag_info2)

        switch_drag_info4 = RenderItemInfo(
            "Chromatic Aberration",
            RenderItemType.SWITCH_DRAG,
            "/rtx/post/chromaticAberration/enabled",
            [
                "/rtx/post/chromaticAberration/strengthR",
                "/rtx/post/chromaticAberration/strengthG",
                "/rtx/post/chromaticAberration/strengthB",
            ],
            0.01,
            -1,
            1,
        )
        RenderItem(switch_drag_info4)

        switch_info6 = RenderItemInfo(
            "Depth of Field", RenderItemType.SWITCH, "/rtx/post/dof/viewUIEnabled", None, 0, 0, 0
        )
        RenderItem(switch_info6, None, self._switch_dof)

        switch_info7 = RenderItemInfo(
            "Auto Exposure", RenderItemType.SWITCH, "/rtx/post/histogram/enabled", None, 0, 0, 0
        )
        self._exposure_control = RenderItem(switch_info7)

    def _add_path_trace_items(self):
        self._spins = []
        spin_info1 = RenderItemInfo("Max Bounces", RenderItemType.FIELD, None, "/rtx/pathtracing/maxBounces", 1, 0, 64)
        spin1 = RenderItem(spin_info1)
        self._spins.append(spin1)

        ui.Spacer(height=3)
        spin_info2 = RenderItemInfo(
            "Total Samples", RenderItemType.SWITCH_FIELD, None, "/rtx/pathtracing/totalSpp", 1, 0, 1048576
        )
        spin2 = RenderItem(spin_info2)
        self._spins.append(spin2)
        switch_drag_info2 = RenderItemInfo(
            "Bloom",
            RenderItemType.SWITCH_DRAG,
            "/rtx/post/lensFlares/enabled",
            "/rtx/post/lensFlares/flareScale",
            0.01,
            0,
            2.0,
        )
        RenderItem(switch_drag_info2)

        switch_drag_info4 = RenderItemInfo(
            "Chromatic Aberration",
            RenderItemType.SWITCH_DRAG,
            "/rtx/post/chromaticAberration/enabled",
            [
                "/rtx/post/chromaticAberration/strengthR",
                "/rtx/post/chromaticAberration/strengthG",
                "/rtx/post/chromaticAberration/strengthB",
            ],
            0.01,
            -1,
            1,
        )
        RenderItem(switch_drag_info4)

        switch_info6 = RenderItemInfo(
            "Depth of Field", RenderItemType.SWITCH, "/rtx/post/dof/viewUIEnabled", None, 0, 0, 0
        )
        RenderItem(switch_info6, None, self._switch_dof)

        switch_info7 = RenderItemInfo(
            "Auto Exposure", RenderItemType.SWITCH, "/rtx/post/histogram/enabled", None, 0, 0, 0
        )
        self._exposure_control = RenderItem(switch_info7)

    # Override base class's implement
    def _build_content(self):
        # self._frame = None
        self._frame = ui.ScrollingFrame(
            name="render_setting_frame",
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
        )
        with self._frame:
            self._add_items()
        self._pick_preset("Draft")

    def _build_separator(self):
        ui.Spacer(height=10)
        with ui.HStack(height=3):
            ui.Spacer(width=40, height=3)
            ui.Line(name="title1", height=1, style={"color": 0xFF24211F})
            ui.Spacer(width=40, height=3)
        ui.Spacer(height=10)

    def _on_visibility_changed(self, visible):
        if visible:
            self.rebuild()
            # rebuild to refresh the value
        else:
            # Refresh menu
            async def __update_menu_async():
                await omni.kit.app.get_app().next_update_async()
                omni.kit.menu.utils.rebuild_menus()

            asyncio.ensure_future(__update_menu_async())

    def _on_exposure_enable_setting_changed(self, item, event_type):
        dict = carb.dictionary.get_dictionary()
        value = dict.get(item)
        if self._exposure_control:
            self._exposure_control.change_switch_status(value)

    def _on_final_close(self, save):
        self._window.visible = False
        UpdateEventHelper.get_instance().deregister_update(self)
        self._settings.unsubscribe_to_change_events(self._exposure_changed_sub)
        if not save:
            return

    def _on_show(self, show):
        self.show(show)

    def __register_menu(self):
        def __on_tick():
            return self._window and self._window.visible

        def __on_toggle_window():
            if self._window:
                self._window.visible = not self._window.visible

        self._menu_list = [
            MenuItemDescription(
                name="Render Settings ",
                ticked=True,
                ticked_fn=__on_tick,
                onclick_action=__on_toggle_window,
                appear_after="Fast Navigation",
            ),
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, "Rendering", -4)

    def __deregister_menu(self):
        omni.kit.menu.utils.remove_menu_items(self._menu_list, "Rendering", -4)

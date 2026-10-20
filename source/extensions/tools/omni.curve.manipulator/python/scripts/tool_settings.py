# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
from typing import Type

import carb.dictionary
import carb.settings
import omni.kit.app
import omni.kit.context_menu
import omni.kit.undo
import omni.ui as ui
from omni.kit.manipulator.tool.snap import settings_constants
from omni.kit.manipulator.tool.snap.provider import SnapProvider
from omni.kit.manipulator.tool.snap.registry import SnapProviderRegistry
from omni.kit.widget.settings import (
    SettingsWidgetBuilder,
    SettingType,
    create_setting_widget,
    create_setting_widget_combo,
)
from omni.kit.widget.settings.settings_model import SettingModel
from pxr import UsdGeom

from ..bindings import CurveEditingModeType
from .bezier_curve_edits_context import BezierCurveEditsContextManager

LABEL_WIDTH = 100

CURVE_DRAW_POINTS_SETTING = "persistent/exts/omni.curve.manipulator/curveDrawPoints"
INTERPOLATE_MODE_SETTING = "persistent/exts/omni.curve.manipulator/pencilToolInterpolateMode"
SHOW_PROMPT_SETTING = "/exts/omni.curve.manipulator/showPrompt"
SNAP_TO_SURFACE_SETTING = "/persistent/app/viewport/snapToSurface"
SPACING_SETTING = "persistent/exts/omni.curve.manipulator/pencilToolSpacing"


def get_valid_curve_type(basis_curves_list, default_curve_type=None):
    curve_types = set()
    for basis_curves in basis_curves_list:
        points = basis_curves.GetPointsAttr().Get()
        if points and len(points) > 0:
            type = basis_curves.GetTypeAttr().Get()
            curve_types.add(type)
    curve_type_count = len(curve_types)
    if curve_type_count > 1:
        return "mixed"
    if curve_type_count == 1:
        return curve_types.pop()
    return default_curve_type


class ToolSettingsMenuDelegate(ui.MenuDelegate):
    COLOR_READONLY = 0xFF5C5C5C
    INTERPOLATE_MODE_ITEM = "ToolSettingsContextMenuImpl.INTERPOLATE_MODE_ITEM"
    SPACING_ITEM = "ToolSettingsContextMenuImpl.SPACING_ITEM"
    ROW_WIDTH = 2 * LABEL_WIDTH

    def __init__(self, objects):
        super().__init__()
        self._objects = objects

    def build_item(self, item):
        if item.text == ToolSettingsMenuDelegate.INTERPOLATE_MODE_ITEM:
            self._build_item_interpolate_mode()
            self._update_custom_item(item)
        elif item.text == ToolSettingsMenuDelegate.SPACING_ITEM:
            self._build_item_spacing()
            self._update_custom_item(item)
        else:
            ui.Label(item.text)

    def build_status(self, item):
        pass

    def build_title(self, item):
        pass

    def _build_container_with_padding(self, container_type=ui.HStack, padding=2):
        with ui.Frame(width=ToolSettingsMenuDelegate.ROW_WIDTH):
            with ui.HStack():
                ui.Spacer(width=padding)
                with ui.VStack():
                    ui.Spacer(height=padding)
                    container = container_type(content_clipping=True)
                    ui.Spacer(height=padding)
                ui.Spacer(width=padding)
        return container

    def _build_item_interpolate_mode(self):
        curve_type = None
        if "basis_curves_list" in self._objects:
            curve_type = get_valid_curve_type(self._objects["basis_curves_list"])
        with self._build_container_with_padding(container_type=ui.ZStack):
            with ui.HStack():
                label = self._build_label("Interpolate Mode", INTERPOLATE_MODE_SETTING)
                if curve_type == "mixed":
                    label.set_style({"color": ToolSettingsMenuDelegate.COLOR_READONLY})
                    with ui.ZStack(alignment=ui.Alignment.CENTER):
                        ui.StringField(enabled=False)
                        ui.Rectangle(alignment=ui.Alignment.CENTER, name="mixed_overlay_text")
                        ui.Label(
                            "Mixed",
                            name="mixed_overlay",
                            alignment=ui.Alignment.CENTER,
                            style={"color": ToolSettingsMenuDelegate.COLOR_READONLY},
                        )
                elif curve_type is not None:
                    label.set_style({"color": ToolSettingsMenuDelegate.COLOR_READONLY})
                    widget = ui.StringField(enabled=False, style={"color": ToolSettingsMenuDelegate.COLOR_READONLY})
                    widget.model.set_value(curve_type)
                else:
                    create_setting_widget_combo(INTERPOLATE_MODE_SETTING, ["cubic", "linear"], False)

    def _build_item_spacing(self):
        with self._build_container_with_padding():
            self._build_label("Spacing", SPACING_SETTING)
            create_setting_widget(SPACING_SETTING, SettingType.FLOAT, width=LABEL_WIDTH)

    def _build_label(self, text, tooltip, **kwargs):
        return ui.Label(text, tooltip=tooltip, width=LABEL_WIDTH, **kwargs)

    def _update_custom_item(self, item):
        item.enabled = True
        item.set_style({"MenuItem": {"background_selected_color": 0}})


class ToolSettingsMenuImpl:
    def __init__(self, menu_name):
        self._menu_entries = []
        self._menu_name = menu_name

    def add_menu(self, menu):
        self._menu_entries.append(omni.kit.context_menu.add_menu(menu, self._menu_name, "omni.curve.manipulator"))

    def add_tool_settings_item(self, item_name):
        self.add_menu({"name": item_name})

    def destroy(self):
        for menu in self._menu_entries:
            if hasattr(menu, "release"):
                menu.release()
        self._menu_entries.clear()


class PencilMenu:
    MENU_NAME = "pencil"

    @classmethod
    def startup(cls):
        cls._impl = ToolSettingsMenuImpl(PencilMenu.MENU_NAME)
        cls._impl.add_tool_settings_item(ToolSettingsMenuDelegate.INTERPOLATE_MODE_ITEM)
        cls._impl.add_tool_settings_item(ToolSettingsMenuDelegate.SPACING_ITEM)

    @classmethod
    def shutdown(cls):
        cls._impl.destroy()


class PointMenu:
    MENU_NAME = "point"

    @classmethod
    def startup(cls):
        cls._impl = ToolSettingsMenuImpl(PointMenu.MENU_NAME)
        cls._impl.add_tool_settings_item(ToolSettingsMenuDelegate.INTERPOLATE_MODE_ITEM)

    @classmethod
    def shutdown(cls):
        cls._impl.destroy()


# Keep this for VP1 backward compatibility
# If/when VP1 is deprecated, remove related code and only keep VP2 path
class SnapSettingModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._settings = carb.settings.get_settings()
        self._dictionary = carb.dictionary.get_dictionary()

        self._update_setting_snap = omni.kit.app.SettingChangeSubscription(
            settings_constants.SNAP_ENABLED_SETTING, self._on_change
        )
        self._update_setting_snap_to_face = omni.kit.app.SettingChangeSubscription(
            SNAP_TO_SURFACE_SETTING, self._on_change
        )

    def destroy(self):
        self._update_setting_snap = None
        self._update_setting_snap_to_face = None

    def __del__(self):
        self.destroy()

    def _on_change(self, value, event_type) -> None:
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._value_changed()

    def get_value_as_bool(self) -> bool:
        return self._settings.get(settings_constants.SNAP_ENABLED_SETTING) and self._settings.get(
            SNAP_TO_SURFACE_SETTING
        )

    def set_value(self, value: bool):
        with omni.kit.undo.group():
            omni.kit.commands.execute("ChangeSetting", path=settings_constants.SNAP_ENABLED_SETTING, value=value)
            omni.kit.commands.execute("ChangeSetting", path=SNAP_TO_SURFACE_SETTING, value=value)


class SnapMenu:
    @classmethod
    def startup(cls):
        cls._settings = carb.settings.get_settings()
        cls._snap_registry = SnapProviderRegistry.get_instance()
        cls._menu_entries = []
        cls._snap_sub = cls._snap_registry.subscribe_to_registry_change(cls._build_snap_menu)

    @classmethod
    def shutdown(cls):
        for menu in cls._menu_entries:
            if hasattr(menu, "release"):
                menu.release()
        cls._menu_entries.clear()
        if cls._snap_sub:
            cls._snap_registry.unsubscribe_to_registry_change(cls._snap_sub)
            cls._snap_sub = None

    @classmethod
    def _build_snap_menu(cls):
        for menu in cls._menu_entries:
            if hasattr(menu, "release"):
                menu.release()
        cls._menu_entries.clear()

        providers = cls._snap_registry.providers

        def build_entry(name: str, provider_class: Type[SnapProvider]):
            def is_checked(*args, **kwargs) -> bool:
                enabled_providers = cls._settings.get(settings_constants.SNAP_PROVIDER_NAME_SETTING_PATH) or []
                return name in enabled_providers

            def on_clicked(*args, **kwargs):
                enabled_providers = list(cls._settings.get(settings_constants.SNAP_PROVIDER_NAME_SETTING_PATH) or [])
                if name not in enabled_providers:
                    enabled_providers.append(name)
                else:
                    enabled_providers.remove(name)
                cls._settings.set(settings_constants.SNAP_PROVIDER_NAME_SETTING_PATH, enabled_providers)

            menu = {
                "name": f"{provider_class.get_display_name()}##{name}",  # append ##{name} for unique menu entry
                "checked_fn": is_checked,
                "onclick_fn": on_clicked,
                "show_fn": provider_class.can_show_menu,
                "enabled_fn": provider_class.can_enable_menu,
            }
            cls._add_snap_menu(menu)

        sorted_providers = dict(sorted(providers.items(), key=lambda item: item[1].get_display_name()))
        for name, provider_class in sorted_providers.items():
            build_entry(name, provider_class)

    @classmethod
    def _add_snap_menu(cls, menu):
        cls._menu_entries.append(omni.kit.context_menu.add_menu(menu, "snap", "omni.curve.manipulator"))


class ToolSettingsWindow:
    ICON_PATH = ""
    READONLY_STYLE = {"color": ToolSettingsMenuDelegate.COLOR_READONLY}

    def __init__(self, title: str, viewport_api, usd_context_name: str = "", refresh_ui_fn=None):
        self._window = None
        self._title = title
        self._basis_curves = []
        self._close_window_on_visibility_change = False
        self._curve_mode_button = None
        self._curve_draw_points_model = SettingModel(CURVE_DRAW_POINTS_SETTING)
        self._delayed_context_menu_task = None
        self._interpolate_mode_label = None
        self._interpolate_mode_combo = None
        self._interpolate_mode_model = SettingModel(INTERPOLATE_MODE_SETTING)
        self._interpolate_mode_mixed_overlay_label = None
        self._interpolate_mode_mixed_overlay_rect = None
        self._pencil_mode_button = None
        self._pencil_mode_model = ui.SimpleBoolModel()
        self._pencil_menu = None
        self._periodic_model = ui.SimpleBoolModel()
        self._point_button = None
        self._radio_mode_bezier = None
        self._radio_mode_freehand = None
        self._radio_model = ui.SimpleIntModel()
        self._refresh_ui_fn = refresh_ui_fn
        self._set_curve_type_on_change = False
        self._snap_model = None
        self._spacing_label = None
        self._spacing_widget = None
        self._value_changed_ids = []
        self._viewport_api = viewport_api
        self._settings = carb.settings.get_settings()
        self._settings_ui_created = False
        self._updating_periodic_model = False
        self._usd_context_name = usd_context_name
        self._vp1 = None
        self._vp2 = None
        if self._pencil_mode_model.get_value_as_bool():
            self._radio_model.set_value(1)
        else:
            self._radio_model.set_value(0)
        if self._viewport_api is not None:
            self._snap_model = SettingModel(settings_constants.SNAP_ENABLED_SETTING)
            self._vp2 = self._get_vp2()
        else:
            self._snap_model = SnapSettingModel()
            self._vp1 = self._get_vp1()
        self._value_changed_ids.append(
            (
                self._curve_draw_points_model,
                self._curve_draw_points_model.add_value_changed_fn(lambda *_: self._on_refresh_pencil_button()),
            )
        )
        self._value_changed_ids.append(
            (
                self._curve_draw_points_model,
                self._curve_draw_points_model.add_value_changed_fn(lambda *_: self._on_refresh_settings_ui()),
            )
        )
        self._value_changed_ids.append(
            (
                self._interpolate_mode_model,
                self._interpolate_mode_model.add_value_changed_fn(lambda *_: self._on_interpolate_mode_changed()),
            )
        )
        self._value_changed_ids.append(
            (
                self._interpolate_mode_model,
                self._interpolate_mode_model.add_value_changed_fn(lambda *_: self._on_refresh_pencil_button()),
            )
        )
        self._value_changed_ids.append(
            (
                self._interpolate_mode_model,
                self._interpolate_mode_model.add_value_changed_fn(lambda *_: self._on_refresh_settings_ui()),
            )
        )
        self._value_changed_ids.append(
            (
                self._interpolate_mode_model,
                self._interpolate_mode_model.add_value_changed_fn(lambda *_: self._on_type_changed()),
            )
        )
        self._value_changed_ids.append(
            (
                self._pencil_mode_model,
                self._pencil_mode_model.add_value_changed_fn(lambda *_: self._on_set_curve_editing_mode()),
            )
        )
        self._value_changed_ids.append(
            (
                self._pencil_mode_model,
                self._pencil_mode_model.add_value_changed_fn(lambda *_: self._on_refresh_pencil_button()),
            )
        )
        self._value_changed_ids.append(
            (
                self._pencil_mode_model,
                self._pencil_mode_model.add_value_changed_fn(lambda *_: self._on_refresh_settings_ui()),
            )
        )
        self._value_changed_ids.append(
            (self._periodic_model, self._periodic_model.add_value_changed_fn(lambda *_: self._on_set_periodic()))
        )
        self._value_changed_ids.append(
            (self._radio_model, self._radio_model.add_value_changed_fn(lambda *_: self._on_radio_button_changed()))
        )

    def __del__(self):
        self.destroy()

    def destroy(self):
        for model, id in self._value_changed_ids:
            model.remove_value_changed_fn(id)
        if self._delayed_context_menu_task:
            self._delayed_context_menu_task.cancel()
            self._delayed_context_menu_task = None
        if self._pencil_menu:
            self._pencil_menu.destroy()
            self._pencil_menu = None
        if self._window:
            self._window.destroy()
            self._window = None
        self._update_sub = None
        self._value_changed_ids.clear()

    def set_pencil_mode(self, mode: int):
        if mode == int(CurveEditingModeType.DRAW):
            self._pencil_mode_model.set_value(True)
            self._radio_model.set_value(1)
        else:
            self._pencil_mode_model.set_value(False)
            self._radio_model.set_value(0)
        self._on_refresh_pencil_button()

    def set_prim_paths(self, stage, prim_paths):
        periodic = False
        start_in_draw_mode = True
        self._basis_curves = []
        if stage:
            for prim_path in prim_paths:
                basis_curves = UsdGeom.BasisCurves.Get(stage, prim_path)
                self._basis_curves.append(basis_curves)
                if basis_curves.GetWrapAttr().Get() == UsdGeom.Tokens.periodic:
                    periodic = True
                points = basis_curves.GetPointsAttr().Get() or []
                if len(points) > 0:
                    start_in_draw_mode = False
        self._curve_draw_points_model.set_value(start_in_draw_mode)
        self._set_curve_type_on_change = False
        self._updating_periodic_model = True
        self._periodic_model.set_value(periodic)
        self._updating_periodic_model = False
        self._on_interpolate_mode_changed()
        self._on_refresh_settings_ui()
        curve_type = get_valid_curve_type(self._basis_curves)
        if curve_type is not None and curve_type != "mixed":
            set_curve_type_on_change = self._set_curve_type_on_change
            self._interpolate_mode_model.set_value(curve_type)
            self._set_curve_type_on_change = set_curve_type_on_change

    def show_window(self, show: bool):
        if self._settings.get(SHOW_PROMPT_SETTING) is False:
            return

        self._close_window_on_visibility_change = False

        if self._window:
            self._window.visible = show

        if show:
            vp = self._vp2 if self._vp2 is not None else ui.Workspace.get_window("Viewport")
            if vp:
                if not self._window:
                    self._create_window(vp)

            if self._vp1:
                self._window.visible = self._vp1.is_visible()
                self._update_sub = (
                    omni.kit.app.get_app()
                    .get_update_event_stream()
                    .create_subscription_to_pop(self._on_update, name=f"{self._title} window update")
                )

            elif self._vp2:
                self._window.visible = self._vp2.visible
        else:
            self._update_sub = None

        if self._window and self._window.visible:
            self._close_window_on_visibility_change = True

    def refresh_vp2(self):
        self._vp2 = self._get_vp2()

    def _apply_inverted_value(self, dst_model, src_model):
        if dst_model.get_value_as_bool() == src_model.get_value_as_bool():
            dst_model.set_value(not dst_model.get_value_as_bool())

    def _build_toggle_button(
        self, model, icon_name, button_size=40, context_menu_fn=None, inverted=False, toggle=False, **kwargs
    ):
        button_model = model
        if inverted:
            button_model = ui.SimpleBoolModel(not model.get_value_as_bool())
            self._value_changed_ids.append(
                (
                    button_model,
                    button_model.add_value_changed_fn(lambda *_: self._apply_inverted_value(model, button_model)),
                )
            )
            self._value_changed_ids.append(
                (model, model.add_value_changed_fn(lambda *_: self._apply_inverted_value(button_model, model)))
            )
        button_widget = ui.ToolButton(
            height=button_size, model=button_model, style=self._get_button_style(icon_name), width=button_size, **kwargs
        )
        button_widget.set_mouse_pressed_fn(lambda x, y, b, m: self._on_show_context_menu(x, y, b, m, context_menu_fn))
        button_widget.set_mouse_released_fn(lambda *_: self._on_cancel_delayed_context_menu())
        if not toggle:
            button_widget.set_clicked_fn(lambda *_: model.set_value(not inverted))
        return button_widget

    def _create_window(self, vp):
        line_height = 52
        radio_size = 23
        radio_style = {
            "": {"background_color": 0x00000000, "image_url": f"{ToolSettingsWindow.ICON_PATH}/radio_off.svg"},
            ":checked": {"image_url": f"{ToolSettingsWindow.ICON_PATH}/radio_on.svg"},
        }
        window_flags = 0
        window_flags |= ui.WINDOW_FLAGS_NO_COLLAPSE
        window_flags |= ui.WINDOW_FLAGS_NO_DOCKING
        window_flags |= ui.WINDOW_FLAGS_NO_RESIZE
        window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_NO_SCROLL_WITH_MOUSE
        self._window = ui.Window(
            auto_resize=True,
            flags=window_flags,
            margin=0,
            title="Curve",
            visible=True,
        )
        spacing = 5
        with self._window.frame:
            with ui.VStack(height=0, spacing=spacing):
                with ui.HStack(height=0, skip_draw_when_clipped=True, spacing=3, width=0):
                    with ui.VStack():
                        ui.Spacer()
                        self._build_toggle_button(
                            self._curve_draw_points_model,
                            "draw.svg",
                            toggle=True,
                            tooltip="When checked, curve points can be added by drawing on the screen or clicking on existing curve to insert.\n"
                            "Hold SHIFT to add a new curve segment.",
                        )
                        ui.Spacer()
                    ui.Spacer()
                    ui.Line(
                        height=line_height,
                        alignment=ui.Alignment.H_CENTER,
                        style={"border_width": 2, "padding": 5, "margin": 5, "color": 0xFF555555},
                    )
                    ui.Spacer()
                    with ui.VStack():
                        ui.Spacer()
                        radio_collection = ui.RadioCollection(model=self._radio_model)
                        self._radio_mode_bezier = ui.HStack(height=0)
                        self._radio_mode_freehand = ui.HStack(height=0)
                        with self._radio_mode_bezier:
                            with ui.VStack(width=0):
                                ui.Spacer()
                                ui.RadioButton(
                                    alignment=ui.Alignment.CENTER,
                                    height=radio_size,
                                    radio_collection=radio_collection,
                                    style=radio_style,
                                    width=radio_size,
                                )
                                ui.Spacer()
                            ui.Label("Bezier", alignment=ui.Alignment.LEFT_CENTER)
                        with self._radio_mode_freehand:
                            with ui.VStack(width=0):
                                ui.Spacer()
                                ui.RadioButton(
                                    alignment=ui.Alignment.CENTER,
                                    height=radio_size,
                                    radio_collection=radio_collection,
                                    style=radio_style,
                                    width=radio_size,
                                )
                                ui.Spacer()
                            ui.Label("Freehand", alignment=ui.Alignment.LEFT_CENTER)
                        ui.Spacer()
                    ui.Spacer()
                    ui.Line(
                        height=line_height,
                        alignment=ui.Alignment.H_CENTER,
                        style={"border_width": 2, "padding": 5, "margin": 5, "color": 0xFF555555},
                    )
                    ui.Spacer()
                    with ui.VStack():
                        ui.Spacer()
                        with ui.HStack(height=0):
                            self._build_toggle_button(
                                self._periodic_model,
                                "periodic.svg",
                                toggle=True,
                                tooltip="When enabled, the curve will be closed (i.e. the first and last points will be connected).",
                            )
                        ui.Spacer()
                    ui.Spacer()
                    ui.Line(
                        height=line_height,
                        alignment=ui.Alignment.H_CENTER,
                        style={"border_width": 2, "padding": 5, "margin": 5, "color": 0xFF555555},
                    )
                    ui.Spacer()
                    with ui.VStack(width=1.5 * LABEL_WIDTH):
                        ui.Spacer()
                        with ui.HStack(height=0):
                            self._interpolate_mode_label = ui.Label(
                                "Type", tooltip=INTERPOLATE_MODE_SETTING, width=LABEL_WIDTH / 2.0
                            )
                            with ui.ZStack():
                                self._interpolate_mode_combo = ui.HStack()
                                with self._interpolate_mode_combo:
                                    create_setting_widget_combo(INTERPOLATE_MODE_SETTING, ["cubic", "linear"], False)
                                self._interpolate_mode_mixed_overlay_rect = ui.Rectangle(
                                    alignment=ui.Alignment.CENTER, name="mixed_overlay_text", style={"border_radius": 2}
                                )
                                self._interpolate_mode_mixed_overlay_label = ui.Label("", name="mixed_overlay", width=0)
                        ui.Spacer(height=4)
                        with ui.HStack(height=0):
                            self._spacing_label = ui.Label("Spacing", tooltip=SPACING_SETTING, width=LABEL_WIDTH / 2.0)
                            self._spacing_widget, _ = create_setting_widget(SPACING_SETTING, SettingType.FLOAT)
                        ui.Spacer()
                    ui.Spacer()
                    ui.Line(
                        height=line_height,
                        alignment=ui.Alignment.H_CENTER,
                        style={"border_width": 2, "padding": 5, "margin": 5, "color": 0xFF555555},
                    )
                    ui.Spacer()
                    with ui.VStack():
                        ui.Spacer()
                        ui.Button(
                            " Done ",
                            clicked_fn=lambda *_: self._on_close_tool_settings(),
                            height=45,
                            margin=1,
                            padding=5,
                            width=40,
                        )
                        ui.Spacer()
                self._settings_ui_created = True
                self._on_refresh_pencil_button()
                self._on_refresh_settings_ui()
        self._window.visible = False
        self._window.frame.set_computed_content_size_changed_fn(lambda *_: self._on_window_init(vp))
        self._on_interpolate_mode_changed()

    def _get_button_style(self, icon_name, enabled=True, margin=1, padding=5):
        color = 0xFFFFFFFF
        color_checked = 0xFF1F2123
        color_hovered = 0xFF666666
        color_transparent = 0x00000000
        if not enabled:
            color = 0x60FFFFFF
            color_checked = color_transparent
            color_hovered = color_transparent
        return {
            "Button": {"background_color": color_transparent, "margin": margin, "padding": padding},
            "Button:hovered": {"background_color": color_hovered},
            "Button:checked": {"background_color": color_checked},
            "Button.Image": {"color": color, "image_url": f"{ToolSettingsWindow.ICON_PATH}/{icon_name}"},
        }

    def _show_snap_menu(self):
        menu_list = omni.kit.context_menu.get_menu_dict("snap", "omni.curve.manipulator")
        objects = {}
        if self._vp2:
            objects["viewport_api"] = self._vp2.viewport_api
        omni.kit.context_menu.get_instance().show_context_menu("curve_snap", objects, menu_list)

    def _show_tool_settings_menu(self, menu_name):
        objects = {"basis_curves_list": self._basis_curves}
        omni.kit.context_menu.get_instance().show_context_menu(
            f"curve_{menu_name}",
            objects,
            omni.kit.context_menu.get_menu_dict(menu_name, "omni.curve.manipulator"),
            delegate=ToolSettingsMenuDelegate(objects),
        )

    def _on_cancel_delayed_context_menu(self):
        if self._delayed_context_menu_task:
            self._delayed_context_menu_task.cancel()
            self._delayed_context_menu_task = None

    def _on_close_tool_settings(self):
        if self._close_window_on_visibility_change:
            self._close_window_on_visibility_change = False
            curve_context = BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits.curve_context
            omni.kit.commands.execute("DisableCurveEditing", curve_context=curve_context)

    def _on_interpolate_mode_changed(self):
        if self._point_button:
            icon_name = "linear.svg"
            curve_type = get_valid_curve_type(self._basis_curves, self._interpolate_mode_model.get_value_as_string())
            if curve_type == "cubic":
                icon_name = "bezier.svg"
            self._point_button.set_style(self._get_button_style(icon_name))

    def _on_radio_button_changed(self):
        if self._radio_model.get_value_as_int() == 0:
            self._pencil_mode_model.set_value(False)
        else:
            self._pencil_mode_model.set_value(True)

    def _on_refresh_pencil_button(self):
        radio_style = ToolSettingsWindow.READONLY_STYLE
        if self._curve_draw_points_model.get_value_as_bool():
            radio_style = {}
        if self._curve_mode_button and self._pencil_mode_button:
            curve_type = get_valid_curve_type(self._basis_curves, self._interpolate_mode_model.get_value_as_string())
            drawing = self._curve_draw_points_model.get_value_as_bool()
            is_curve = bool(curve_type == "cubic")
            self._curve_mode_button.enabled = drawing
            self._pencil_mode_button.enabled = drawing
            if is_curve:
                self._curve_mode_button.set_style(self._get_button_style("mode_point_curve.svg", enabled=drawing))
                self._curve_mode_button.set_tooltip(
                    "Edit the curve by clicking and adding bezier points with tangents."
                )
                self._pencil_mode_button.set_style(self._get_button_style("mode_draw_curve.svg", enabled=drawing))
                self._pencil_mode_button.set_tooltip("Edit the curve by drawing a line.")
            else:
                self._curve_mode_button.set_style(self._get_button_style("mode_point_line.svg", enabled=drawing))
                self._curve_mode_button.set_tooltip("Edit the curve by clicking and adding points.")
                self._pencil_mode_button.set_style(self._get_button_style("mode_draw_line.svg", enabled=drawing))
                self._pencil_mode_button.set_tooltip("Edit the curve by drawing a line.")
        if self._radio_mode_bezier:
            self._radio_mode_bezier.set_style(radio_style)
        if self._radio_mode_freehand:
            self._radio_mode_freehand.set_style(radio_style)

    def _on_refresh_settings_ui(self):
        if self._settings_ui_created:
            curve_type = get_valid_curve_type(self._basis_curves)
            if curve_type == "mixed":
                self._interpolate_mode_combo.enabled = False
                self._interpolate_mode_label.set_style(ToolSettingsWindow.READONLY_STYLE)
                self._interpolate_mode_mixed_overlay_label.set_style(ToolSettingsWindow.READONLY_STYLE)
                self._interpolate_mode_mixed_overlay_label.text = " Mixed"
                self._interpolate_mode_mixed_overlay_label.visible = True
                self._interpolate_mode_mixed_overlay_rect.visible = True
                self._set_curve_type_on_change = False
            elif curve_type is not None:
                self._interpolate_mode_combo.enabled = True
                self._interpolate_mode_label.set_style({})
                self._interpolate_mode_mixed_overlay_label.set_style({})
                self._interpolate_mode_mixed_overlay_label.text = ""
                self._interpolate_mode_mixed_overlay_label.visible = False
                self._interpolate_mode_mixed_overlay_rect.visible = False
                self._set_curve_type_on_change = True
            else:
                self._interpolate_mode_combo.enabled = True
                self._interpolate_mode_label.set_style({})
                self._interpolate_mode_mixed_overlay_label.set_style({})
                self._interpolate_mode_mixed_overlay_label.text = ""
                self._interpolate_mode_mixed_overlay_label.visible = False
                self._interpolate_mode_mixed_overlay_rect.visible = False
                self._set_curve_type_on_change = False
            if self._curve_draw_points_model.get_value_as_bool() and self._pencil_mode_model.get_value_as_bool():
                self._spacing_label.set_style({})
                self._spacing_widget.enabled = True
                self._spacing_widget.set_style({})
            else:
                self._spacing_label.set_style(ToolSettingsWindow.READONLY_STYLE)
                self._spacing_widget.enabled = False
                self._spacing_widget.set_style(ToolSettingsWindow.READONLY_STYLE)

    def _on_set_curve_editing_mode(self):
        curve_context = BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits.curve_context
        mode = CurveEditingModeType.DRAG
        if self._pencil_mode_model.get_value_as_bool():
            mode = CurveEditingModeType.DRAW
        omni.kit.commands.execute("SetCurveEditingMode", curve_context=curve_context, mode=mode)

    def _on_set_periodic(self):
        if not self._updating_periodic_model:
            with omni.kit.undo.group():
                set_periodic = self._periodic_model.get_value_as_bool()
                curve_edits = BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits
                for basis_curves in self._basis_curves:
                    points = basis_curves.GetPointsAttr().Get() or []
                    if len(points) > 0:
                        basis_curve_periodic = bool(basis_curves.GetWrapAttr().Get() == UsdGeom.Tokens.periodic)
                        if basis_curve_periodic != set_periodic:
                            curve_edits.open_close_curve(basis_curves)

    def _on_show_context_menu(self, x, y, button, modifiers, context_menu_fn):
        left_button = 0
        right_button = 1
        if self._delayed_context_menu_task:
            self._delayed_context_menu_task.cancel()
            self._delayed_context_menu_task = None
        if context_menu_fn:
            if button == left_button:
                self._delayed_context_menu_task = asyncio.ensure_future(
                    self._on_show_context_menu_delayed(x, y, button, modifiers, context_menu_fn)
                )
            elif button == right_button:
                context_menu_fn(x, y, button, modifiers)

    async def _on_show_context_menu_delayed(self, x, y, button, modifiers, context_menu_fn, delay=0.5):
        try:
            await asyncio.sleep(delay)
            context_menu_fn(x, y, button, modifiers)
        except asyncio.CancelledError:
            pass
        self._delayed_context_menu_task = None

    def _on_type_changed(self):
        if self._set_curve_type_on_change:
            BezierCurveEditsContextManager.get_context(self._usd_context_name).curve_edits.set_curve_type(
                self._basis_curves, self._interpolate_mode_model.get_value_as_string()
            )
            if self._refresh_ui_fn:
                self._refresh_ui_fn()

    def _on_window_init(self, vp):
        self._window.set_visibility_changed_fn(lambda *_: self._on_close_tool_settings())
        self._window.frame.set_computed_content_size_changed_fn(None)
        self._window.visible = True
        self._window.position_x = vp.position_x + (vp.width - self._window.frame.computed_width) / 2.0
        self._window.position_y = vp.position_y + 60

    def _get_vp1(self):
        try:
            import omni.kit.viewport_legacy

            return omni.kit.viewport_legacy.get_default_viewport_window()
        except:
            return None

    def _get_vp2(self):
        import omni.kit.viewport.window

        for window in omni.kit.viewport.window.get_viewport_window_instances(None):
            if window.viewport_api == self._viewport_api:
                return window

        return None

    def _on_update(self, evt):
        if self._window and self._vp1:
            self._window.visible = self._vp1.is_visible()

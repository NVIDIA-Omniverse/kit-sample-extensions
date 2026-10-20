# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
from typing import List

import carb.events
import omni.kit.commands
import omni.ui as ui
from omni.kit.property.usd.usd_property_widget import (
    HORIZONTAL_SPACING,
    SchemaPropertiesWidget,
    UsdPropertiesWidgetBuilder,
)
from omni.kit.window.property.property_scheme_delegate import PropertySchemeDelegate
from omni.kit.window.property.style import get_style
from omni.kit.window.property.templates import SimplePropertyWidget
from pxr import Gf, Sdf, Tf, Usd, UsdGeom

from ..bindings import CurveEditingModeType, CurvesEventType, get_interface
from . import utils
from .bezier_curve_edits import BezierCurveEdits
from .bezier_curve_edits_context import BezierCurveEditsContextManager
from .cv_payload import CvPayloadManager
from .property_model import (
    CvAnchorElementAttributeModel,
    InterpolationsModel,
    UsdArrayElementAttributeModel,
    UsdTupleArrayElementAttributeModel,
)
from .property_widget_plugin import BasisCurvesCvWidgetPlugin
from .tool_settings import ToolSettingsWindow

DEFAULT_ICON_WIDTH = 22
EDIT_CV_BUTTON_LABEL = " Edit Control Vertices "


def create_edit_cv_button():
    return ui.Button(EDIT_CV_BUTTON_LABEL, image_height=20, image_width=20, spacing=0)


def refresh_edit_cv_button(button, context):
    background_color = 0xFF292929
    text_color = 0xFFCCCCCC
    if get_interface().is_in_curve_editing_mode(context):
        background_color = 0xFFFCC559
        text_color = 0xFF23211F
    button.set_style(
        {
            "Button": {
                "background_color": background_color,
                "margin": 0,
                "margin_height": 0,
                "margin_width": 0,
                "padding": 2,
                "stack_direction": ui.Direction.LEFT_TO_RIGHT,
            },
            "Button.Image": {
                "alignment": ui.Alignment.CENTER,
                "color": text_color,
                "image_url": f"{ToolSettingsWindow.ICON_PATH}/edit.svg",
            },
            "Button.Label": {"alignment": ui.Alignment.CENTER, "color": text_color},
        }
    )


class BasisCurvesCvWidget(SimplePropertyWidget):
    COMPONENT_LABELS = [("X", 0xFF5555AA), ("Y", 0xFF76A371), ("Z", 0xFFA07D4F), ("W", 0xFFFFFFFF)]

    def __init__(self):
        super().__init__(title="Control Point", collapsable=False)
        self._interpolation_model_values = []
        self._interpolation_models = []
        self._listener = None
        self._payload = None
        self._pending_dirty_paths = set()
        self._pending_dirty_task = None
        self._value_models = []

    def _all_models_enabled(self, models):
        for model in models:
            if not model.is_editable():
                return False
        return True

    def _build_frame_header(self, collapsed, text: str, id: str = None):
        if id is None:
            id = text
        if collapsed:
            alignment = ui.Alignment.RIGHT_CENTER
            width = 5
            height = 7
        else:
            alignment = ui.Alignment.CENTER_BOTTOM
            width = 7
            height = 5
        header_stack = ui.HStack(spacing=8)
        with header_stack:
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Label(text, style_type_name_override="CollapsableFrame.Header")
            ui.Spacer()
            with ui.VStack(content_clipping=True, width=20):
                self._edit_button = create_edit_cv_button()
                self._edit_button.set_mouse_pressed_fn(lambda *_: self._on_exit_curve_editing_mode())
                self._on_refresh_edit_button()

    def _get_widget_kwargs(self, models):
        widget_kwargs = {}
        if not self._all_models_enabled(models):
            widget_kwargs["enabled"] = False
            widget_kwargs["style"] = get_style()["Field::models_readonly"]
        return widget_kwargs

    async def _on_delayed_dirty_handler(self):
        self._pending_dirty_task = None
        if self._pending_dirty_paths:
            pending_dirty_paths = self._pending_dirty_paths.copy()
            self._pending_dirty_paths = set()
            dirtied_models = set()
            for model in self._value_models:
                if model not in dirtied_models:
                    # dedup get_attribute_paths. The curve models duplicate paths for each CV
                    for attribute_path in set(model.get_attribute_paths()):
                        if attribute_path in pending_dirty_paths:
                            model._set_dirty()
                            dirtied_models.add(model)

    def _on_exit_curve_editing_mode(self):
        curve_context = BezierCurveEditsContextManager.get_context().curve_edits.curve_context
        omni.kit.commands.execute("DisableCurveEditing", curve_context=curve_context)

    def _on_refresh_edit_button(self):
        if self._edit_button:
            curve_context = BezierCurveEditsContextManager.get_context().curve_edits.curve_context
            refresh_edit_cv_button(self._edit_button, curve_context)

    def _on_usd_changed(self, notice, stage):
        if self._pending_rebuild_task is not None:
            return
        if not self._payload:
            return
        if stage != self._payload.get_stage():
            return
        dirty_paths = set()
        for path in notice.GetResyncedPaths():
            if path in self._payload:
                self.request_rebuild()
                return
            if path.GetPrimPath() in self._payload:
                prop_is_valid = stage.GetPropertyAtPath(path).IsValid()
                prop_is_watched = False
                for model in self._value_models:
                    if path in model.get_attribute_paths():
                        prop_is_watched = True
                        break
                if prop_is_valid != prop_is_watched:
                    self.request_rebuild()
                    return
                dirty_paths.add(path)
        for path in notice.GetChangedInfoOnlyPaths():
            for i, model in enumerate(self._interpolation_models):
                if path in model.get_attribute_paths():
                    if model.get_current_value() != self._interpolation_model_values[i]:
                        self.request_rebuild()
                        return
            dirty_paths.add(path)
        self._pending_dirty_paths.update(dirty_paths)
        if self._pending_dirty_task is None:
            self._pending_dirty_task = asyncio.ensure_future(self._on_delayed_dirty_handler())

    def build_items(self):
        if self._listener:
            self._listener.Revoke()
            self._listener = None
        if self._pending_dirty_task is not None:
            self._pending_dirty_task.cancel()
            self._pending_dirty_task = None
        self._interpolation_models = []
        self._interpolation_model_values = []
        self._pending_dirty_paths = set()
        if not self._payload:
            return
        basis_curves = []
        cv_list = self._payload.get_paths_and_indices()
        stage = self._payload.get_stage()
        if not stage or len(cv_list) <= 0:
            return
        indices = self._payload.get_indices()
        paths = self._payload.get_paths()
        self.build_ui_readonly_stringfield("Prim Name", [path.name for path in paths])
        self.build_ui_readonly_stringfield("Prim Path", [path.pathString for path in paths])
        self.build_ui_readonly_stringfield("Point index", [str(index) for index in indices])
        basis_curves_frame = ui.CollapsableFrame(build_header_fn=self._build_frame_header, title="Basis Curve")
        with basis_curves_frame:
            basis_curves_stack = ui.VStack(height=0, spacing=5)
        section_build_fns = BasisCurvesCvWidgetPlugin.get_build_fns()
        section_names = sorted(section_build_fns.keys())
        for section_name in section_names:
            if len(cv_list) <= 0:
                break
            collapsable_frame = ui.CollapsableFrame(build_header_fn=self._build_frame_header, title=section_name)
            with collapsable_frame:
                with ui.VStack(height=0, spacing=5):
                    new_cv_list = section_build_fns[section_name](self, stage, cv_list)
            if len(new_cv_list) != len(cv_list):
                cv_list = new_cv_list
            else:
                collapsable_frame.destroy()
        if len(cv_list) > 0:
            indices = []
            normals_attr_paths = []
            points_attr_paths = []
            widths_attr_paths = []
            for prim_path, index in cv_list:
                bc = UsdGeom.BasisCurves.Get(stage, prim_path)
                basis_curves.append(bc)
                indices.append(index)
                normals_attr_paths.append(bc.GetNormalsAttr().GetPath())
                points_attr_paths.append(bc.GetPointsAttr().GetPath())
                widths_attr_paths.append(bc.GetWidthsAttr().GetPath())
            with basis_curves_stack:
                self.build_ui_basis_curves(
                    stage=stage,
                    basis_curves=basis_curves,
                    points_attr_paths=points_attr_paths,
                    normals_attr_paths=normals_attr_paths,
                    widths_attr_paths=widths_attr_paths,
                    indices=indices,
                )
        else:
            basis_curves_frame.destroy()
        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)

    def build_ui_basis_curves(
        self,
        stage: Usd.Stage,
        basis_curves: List[UsdGeom.BasisCurves],
        points_attr_paths: List[Sdf.Path],
        normals_attr_paths: List[Sdf.Path],
        widths_attr_paths: List[Sdf.Path],
        indices: List[int],
    ):
        self.build_ui_points(
            stage=stage,
            attribute_paths=points_attr_paths,
            basis_curves=basis_curves,
            indices=indices,
        )
        self.build_ui_float3_with_interpolation(
            "Normal",
            stage=stage,
            attribute_paths=normals_attr_paths,
            basis_curves=basis_curves,
            indices=indices,
            get_interpolation_fn=lambda s, ap, bc: bc.GetNormalsInterpolation(),
        )
        self.build_ui_float_with_interpolation(
            "Width",
            stage=stage,
            attribute_paths=widths_attr_paths,
            basis_curves=basis_curves,
            indices=indices,
            get_interpolation_fn=lambda s, ap, bc: bc.GetWidthsInterpolation(),
        )

    def build_ui_float(
        self,
        label: str,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        indices: List[int],
        create_default_element_fn=lambda: 0.0,
        get_interpolation_fn=None,
        value_model_class=UsdArrayElementAttributeModel,
    ):
        value_model = value_model_class(
            stage=stage,
            attribute_paths=attribute_paths,
            basis_curves=basis_curves,
            indices=indices,
            metadata={},
            self_refresh=False,
            create_default_element_fn=create_default_element_fn,
            get_interpolation_fn=get_interpolation_fn,
        )
        self._value_models.append(value_model)
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            kwargs = self._get_widget_kwargs([value_model])
            UsdPropertiesWidgetBuilder._create_label(label)
            with ui.ZStack():
                value_widget = ui.FloatDrag(value_model, **kwargs)
                mixed_overlay = UsdPropertiesWidgetBuilder._create_mixed_text_overlay(value_model, value_model)
            UsdPropertiesWidgetBuilder._create_control_state(
                value_model, value_widget=value_widget, mixed_overlay=mixed_overlay
            )

    def build_ui_float_with_interpolation(
        self,
        label: str,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        indices: List[int],
        create_default_element_fn=lambda: 0.0,
        get_interpolation_fn=None,
        value_model_class=UsdArrayElementAttributeModel,
    ):
        interpolation_model = InterpolationsModel(
            stage=stage,
            attribute_paths=attribute_paths,
            basis_curves=basis_curves,
            create_default_element_fn=create_default_element_fn,
            get_interpolation_fn=get_interpolation_fn,
        )
        self._interpolation_models.append(interpolation_model)
        self._interpolation_model_values.append(interpolation_model.get_current_value())
        self.build_ui_float(
            label,
            stage,
            attribute_paths,
            basis_curves,
            indices,
            create_default_element_fn,
            get_interpolation_fn,
            value_model_class,
        )
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            UsdPropertiesWidgetBuilder._create_label(f"{label} Interpolation")
            ui.ComboBox(interpolation_model)
            ui.Spacer(width=DEFAULT_ICON_WIDTH)

    def build_ui_float3(
        self,
        label: str,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        indices: List[int],
        create_default_element_fn=lambda: Gf.Vec3f(0.0, 0.0, 0.0),
        get_interpolation_fn=None,
        value_model_class=UsdTupleArrayElementAttributeModel,
    ):
        value_models = []
        for component_index in range(3):
            value_models.append(
                value_model_class(
                    stage=stage,
                    attribute_paths=attribute_paths,
                    basis_curves=basis_curves,
                    indices=indices,
                    component_index=component_index,
                    metadata={},
                    self_refresh=False,
                    create_default_element_fn=create_default_element_fn,
                    get_interpolation_fn=get_interpolation_fn,
                )
            )
        self._value_models = self._value_models + value_models
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            kwargs = self._get_widget_kwargs(value_models)
            UsdPropertiesWidgetBuilder._create_label(label)
            UsdPropertiesWidgetBuilder._create_float_drag_per_channel_with_labels_and_control(
                value_models, {}, BasisCurvesCvWidget.COMPONENT_LABELS, **kwargs
            )

    def build_ui_float3_with_interpolation(
        self,
        label: str,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        indices: List[int],
        create_default_element_fn=lambda: Gf.Vec3f(0.0, 0.0, 0.0),
        get_interpolation_fn=None,
        value_model_class=UsdTupleArrayElementAttributeModel,
    ):
        interpolation_model = InterpolationsModel(
            stage=stage,
            attribute_paths=attribute_paths,
            basis_curves=basis_curves,
            create_default_element_fn=create_default_element_fn,
            get_interpolation_fn=get_interpolation_fn,
        )
        self._interpolation_models.append(interpolation_model)
        self._interpolation_model_values.append(interpolation_model.get_current_value())
        self.build_ui_float3(
            label,
            stage,
            attribute_paths,
            basis_curves,
            indices,
            create_default_element_fn,
            get_interpolation_fn,
            value_model_class,
        )
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            UsdPropertiesWidgetBuilder._create_label(f"{label} Interpolation")
            ui.ComboBox(interpolation_model)
            ui.Spacer(width=DEFAULT_ICON_WIDTH)

    def build_ui_points(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        indices: List[int],
    ):
        self.build_ui_float3(
            "Position",
            stage=stage,
            attribute_paths=attribute_paths,
            basis_curves=basis_curves,
            indices=indices,
            get_interpolation_fn=lambda s, ap, bc: UsdGeom.Tokens.vertex,
            value_model_class=CvAnchorElementAttributeModel,
        )

    def build_ui_readonly_stringfield(self, label: str, values: List[str]):
        unique_value_set = {}
        unique_values = []
        for value in values:
            if value not in unique_value_set:
                unique_value_set[value] = True
                unique_values.append(value)
        with ui.HStack(spacing=HORIZONTAL_SPACING):
            UsdPropertiesWidgetBuilder._create_label(label)
            if len(unique_values) == 1:
                value_widget = ui.StringField(name="models")
                value_widget.enabled = False
                value_widget.model.set_value(unique_values[0])
            else:
                mixed_style = get_style()
                mixed_style["Field::models"].update(mixed_style["Label::mixed_overlay"])
                value_widget = ui.StringField(name="models", style=mixed_style)
                value_widget.enabled = False
                value_widget.model.set_value("Mixed")

    def on_new_payload(self, payload) -> bool:
        self._payload = None
        if CvPayloadManager.is_cv_payload(payload):
            self._payload = payload
            return True
        return False

    def clean(self):
        self.reset()
        super().clean()

    def reset(self):
        if self._listener:
            self._listener.Revoke()
            self._listener = None
        if self._pending_dirty_task is not None:
            self._pending_dirty_task.cancel()
            self._pending_dirty_task = None
        self._interpolation_model_values = []
        self._interpolation_models = []
        self._payload = None
        self._pending_dirty_paths = set()
        self._value_models = []
        super().reset()


class BasisCurvesWidget(SchemaPropertiesWidget):
    def __init__(self, bezier_curve_edits: BezierCurveEdits):
        super().__init__("Basis Curves", UsdGeom.BasisCurves, include_inherited=False)
        self._curve_manip = get_interface()
        self._bezier_curve_edits = bezier_curve_edits
        self._curve_context = bezier_curve_edits.curve_context

    def clean(self):
        super().clean()

    def reset(self):
        super().reset()
        self._curve_event_sub = None

    def build_items(self):
        super().build_items()

        self._curve_event_sub = self._curve_manip.get_curves_event_stream(
            self._curve_context
        ).create_subscription_to_pop(self._on_curves_event, name="omni.curve.manipulator property widget")

    def build_impl(self):
        """
        See PropertyWidget.build_impl
        """
        if self._collapsable:
            self._collapsable_frame = ui.CollapsableFrame(
                self._title, build_header_fn=self._build_frame_header, collapsed=self._collapsed
            )

            def on_collapsed_changed(collapsed):
                self._collapsed = collapsed

            self._collapsable_frame.set_collapsed_changed_fn(on_collapsed_changed)
        else:
            self._collapsable_frame = ui.Frame(height=10, style={"Frame": {"padding": 5}})
        self._collapsable_frame.set_build_fn(self._build_frame)

    def _build_frame_header(self, collapsed, text: str, id: str = None):
        """Custom header for CollapsibleFrame"""
        if id is None:
            id = text

        if collapsed:
            alignment = ui.Alignment.RIGHT_CENTER
            width = 5
            height = 7
        else:
            alignment = ui.Alignment.CENTER_BOTTOM
            width = 7
            height = 5

        header_stack = ui.HStack(spacing=8)
        with header_stack:
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Label(text, style_type_name_override="CollapsableFrame.Header", width=0)
            ui.Spacer()
            with ui.VStack(content_clipping=True, width=0):
                self._edit_button = create_edit_cv_button()
                self._edit_button.set_mouse_pressed_fn(self._on_edit_cv)
                self._on_refresh_edit_button()

    def _on_refresh_edit_button(self):
        if self._edit_button:
            refresh_edit_cv_button(self._edit_button, self._curve_context)

    def _on_edit_cv(self, *args, **kwargs):
        if get_interface().is_in_curve_editing_mode(self._curve_context):
            omni.kit.commands.execute("DisableCurveEditing", curve_context=self._curve_context)
        else:
            prim_list_str = []
            stage = self._payload.get_stage()

            for path in self._payload:
                prim = stage.GetPrimAtPath(path)
                if prim.IsValid() and prim.IsA(UsdGeom.BasisCurves):
                    prim_list_str.append(path.pathString)

            if prim_list_str:
                omni.kit.commands.execute(
                    "EnableCurveEditing",
                    curve_context=self._curve_context,
                    paths=prim_list_str,
                    mode=CurveEditingModeType.DRAG,
                )

    def _on_curves_event(self, event: carb.events.IEvent):
        if event.type == int(CurvesEventType.BEGIN_CURVE_EDIT):
            self._on_refresh_edit_button()
        elif event.type == int(CurvesEventType.END_CURVE_EDIT):
            self._on_refresh_edit_button()


class BasisCurvesSchemeDelegate(PropertySchemeDelegate):
    def get_widgets(self, payload):
        widgets_to_build = []
        if self._should_enable_delegate(payload):
            widgets_to_build.append("path")
            widgets_to_build.append("transform")
            widgets_to_build.append("basis_curves")
            widgets_to_build.append("material_binding")

        return widgets_to_build

    def _should_enable_delegate(self, payload):
        stage = payload.get_stage()
        ret = True
        if stage:
            for prim_path in payload:
                prim = stage.GetPrimAtPath(prim_path)
                if prim.IsValid():
                    if not prim.IsA(UsdGeom.BasisCurves):
                        ret = False
                        break
                else:
                    ret = False
        return ret

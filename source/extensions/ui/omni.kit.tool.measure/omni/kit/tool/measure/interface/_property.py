# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import List

import omni.ui as ui
from omni.kit.property.usd import (
    GfVecAttributeModel,
    TfTokenAttributeModel,
    UsdPropertiesWidgetBuilder,
    UsdPropertyUiEntry,
)

try:
    from omni.kit.property.usd import UsdPropertiesWidget
except ImportError:
    # 106.5
    from omni.kit.property.usd.widgets import UsdPropertiesWidget

from omni.kit.property.usd.custom_layout_helper import CustomLayoutFrame, CustomLayoutProperty
from pxr import Gf, Sdf, Usd, Vt

from ..common import DisplayAxisSpace, LabelSize, Precision, UnitType


class MeasurementPropertyWidget(UsdPropertiesWidget):
    def __init__(self):
        super().__init__(title="Measurement", collapsed=False)

    def on_new_payload(self, payload) -> bool:
        """
        See PropertyWidget.on_new_payload
        """
        if not super().on_new_payload(payload):
            return False

        if len(self._payload) == 0:
            return False

        for path in self._payload:
            if not self._get_prim(path).HasAttribute("measure:uuid"):
                return False

        return True

    def _customize_props_layout(self, props):
        props.append(
            UsdPropertyUiEntry("measure:prop:axis_display", "", {Sdf.PrimSpec.TypeNameKey: "string"}, Usd.Attribute)
        )

        props.append(UsdPropertyUiEntry("measure:prop:unit", "", {Sdf.PrimSpec.TypeNameKey: "string"}, Usd.Attribute))
        props.append(
            UsdPropertyUiEntry("measure:prop:precision", "", {Sdf.PrimSpec.TypeNameKey: "string"}, Usd.Attribute)
        )
        props.append(
            UsdPropertyUiEntry("measure:prop:label_size", "", {Sdf.PrimSpec.TypeNameKey: "int"}, Usd.Attribute)
        )
        props.append(
            UsdPropertyUiEntry(
                "measure:prop:label_color",
                "",
                {Sdf.PrimSpec.TypeNameKey: "float4", "customData": {"default": Gf.Vec4f(0.0, 1.0, 1.0, 1.0)}},
                Usd.Attribute,
            )
        )

        frame = CustomLayoutFrame(hide_extra=True)
        with frame:
            CustomLayoutProperty("measure:prop:axis_display", "Name", build_fn=self._build_axis_fn)
            CustomLayoutProperty("measure:prop:unit", "Unit", build_fn=self._build_unit_fn)
            CustomLayoutProperty("measure:prop:precision", "Precision", build_fn=self._build_precision_fn)
            CustomLayoutProperty("measure:prop:label_size", "Label Size", build_fn=self._build_size_fn)
            CustomLayoutProperty("measure:prop:label_color", "Label Color", build_fn=self._build_color_ui)

        return frame.apply(props)

    def _build_axis_fn(
        self,
        stage,
        attr_name,
        metadata,
        property_type,
        prim_paths: List[Sdf.Path],
        additional_label_kwargs={},
        additional_widget_kwargs={},
    ):
        if not attr_name or not property_type:
            return

        # Check to see if its a valid type to display axis
        for path in prim_paths:
            mode = self._get_prim(path).GetAttribute("measure:meta:tool_mode").Get()
            if mode not in [0, 6]:
                text = "Axis Display is not available.\nA non-supported measurement is in the current selection."
                with ui.VStack():
                    UsdPropertiesWidgetBuilder._create_label(text)
                    ui.Spacer(height=12)
                return

        display_names = [display.name for display in DisplayAxisSpace]

        metadata = {
            Sdf.PrimSpec.TypeNameKey: "token",
            "allowedTokens": Vt.TokenArray(len(display_names), display_names),
            "customData": {"default": DisplayAxisSpace.NONE.name},
        }

        model = TfTokenAttributeModel(stage, [path.AppendProperty(attr_name) for path in prim_paths], False, metadata)

        with ui.HStack(spacing=4):
            UsdPropertiesWidgetBuilder._create_label("Axis Display", metadata)

            with ui.ZStack():
                value_widget = ui.ComboBox(model, name="Axis Display")
                mixed_overlay = UsdPropertiesWidgetBuilder._create_mixed_text_overlay()

            UsdPropertiesWidgetBuilder._create_control_state(
                model=model, value_widget=value_widget, mixed_overlay=mixed_overlay, name="AxisDisplay"
            )

        return model

    def _build_unit_fn(
        self,
        stage,
        attr_name,
        metadata,
        property_type,
        prim_paths: List[Sdf.Path],
        additional_label_kwargs={},
        additional_widget_kwargs={},
    ):
        if not attr_name or not property_type:
            return

        for path in prim_paths:
            mode = self._get_prim(path).GetAttribute("measure:meta:tool_mode").Get()
            if mode == 2:  # Angle Measurement uses Degrees.
                text = "Unit type is not available.\nAn Angle Measurement is in the current selection."
                with ui.VStack():
                    UsdPropertiesWidgetBuilder._create_label(text)
                    ui.Spacer(height=12)
                return

        unit_names = [unit.name for unit in UnitType]

        metadata = {
            Sdf.PrimSpec.TypeNameKey: "token",
            "allowedTokens": Vt.TokenArray(len(unit_names), unit_names),
            "customData": {"default": UnitType.CENTIMETERS.name},
        }

        model = TfTokenAttributeModel(stage, [path.AppendProperty(attr_name) for path in prim_paths], False, metadata)

        with ui.HStack(spacing=4):
            UsdPropertiesWidgetBuilder._create_label("Unit", metadata)

            with ui.ZStack():
                value_widget = ui.ComboBox(model, name="Unit")
                mixed_overlay = UsdPropertiesWidgetBuilder._create_mixed_text_overlay()

            UsdPropertiesWidgetBuilder._create_control_state(
                model=model, value_widget=value_widget, mixed_overlay=mixed_overlay, name="Unit"
            )

        return model

    def _build_precision_fn(
        self,
        stage,
        attr_name,
        metadata,
        property_type,
        prim_paths: List[Sdf.Path],
        additional_label_kwargs={},
        additional_widget_kwargs={},
    ):
        if not attr_name or not property_type:
            return

        precision_names = [precision.name for precision in Precision]

        metadata = {
            Sdf.PrimSpec.TypeNameKey: "token",
            "allowedTokens": Vt.TokenArray(len(precision_names), precision_names),
            "customData": {"default": Precision.HUNDRETH.name},
        }

        model = TfTokenAttributeModel(stage, [path.AppendProperty(attr_name) for path in prim_paths], False, metadata)

        with ui.HStack(spacing=4):
            UsdPropertiesWidgetBuilder._create_label("Precision", metadata)

            with ui.ZStack():
                value_widget = ui.ComboBox(model, name="Precision")
                mixed_overlay = UsdPropertiesWidgetBuilder._create_mixed_text_overlay()

            UsdPropertiesWidgetBuilder._create_control_state(
                model=model, value_widget=value_widget, mixed_overlay=mixed_overlay, name="Precision"
            )

        return model

    def _build_size_fn(
        self,
        stage,
        attr_name,
        metadata,
        property_type,
        prim_paths: List[Sdf.Path],
        additional_label_kwargs={},
        additional_widget_kwargs={},
    ):
        if not attr_name or not property_type:
            return

        size_names = [size.name for size in LabelSize]

        metadata = {
            Sdf.PrimSpec.TypeNameKey: "token",
            "allowedTokens": Vt.TokenArray(4, size_names),
            "customData": {"default": LabelSize.MEDIUM.name},
        }

        model = TfTokenAttributeModel(stage, [path.AppendProperty(attr_name) for path in prim_paths], False, metadata)

        with ui.HStack(spacing=4):
            UsdPropertiesWidgetBuilder._create_label("Label Size", metadata)

            with ui.ZStack():
                value_widget = ui.ComboBox(model, name="Label_Size")
                mixed_overlay = UsdPropertiesWidgetBuilder._create_mixed_text_overlay()

            UsdPropertiesWidgetBuilder._create_control_state(
                model=model, value_widget=value_widget, mixed_overlay=mixed_overlay, name="Label_Size"
            )

        return model

    def _build_color_ui(
        self,
        stage,
        attr_name,
        metadata,
        property_type,
        prim_paths: List[Sdf.Path],
        additional_label_kwargs={},
        additional_widget_kwargs={},
    ):
        if not attr_name or not property_type:
            return

        model = GfVecAttributeModel(
            stage,
            [path.AppendProperty(attr_name) for path in prim_paths],
            4,
            Sdf.ValueTypeNames.Float4.type,
            False,
            metadata,
        )

        with ui.HStack(spacing=4):
            label = UsdPropertiesWidgetBuilder._create_label("Label Color", metadata)

            with ui.HStack(spacing=4):
                value_widget, mixed_overlay = UsdPropertiesWidgetBuilder._create_multi_float_drag_with_labels(
                    labels=[("R", 0xFF5555AA), ("G", 0xFF76A371), ("B", 0xFFA07D4F), ("A", 0xFF000000)],
                    comp_count=4,
                    model=model,
                )

                ui.Spacer(width=4)
                color_widget = ui.ColorWidget(model, width=65, height=0)

                UsdPropertiesWidgetBuilder._create_control_state(
                    value_widget=color_widget,
                    mixed_overlay=mixed_overlay,
                    extra_widgets=[color_widget],
                    model=model,
                    label=label,
                )

        return model

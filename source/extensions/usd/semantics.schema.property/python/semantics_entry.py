# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import carb
import omni.ui as ui
from omni.kit.window.property.templates import HORIZONTAL_SPACING, LABEL_HEIGHT, LABEL_WIDTH, LABEL_WIDTH_LIGHT

# from .ext import P1_LABEL_STYLE
from pxr import Sdf, Semantics, Tf, Trace, Usd, UsdGeom, UsdSemantics

P1_LABEL_STYLE = {"color": 0xFF9A9A9A}


def property_log(level, message):
    if level == "info":
        carb.log_info(f"[semantics.schema.property] {message}")
    if level == "warn":
        carb.log_warn(f"[semantics.schema.property] {message}")
    if level == "error":
        carb.log_error(f"[semantics.schema.property] {message}")


class PrimSemantics:
    def __init__(self, prim) -> None:
        self._prim = prim
        self._semantics_v2 = []
        self._semantics_v1 = []

        self._get_current_semantics()

    @property
    def prim_path(self):
        return self._prim.GetPath().pathString

    @property
    def has_semantics(self):
        return self.has_semantics_v1 or self.has_semantics_v2

    @property
    def has_semantics_v1(self):
        return len(self._semantics_v1) > 0

    @property
    def has_semantics_v2(self):
        return len(self._semantics_v2) > 0

    def _get_current_semantics(self):
        # [OM-96866] If prim doesn't have the semanticsAPI, don't build entry
        if not self._prim.HasAPI("SemanticsLabelsAPI") and not self._prim.HasAPI("SemanticsAPI"):
            return

        # Get all the semantic instance names that currently exist
        semantic_instance_names = []
        for schema in self._prim.GetAppliedSchemas():
            if "SemanticsLabelsAPI" in schema:
                semantic = (schema.split(":")[1], "SemanticsLabelsAPI")
                semantic_instance_names.append(semantic)
            # Also support the old semantics API
            elif "SemanticsAPI" in schema:
                semantic = (schema.split(":")[1], "SemanticsAPI")
                semantic_instance_names.append(semantic)

        # Get all the semantic info for each semantic instance
        if not len(semantic_instance_names) == 0:
            for instance_name in semantic_instance_names:
                data = {}
                if instance_name[1] == "SemanticsLabelsAPI":
                    data["api"] = "SemanticsLabelsAPI"
                    sem = UsdSemantics.LabelsAPI(self._prim, instance_name[0])
                    data["name"] = instance_name[0]
                    data["labels"] = sem.GetLabelsAttr().Get()
                    if sem.GetLabelsAttr().Get() == None:
                        data["ui_hide"] = True
                    else:
                        data["ui_hide"] = False

                    self._semantics_v2.append(data)
                elif instance_name[1] == "SemanticsAPI":
                    data["api"] = "SemanticsAPI"
                    data["name"] = instance_name[0]
                    sem = Semantics.SemanticsAPI
                    p_sem = sem.Get(self._prim, instance_name[0])
                    data["type"] = p_sem.GetSemanticTypeAttr().Get()
                    data["data"] = p_sem.GetSemanticDataAttr().Get()
                    self._semantics_v1.append(data)

    def _update_labels_attr(self, value_model: ui.StringField, inst_name: str, old_label: str):
        if not inst_name:
            return

        sem = UsdSemantics.LabelsAPI(self._prim, inst_name)
        labelsAttr = sem.GetLabelsAttr()

        if ":" in value_model.as_string:
            property_log("warn", "Data string cannot contain ':'.")
            value_model.set_value(old_label)
            return

        if value_model.as_string == "":
            property_log("warn", "Data string cannot be blank.")
            value_model.set_value(old_label)
            return

        with Sdf.ChangeBlock():
            labels = labelsAttr.Get()
            labels_list = list(labels)
            if old_label in labels_list:
                labels_list[labels_list.index(old_label)] = value_model.as_string
            labelsAttr.Set(labels_list)

    def _update_type_attr(self, value_model: ui.StringField, inst_name: str):
        if not inst_name:
            return

        sem = Semantics.SemanticsAPI.Apply(self._prim, inst_name)
        typeAttr = sem.GetSemanticTypeAttr()

        if ":" in value_model.as_string:
            property_log("warn", "Type string cannot contain ':'.")
            value_model.set_value(typeAttr.Get())
            return

        if value_model.as_string == "":
            property_log("warn", "Type string cannot be blank.")
            value_model.set_value(typeAttr.Get())
            return

        with Sdf.ChangeBlock():
            typeAttr.Set(str(value_model.as_string))

    def _update_data_attr(self, value_model: ui.StringField, inst_name: str):
        if not inst_name:
            return

        sem = Semantics.SemanticsAPI.Apply(self._prim, inst_name)
        dataAttr = sem.GetSemanticDataAttr()

        if ":" in value_model.as_string:
            property_log("warn", "Data string cannot contain ':'.")
            value_model.set_value(dataAttr.Get())
            return

        if value_model.as_string == "":
            property_log("warn", "Data string cannot be blank.")
            value_model.set_value(dataAttr.Get())
            return

        with Sdf.ChangeBlock():
            dataAttr.Set(str(value_model.as_string))

    def _on_value_changed(self, value_model: ui.StringField.model, ui_elem: ui.StringField):
        if value_model.as_string == "" or ":" in value_model.as_string:
            ui_elem.set_style({"border_width": 1, "border_color": 0xFF0000FF})
        else:
            ui_elem.set_style({})

    def draw_ui(self):
        with ui.VStack(spacing=5):
            for semantic in self._semantics_v2:
                with ui.HStack(spacing=HORIZONTAL_SPACING):
                    ui.Label(semantic["name"], identifier="lbl_semantic_id", style=P1_LABEL_STYLE, width=LABEL_WIDTH)
                    ui.Spacer(width=HORIZONTAL_SPACING)
                    with ui.VStack():
                        for label in semantic["labels"]:
                            m_data = ui.StringField(identifier="txt_semantic_label")
                            m_data.model.set_value(label)
                            m_data.model.add_value_changed_fn(lambda n, m=m_data,: self._on_value_changed(n, m))
                            m_data.model.add_end_edit_fn(
                                lambda n, m=semantic["name"], c=label: self._update_labels_attr(n, m, c)
                            )
                            ui.Spacer()
                    ui.Spacer(width=HORIZONTAL_SPACING * 3)
            if len(self._semantics_v1) > 0:
                property_log("warn", "Semantics.SemanticsAPI is deprecated, please use SemanticsLabelsAPI instead.")
                with ui.HStack():
                    ui.Label(
                        "Old Semantics Schema",
                        identifier="lbl_deprecated_semantics",
                        style={"color": 0xFF9A9A9A},
                        width=0,
                    )
                    ui.Spacer(width=HORIZONTAL_SPACING)
                    ui.Line(style={"color": 0x338A8777}, width=ui.Fraction(1))
                for semantic in self._semantics_v1:
                    with ui.HStack(spacing=HORIZONTAL_SPACING):
                        ui.Label(
                            semantic["name"], identifier="lbl_semantic_id", style=P1_LABEL_STYLE, width=LABEL_WIDTH
                        )
                        ui.Spacer(width=HORIZONTAL_SPACING)
                        m_type = ui.StringField(identifier="txt_semantic_type")
                        m_type.model.set_value(semantic["type"])
                        m_type.model.add_value_changed_fn(lambda n, m=m_type: self._on_value_changed(n, m))
                        m_type.model.add_end_edit_fn(lambda n, m=semantic["name"]: self._update_type_attr(n, m))
                        ui.Spacer(width=HORIZONTAL_SPACING)
                        m_data = ui.StringField(identifier="txt_semantic_data")
                        m_data.model.set_value(semantic["data"])
                        m_data.model.add_value_changed_fn(lambda n, m=m_data: self._on_value_changed(n, m))
                        m_data.model.add_end_edit_fn(lambda n, m=semantic["name"]: self._update_data_attr(n, m))
                        ui.Spacer(width=HORIZONTAL_SPACING * 3)
            ui.Spacer()

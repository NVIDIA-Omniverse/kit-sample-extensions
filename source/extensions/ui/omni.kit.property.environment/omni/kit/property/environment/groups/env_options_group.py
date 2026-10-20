# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import weakref
from pathlib import Path
from typing import Dict, Optional

import carb.settings
from omni import ui
from omni.kit.environment.core import (
    GROUND_DEFAULT_SIZE,
    EnvironmentProperties,
    GroundSettings,
    GroundType,
    ResetButton,
    SettingModel,
    UsdModelBuilder,
)
from omni.kit.property.usd import PrimSelectionPayload
from pxr import Sdf, Usd

from .property_group import AbstractPropertyGroup

CURRENT_PATH = Path(__file__).parent
EXT_PATH = CURRENT_PATH.parent.parent.parent.parent.parent


ENGINE_TO_MATTE_SHADOW_SETTING = {"iray": "/rtx/iray/environment_dome_ground", "rtx": "/rtx/shadows/enabled"}
SETTING_ACTIVE_RENDER = "/renderer/active"
SETTING_RTX_RENDER_MODE = "/rtx/rendermode"

GROUND_TYPES = [GroundType.OFF, GroundType.ON, GroundType.SHADOWS]


class EnvironmentOptionsGroup(AbstractPropertyGroup):
    def __init__(self, payload: PrimSelectionPayload):
        self._ground_type_index_model = ui.SimpleIntModel()
        self._ground_type_index_sub_id = None
        self._ground_type_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.GROUND_TYPE, value_type=Sdf.ValueTypeNames.String, default=GroundType.OFF
        )
        self._ground_type_sub_id = None
        self._ground_size_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.GROUND_SIZE, value_type=Sdf.ValueTypeNames.Int, default=GROUND_DEFAULT_SIZE, min=1
        )
        self._ground_size_sub_id = None
        self._ground_path_model = SettingModel(GroundSettings.PATH)
        self._ground_path_sub_id = self._ground_path_model.add_value_changed_fn(self._on_ground_path_changed)

        self._payload = payload
        self._ground_prim: Optional[Usd.Prim] = None
        self._settings = carb.settings.get_settings()
        self._matte_shadow_change_cb: Dict[str, callable] = {}

        try:
            from omni.kit.property.material.scripts.usd_binding_widget import UsdBindingAttributeWidget

            self._binding_widget = UsdBindingAttributeWidget(EXT_PATH)
        except ImportError:
            from omni.kit.property.material.scripts.widgets import MaterialBindingWidget

            self._binding_widget = MaterialBindingWidget(extension_path=EXT_PATH)

        # Donot show frame header
        self._binding_widget._collapsable = False

        super().__init__("Environment Options")

    def destroy(self):
        self._ground_path_model.remove_value_changed_fn(self._ground_path_sub_id)
        if self._ground_type_sub_id is not None:
            self._ground_type_model.remove_value_changed_fn(self._ground_type_sub_id)
        if self._ground_type_index_sub_id is not None:
            self._ground_type_index_model.remove_value_changed_fn(self._ground_type_index_sub_id)
        pass

    def on_new_payload(self, payload: PrimSelectionPayload):
        self._payload = payload

        # Material binding
        if self._payload is not None:
            payload = PrimSelectionPayload(
                weakref.ref(self._payload.get_stage()),
                [Sdf.Path(self._ground_path_model.as_string)] if self._ground_path_model.as_string else [],
            )
            self._binding_widget.on_new_payload(payload)

    def _build_widgets(self):
        with ui.VStack(height=0, spacing=5):
            with ui.HStack(height=0):
                self._create_label("Ground")
                collection = ui.RadioCollection(self._ground_type_index_model)
                with ui.HStack(spacing=8):
                    for ground_type in GROUND_TYPES:
                        with ui.HStack():
                            ui.RadioButton(
                                radio_collection=collection,
                                width=20,
                                image_width=14,
                                style_type_name_override="TypeOption",
                                aligment=ui.Alignment.LEFT,
                            )

                            ui.Spacer(width=0)
                            ui.Label(ground_type, width=5)
                            ui.Spacer(width=0)
                ui.Spacer()
                ResetButton(self._ground_type_model)

            # Ground size
            self._ground_size_container = ui.HStack(height=0)
            with self._ground_size_container:
                self._create_label("Ground Size")
                self._ground_size = self._create_int_drag(self._ground_size_model)
                with ui.ZStack(width=0):
                    ui.Rectangle(style_type_name_override="Field.Frame")
                    ui.Label("cm", name="label", width=20)
                ui.Spacer(width=10)
                ResetButton(self._ground_size_model)

            # Material binding
            self._material_container = ui.ZStack()
            with self._material_container:
                ui.Rectangle(style_type_name_override="Material.Frame")
                with ui.VStack():
                    ui.Spacer(height=5)
                    self._binding_widget.build()
                    ui.Spacer(height=5)

        self._ground_type_sub_id = self._ground_type_model.add_value_changed_fn(self._on_ground_type_changed)
        self._ground_type_index_sub_id = self._ground_type_index_model.add_value_changed_fn(
            self._on_ground_type_index_changed
        )

        self._ground_size_container.enabled = self._ground_type_model.as_string != GroundType.OFF
        self._material_container.visible = self._ground_type_model.as_string != GroundType.OFF

        self._on_ground_type_changed(self._ground_type_model)
        self.on_new_payload(self._payload)

    def _on_ground_type_changed(self, model: ui.AbstractValueModel) -> None:
        self._ground_type_index_model.set_value(GROUND_TYPES.index(model.as_string))
        if model.as_string == GroundType.OFF:
            # Ground OFF
            self._ground_size_container.enabled = False
            self._material_container.visible = False
        elif model.as_string == GroundType.ON:
            # Ground ON
            self._ground_size_container.enabled = True
            self._material_container.visible = True
        elif model.as_string == GroundType.SHADOWS:
            # Shadows Only
            self._ground_size_container.enabled = True
            self._material_container.visible = False

    def _on_ground_type_index_changed(self, model: ui.AbstractValueModel) -> None:
        ground_type = GROUND_TYPES[model.as_int]
        if ground_type != self._ground_type_model.as_string:
            self._ground_type_model.set_value(ground_type)

    def _on_ground_path_changed(self, model: SettingModel) -> None:
        path = model.as_string
        if path and self._payload is not None:
            payload = PrimSelectionPayload(weakref.ref(self._payload.get_stage()), [Sdf.Path(path)])
            self._binding_widget.on_new_payload(payload)

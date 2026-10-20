# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.ui as ui
from omni.kit.property.usd.usd_property_widget import UsdPropertiesWidget
from omni.kit.property.usd.usd_property_widget_builder import UsdPropertiesWidgetBuilder
from pxr import Sdf, Tf, Usd

from .variant_property_models import VariantSetModel
from .variant_property_widget_builder import UsdVariantPropertiesWidgetBuilder


class VariantsWidget(UsdPropertiesWidget):
    def __init__(self, variant_set, prim_path, prop_path):
        super().__init__(title="Variants", collapsed=False, multi_edit=False)
        self._variant_set = variant_set
        self._prim_path = Sdf.Path(prim_path).StripAllVariantSelections()
        self._prop_path = Sdf.Path(prop_path)

    def reset(self):
        if self._listener:
            self._listener.Revoke()
            self._listener = None
        super().reset()

    def on_new_payload(self, payload):
        """
        See PropertyWidget.on_new_payload
        """

        if not super().on_new_payload(payload):
            return False

        if not self._payload:
            return False

        prim = self._get_prim(self._prim_path)

        if not prim:
            return False

        if not prim.HasVariantSets():
            return False

        return True

    def build_items(self):
        self.reset()

        if len(self._payload) == 0:
            return

        last_prim = self._get_prim(self._prim_path)
        if not last_prim:
            return

        stage = last_prim.GetStage()
        if not stage:
            return

        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)

        set_names = [self._variant_set]

        with ui.VStack():
            for name in set_names:
                self._build_variant_set(stage, last_prim.GetPath(), name)
                self._any_item_visible = True

    def _build_variant_set(self, stage, prim_path, name):
        with ui.HStack():
            filter_text = self._filter.name
            UsdVariantPropertiesWidgetBuilder.create_label(
                name,
                additional_label_kwargs={
                    "width": 154,
                    "highlight": filter_text,
                    "prop_path": self._prop_path,
                    "is_variant": True,
                },
            )
            prim_paths = [self._prim_path]
            model = VariantSetModel(stage, prim_paths, name, False)
            ui.Spacer(width=8)
            with ui.ZStack(alignment=ui.Alignment.CENTER):
                combo_widget = ui.ComboBox(model)
                combo_widget.identifier = f"combo_variant_{name.lower()}"
                mixed_widget = UsdVariantPropertiesWidgetBuilder._create_mixed_text_overlay()
                mixed_widget.identifier = f"mixed_variant_{name.lower()}"
            ui.Spacer(width=20)
            if model.is_ambiguous():
                mixed_widget.visible = True

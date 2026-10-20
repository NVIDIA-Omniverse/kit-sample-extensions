# Copyright (c) 2018-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.commands
from omni.kit.property.usd.prim_path_widget import PrimPathWidget
from omni.kit.property.usd.prim_selection_payload import PrimSelectionPayload
from pxr import Sdf, Usd, UsdGeom

ZONE_SIGN_ATTRIBUTE_NAME = "zoneSign"
ZONE_SIGN_ADDITIVE_MENU_ENTRY = "Zone Sign/Additive"
ZONE_SIGN_SUBTRACTIVE_MENU_ENTRY = "Zone Sign/Subtractive"
ZONE_SIGN_ADDITIVE_ATTRIBUTE_VALUE = "additive"
ZONE_SIGN_SUBTRACTIVE_ATTRIBUTE_VALUE = "subtractive"


class CurveZoneSignMenu:
    """
    Class to create and manage the zone sign menu item
    """

    def __init__(self):
        super().__init__()
        self._additive_item = None
        self._subtractive_item = None
        self.on_startup()

    def on_startup(self) -> None:
        """
        Method called by the extension on startup to create the menu items.
        :return: None
        """
        self._additive_item = PrimPathWidget.add_button_menu_entry(
            ZONE_SIGN_ADDITIVE_MENU_ENTRY,
            show_fn=lambda objects: self._show_item(objects),
            onclick_fn=lambda payload: self._on_zone_sign(payload, ZONE_SIGN_ADDITIVE_ATTRIBUTE_VALUE),
        )
        self._subtractive_item = PrimPathWidget.add_button_menu_entry(
            ZONE_SIGN_SUBTRACTIVE_MENU_ENTRY,
            show_fn=lambda objects: self._show_item(objects),
            onclick_fn=lambda payload: self._on_zone_sign(payload, ZONE_SIGN_SUBTRACTIVE_ATTRIBUTE_VALUE),
        )

    def on_shutdown(self) -> None:
        if self._additive_item:
            PrimPathWidget.remove_button_menu_entry(self._additive_item)
        if self._subtractive_item:
            PrimPathWidget.remove_button_menu_entry(self._subtractive_item)
        self._additive_item = None
        self._subtractive_item = None

    def _show_item(self, objects: dict):
        return self._is_selected_all_curve(objects)

    def _on_zone_sign(self, payload: PrimSelectionPayload, zoneSignValue):
        if payload is None:
            return

        stage = payload.get_stage()
        if not stage:
            return

        zone_attr_name = ZONE_SIGN_ATTRIBUTE_NAME
        for path in payload:
            if path:
                selected_prim = stage.GetPrimAtPath(path)
                zone_attr = selected_prim.GetAttribute(zone_attr_name)
                if not zone_attr:
                    omni.kit.commands.execute(
                        "CreateUsdAttribute",
                        prim=selected_prim,
                        attr_name=zone_attr_name,
                        attr_type=Sdf.ValueTypeNames.Token,
                        attr_value=zoneSignValue,
                    )
                else:
                    omni.kit.commands.execute(
                        "ChangePropertyCommand",
                        prop_path=path.AppendProperty(zone_attr_name),
                        value=zoneSignValue,
                        prev=zone_attr.Get(),
                    )

    @staticmethod
    def _is_selected_all_curve(objects: dict):
        if "prim_list" not in objects or "stage" not in objects:
            return False

        stage = objects["stage"]
        if not stage:
            return False

        prim_list = objects["prim_list"]
        if len(prim_list) < 1:
            return False

        for item in prim_list:
            if isinstance(item, Sdf.Path):
                prim = stage.GetPrimAtPath(item)
            elif isinstance(item, Usd.Prim):
                prim = item
            if not prim.IsA(UsdGeom.BasisCurves):
                return False

        return True

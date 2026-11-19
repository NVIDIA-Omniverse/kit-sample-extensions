# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb
import omni.kit.context_menu
import omni.kit.menu.utils
import omni.ui as ui
from omni.kit.menu.utils import MenuItemDescription

from ..bindings import CurveEditingModeType
from .bezier_curve_edits import BezierCurveEdits


class MenubarMenu:
    def __init__(self, bezier_curve_edits: BezierCurveEdits):
        self._menu_added = False
        self._add_create_menu()
        self._context_menus_added = False
        self._add_context_menus()
        self._bezier_curve_edits = bezier_curve_edits

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._menu_added:
            omni.kit.menu.utils.remove_menu_items(self._create_menu_list, "Create")
            self._menu_added = False
        if self._context_menus_added:
            self._context_menus = []
            self._context_menus_added = False

    def _add_create_menu(self):
        if not self._menu_added:
            curves_sub_menu_list = [
                MenuItemDescription(
                    name="New Curve",
                    onclick_fn=lambda *_: self._on_bezier_curve_tool(mode=CurveEditingModeType.DRAG),
                )
            ]

            self._create_menu_list = [
                MenuItemDescription(
                    name="BasisCurves", glyph="menu_curve.svg", appear_after="Xform", sub_menu=curves_sub_menu_list
                )
            ]
            omni.kit.menu.utils.add_menu_items(self._create_menu_list, "Create")
            self._menu_added = True

    def _add_context_menus(self):
        if not self._context_menus_added:
            context_menu_dict = {
                "glyph": "menu_curve.svg",
                "name": {
                    "BasisCurves": [
                        {
                            "name": "New Curve",
                            "onclick_fn": lambda *_: self._on_bezier_curve_tool(mode=CurveEditingModeType.DRAG),
                        }
                    ]
                },
            }

            self._context_menus = []
            self._context_menus.append(
                omni.kit.context_menu.add_menu(context_menu_dict, "CREATE", "omni.kit.widget.stage")
            )
            self._context_menus.append(
                omni.kit.context_menu.add_menu(context_menu_dict, "CREATE", "omni.kit.viewport.window")
            )

            self._context_menus_added = True

    def _on_bezier_curve_tool(self, mode: CurveEditingModeType):
        self._bezier_curve_edits.create_new_bezier_curve_and_edit(mode=mode)

    def _on_pencil_tool(self, *args, **kwargs):
        self._on_bezier_curve_tool(mode=CurveEditingModeType.DRAW)

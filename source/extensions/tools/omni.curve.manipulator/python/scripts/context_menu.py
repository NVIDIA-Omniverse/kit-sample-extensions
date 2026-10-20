# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import carb
import omni.kit.commands
import omni.kit.context_menu
import omni.kit.undo
import omni.ui as ui
from pxr import UsdGeom

from ..bindings import CurveEditingModeType, CurveManipulatorContext, get_interface
from .bezier_curve_edits_context import BezierCurveEditsContextManager
from .utils import get_array_index_offset_and_curve_index


class DefaultMenuDelegate(ui.MenuDelegate):
    """
    Show the new "fancy" viewport 2.0 style menu
    """

    def get_style(self):
        from omni.kit.context_menu import style

        return style.MENU_STYLE


class ContextMenu:
    @classmethod
    def startup(cls):
        cls._curve_manip = get_interface()

        cls._menu_delegate = DefaultMenuDelegate()

        cls._menu_entry_handles = []
        cls._stage_menu_entry_handles = []

        cls._add_break_tangents_menu()
        cls._add_smooth_tangents_menu()
        cls._add_even_tangents_menu()
        cls._add_uneven_tangents_menu()

        cls._add_sep()

        cls._add_delete_cvs_menu()
        cls._add_split_cvs_menu()

        cls._add_sep()

        cls._add_bezier_menu()
        cls._add_bezier_corner_menu()
        cls._add_corner_menu()

        cls._add_sep2()

        cls._add_open_close_curves_menu()
        cls._add_enable_cv_edit_menu()
        cls._add_disable_cv_edit_menu()

        manager = omni.kit.app.get_app().get_extension_manager()
        cls._hooks = manager.subscribe_to_extension_enable(
            on_enable_fn=lambda _: cls._register_stage_context_menu(),
            on_disable_fn=lambda _: cls._unregister_stage_context_menu(),
            ext_name="omni.kit.window.stage",
            hook_name="omni.curve.manipulator omni.kit.window.preferences listener",
        )

    @classmethod
    def shutdown(cls):
        for handle in cls._menu_entry_handles:
            handle.release()
        cls._menu_entry_handles.clear()

        cls._unregister_stage_context_menu()
        cls._hooks = None

        cls._menu_delegate = None

    @classmethod
    def on_context_menu(cls, payload):
        menu_list = omni.kit.context_menu.get_menu_dict("MENU", "omni.curve.manipulator")

        # get context menu core functionality & check its enabled
        context_menu = omni.kit.context_menu.get_instance()
        if context_menu is None:
            carb.log_error("context_menu is disabled!")
            return

        context_menu.show_context_menu("cv_context_menu", payload, menu_list, delegate=cls._menu_delegate)

    @classmethod
    def _add_break_tangents_menu(cls):
        menu = {
            "name": "Break Anchor Tangents",
            "show_fn": cls._can_show,
            "onclick_fn": cls._break_tangents,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_smooth_tangents_menu(cls):
        menu = {
            "name": "Smooth Anchor Tangents",
            "show_fn": cls._can_show,
            "onclick_fn": cls._smooth_tangents,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_even_tangents_menu(cls):
        menu = {
            "name": "Even Anchor Tangents",
            "show_fn": cls._can_show,
            "onclick_fn": cls._even_tangents,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_uneven_tangents_menu(cls):
        menu = {
            "name": "Uneven Anchor Tangents",
            "show_fn": cls._can_show,
            "onclick_fn": cls._uneven_tangents,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_sep(cls):
        menu = {
            "name": "",
            "show_fn": cls._can_show,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_bezier_menu(cls):
        menu = {
            "name": "Bezier",
            "show_fn": cls._can_show,
            "onclick_fn": cls._bezier,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_bezier_corner_menu(cls):
        menu = {
            "name": "Bezier Corner",
            "show_fn": cls._can_show,
            "onclick_fn": cls._bezier_corner,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_corner_menu(cls):
        menu = {
            "name": "Corner",
            "show_fn": cls._can_show,
            "onclick_fn": cls._corner,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_delete_cvs_menu(cls):
        menu = {
            "show_fn": cls._can_delete,
            "name": {
                "Delete...": [
                    {"name": "Delete CV(s)", "onclick_fn": cls._delete_cvs},
                    {
                        "name": "Delete and Split Curves at CV(s)",
                        "onclick_fn": lambda object: cls._delete_and_split_at_cvs(object, False),
                    },
                    {
                        "name": "Delete and Split Curves at CV(s) to new BasisCurves",
                        "onclick_fn": lambda object: cls._delete_and_split_at_cvs(object, True),
                    },
                ]
            },
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_split_cvs_menu(cls):
        menu = {
            "show_fn": cls._can_split,
            "name": {
                "Split...": [
                    {
                        "name": "Split Curves at CV(s)",
                        "onclick_fn": lambda object: cls._split_at_cvs(object, False),
                    },
                    {
                        "name": "Split Curves at CV(s) to new BasisCurves",
                        "onclick_fn": lambda object: cls._split_at_cvs(object, True),
                    },
                ]
            },
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_sep2(cls):
        menu = {
            "name": "",
            "show_fn": lambda object: cls._can_show(object)
            and cls._curve_manip.is_in_curve_editing_mode(cls._get_curve_context(object)),
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_open_close_curves_menu(cls):
        menu = {
            "name": "Open/Close Curve(s)",
            "show_fn": lambda object: cls._curve_manip.is_in_curve_editing_mode(cls._get_curve_context(object)),
            "onclick_fn": cls._open_close_curves,
        }
        cls._menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.curve.manipulator"))

    @classmethod
    def _add_enable_cv_edit_menu_impl(cls, extension: str):
        menu = {
            "name": "Edit Control Vertices",
            "glyph": "pencil.svg",
            "show_fn": cls._can_enabled_cv_edit,
            "onclick_fn": cls._enable_cv_edit,
        }
        return omni.kit.context_menu.add_menu(menu, "MENU", extension)

    @classmethod
    def _add_enable_cv_edit_menu(cls):
        cls._menu_entry_handles.append(cls._add_enable_cv_edit_menu_impl("omni.kit.viewport.window"))

    @classmethod
    def _add_disable_cv_edit_menu_impl(cls, extension: str):
        menu = {
            "name": "Stop Editing Control Vertices",
            # "glyph": "none.svg",
            "show_fn": lambda object: cls._curve_manip.is_in_curve_editing_mode(cls._get_curve_context(object)),
            "onclick_fn": lambda object: omni.kit.commands.execute(
                "DisableCurveEditing", curve_context=cls._get_curve_context(object)
            ),
        }
        return omni.kit.context_menu.add_menu(menu, "MENU", extension)

    @classmethod
    def _add_disable_cv_edit_menu(cls):
        cls._menu_entry_handles.append(cls._add_disable_cv_edit_menu_impl("omni.kit.viewport.window"))
        cls._menu_entry_handles.append(cls._add_disable_cv_edit_menu_impl("omni.curve.manipulator"))

    @classmethod
    def _can_show(cls, object: dict):
        cv_dict = object.get("cv_dict", [])
        for basis_curves, ids in cv_dict.items():
            type = basis_curves.GetTypeAttr().Get()
            basis = basis_curves.GetBasisAttr().Get()
            # Only show for cubic bezier curve for now until linear curve is better supported
            if type != UsdGeom.Tokens.cubic or basis != UsdGeom.Tokens.bezier:
                return False

        return len(cv_dict) > 0

    @classmethod
    def _do_curve_edit_on_all_prims(cls, object, fn_name):
        cv_dict = object.get("cv_dict", [])
        fn = getattr(cls._get_bezier_curve_edits_context(object), fn_name)

        try:
            omni.kit.undo.begin_group()
            for basis_curves, ids in cv_dict.items():
                fn(basis_curves, ids)
        finally:
            omni.kit.undo.end_group()

    @classmethod
    def _break_tangents(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "break_tangents")

    @classmethod
    def _smooth_tangents(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "smooth_tangents")

    @classmethod
    def _even_tangents(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "even_tangents")

    @classmethod
    def _uneven_tangents(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "uneven_tangents")

    @classmethod
    def _can_delete(cls, object: dict):
        cv_dict = object.get("cv_dict", [])

        for basis_curves, ids in cv_dict.items():
            curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
            curve_vertex_counts = curve_vertex_counts_attr.Get()

            type_attr = basis_curves.GetTypeAttr()
            type = type_attr.Get()
            basis = basis_curves.GetBasisAttr().Get()

            # Only show for bezier curve for now until other curve is better supported
            if basis != UsdGeom.Tokens.bezier and type != UsdGeom.Tokens.linear:
                return False

            for id in ids:
                if type == UsdGeom.Tokens.cubic:
                    id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)
                    index = id - id_curve_offset
                    if index % 3 != 0:  # if not anchor cv, can't delete
                        return False

        return True

    @classmethod
    def _can_split(cls, object: dict):
        cv_dict = object.get("cv_dict", [])

        for basis_curves, ids in cv_dict.items():
            curve_vertex_counts_attr = basis_curves.GetCurveVertexCountsAttr()
            curve_vertex_counts = curve_vertex_counts_attr.Get()

            wrap_attr = basis_curves.GetWrapAttr()
            wrap = wrap_attr.Get()

            type_attr = basis_curves.GetTypeAttr()
            type = type_attr.Get()
            basis = basis_curves.GetBasisAttr().Get()

            if wrap == UsdGeom.Tokens.periodic:
                # What's the behavior of splitting a periodic curve? disable it for now
                return False

            for id in ids:
                id_curve_offset, curve_index = get_array_index_offset_and_curve_index(id, curve_vertex_counts)
                index = id - id_curve_offset
                if index == 0 or index == curve_vertex_counts[curve_index] - 1:
                    # cannot split at the beginning or end of a segment
                    return False

                if type == UsdGeom.Tokens.cubic and basis == UsdGeom.Tokens.bezier:
                    if index % 3 != 0:  # if not anchor cv, can't split
                        return False

        return True

    @classmethod
    def _bezier(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "bezier")

    @classmethod
    def _bezier_corner(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "bezier_corner")

    @classmethod
    def _corner(cls, object: dict):
        cls._do_curve_edit_on_all_prims(object, "corner")

    @classmethod
    def _delete_cvs(cls, object: dict):
        cv_dict = object.get("cv_dict", [])
        cls._get_bezier_curve_edits_context(object).delete_anchor_cvs(cv_dict)

    @classmethod
    def _split_at_cvs(cls, object: dict, new_basis_curves: bool):
        cv_dict = object.get("cv_dict", [])
        cls._get_bezier_curve_edits_context(object).split_at_anchor_cvs(cv_dict, new_basis_curves)

    @classmethod
    def _delete_and_split_at_cvs(cls, object: dict, new_basis_curves: bool):
        cv_dict = object.get("cv_dict", [])
        cls._get_bezier_curve_edits_context(object).delete_and_split_anchor_cvs(cv_dict, new_basis_curves)

    @classmethod
    def _open_close_curves(cls, object: dict):
        cv_dict = object.get("cv_dict", [])
        curves_prims_of_selected_cvs = set(cv_dict.keys())

        with omni.kit.undo.group():
            for basis_curves in curves_prims_of_selected_cvs:
                cls._get_bezier_curve_edits_context(object).open_close_curve(basis_curves)

    @staticmethod
    def _is_selected_all_curve(object: dict):
        prim_list = object.get("prim_list", [])
        if not prim_list:
            return False

        for prim in prim_list:
            if not prim.IsA(UsdGeom.BasisCurves):
                return False

        return True

    @classmethod
    def _can_enabled_cv_edit(cls, object: dict):
        if cls._curve_manip.is_in_curve_editing_mode(cls._get_curve_context(object)):
            return False

        return cls._is_selected_all_curve(object)

    @classmethod
    def _enable_cv_edit(cls, object: dict):
        prim_list = object.get("prim_list", [])
        prim_list_str = [prim.GetPath().pathString for prim in prim_list if prim.IsA(UsdGeom.BasisCurves)]
        if prim_list_str:
            omni.kit.commands.execute(
                "EnableCurveEditing",
                curve_context=cls._get_curve_context(object),
                paths=prim_list_str,
                mode=CurveEditingModeType.DRAG,
            )

    @classmethod
    def _register_stage_context_menu(cls):
        menu = {
            "name": "endsep/",
            "show_fn": lambda object: cls._curve_manip.is_in_curve_editing_mode(cls._get_curve_context(object))
            or cls._can_enabled_cv_edit(object),
        }
        cls._stage_menu_entry_handles.append(omni.kit.context_menu.add_menu(menu, "MENU", "omni.kit.widget.stage"))

        cls._stage_menu_entry_handles.append(cls._add_enable_cv_edit_menu_impl("omni.kit.widget.stage"))
        cls._stage_menu_entry_handles.append(cls._add_disable_cv_edit_menu_impl("omni.kit.widget.stage"))

    @classmethod
    def _unregister_stage_context_menu(cls):
        for handle in cls._stage_menu_entry_handles:
            handle.release()
        cls._stage_menu_entry_handles.clear()

    @classmethod
    def _get_curve_context(cls, object: dict) -> CurveManipulatorContext:
        usd_context_name = object.get("usd_context_name", "")
        return BezierCurveEditsContextManager.get_context(usd_context_name).curve_edits.curve_context

    @classmethod
    def _get_bezier_curve_edits_context(cls, object: dict):
        usd_context_name = object.get("usd_context_name", "")
        return BezierCurveEditsContextManager.get_context(usd_context_name).curve_edits

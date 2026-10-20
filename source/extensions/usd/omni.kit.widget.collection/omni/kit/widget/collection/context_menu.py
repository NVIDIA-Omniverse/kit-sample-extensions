# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from functools import partial
from typing import Callable, Dict, List, Tuple

import carb
import omni.kit.commands
import omni.kit.ui
import omni.usd
from omni import ui
from omni.kit.context_menu import ContextMenuExtension
from omni.kit.core.collection import usd
from pxr import Sdf, Usd, UsdGeom

from .model import BaseItem


class CustomExpansionRuleMenu(object):
    def __init__(self):
        super().__init__()
        self.menu_item_count = 0
        self.menu_item_prev = None

    def menu_item(self, name: str, triggered_fn: Callable = None, check_state: bool = False, enabled: bool = True):
        self.menu_item_prev = ContextMenuExtension.uiMenuItem(name, triggered_fn=triggered_fn, enabled=enabled)
        self.menu_item_prev.checkable = True
        self.menu_item_prev.checked = check_state
        self.menu_item_count += 1
        self._menu_cache.append(self.menu_item_prev)

    def set_expansion_rule(custom_menu, item: BaseItem, expansion_rule: str):
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=item.path.pathString, expansion_rule=expansion_rule
        )

    def build_menu(self, item):
        self._menu_cache = []
        currentState = usd.CollectionHelper(item.path.pathString).get_collection_api().GetExpansionRuleAttr().Get()
        menu = ContextMenuExtension.uiMenu(
            f' {omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_create.svg")}   Set ExpansionRule',
            style={"secondary_color": 0xFFFFFFFF},
        )
        self._menu_cache.append(menu)
        with menu:

            self.menu_item(
                f' {omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_scope.svg")}   explicitOnly',
                triggered_fn=partial(self.set_expansion_rule, item, "explicitOnly"),
                check_state=currentState == Usd.Tokens.explicitOnly,
            ),

            self.menu_item(
                f' {omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_scope.svg")}   expandPrims',
                triggered_fn=partial(self.set_expansion_rule, item, "expandPrims"),
                check_state=currentState == Usd.Tokens.expandPrims,
            ),

            self.menu_item(
                f' {omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_scope.svg")}   expandPrimsAndProperties',
                triggered_fn=partial(self.set_expansion_rule, item, "expandPrimsAndProperties"),
                check_state=currentState == Usd.Tokens.expandPrimsAndProperties,
            ),


class ActionsMenu(object):
    def __init__(self):
        super().__init__()
        self.menu_item_count = 0
        self.menu_item_prev = None

    def menu_item(self, name: str, triggered_fn: Callable = None, check_state: bool = False, enabled: bool = True):
        self.menu_item_prev = ContextMenuExtension.uiMenuItem(name, triggered_fn=triggered_fn, enabled=enabled)
        self.menu_item_prev.checkable = True
        self.menu_item_prev.checked = check_state
        self.menu_item_count += 1
        self._menu_cache.append(self.menu_item_prev)

    def click_set_primvar(self, primvar_name: str, collection_path: Sdf.Path):
        """
        assumption that all values are initially the same is a bit disingenous
        """
        helper = usd.CollectionHelper(collection_path)
        members = helper.get_all_members(prims_only=True)
        for prim in members:
            primvars_api = UsdGeom.PrimvarsAPI(prim)
            value = primvars_api.GetPrimvar(primvar_name)
            if value:
                value.Set(not value.Get())
            else:
                primvars_api.CreatePrimvar(primvar_name, Sdf.ValueTypeNames.Bool).Set(True)

    def build_menu(self, collection_path):
        self._menu_cache = []
        actions = [
            (
                "Toggle Wireframe Mode",
                partial(self.click_set_primvar, primvar_name="wireframe", collection_path=collection_path),
            ),
            (
                "Toggle Do Not Cast Shadows",
                partial(self.click_set_primvar, primvar_name="doNotCastShadows", collection_path=collection_path),
            ),
            (
                "Toggle Enable Shadow Terminator Fix",
                partial(
                    self.click_set_primvar, primvar_name="enableShadowTerminatorFix", collection_path=collection_path
                ),
            ),
            (
                "Toggle Matte Object",
                partial(self.click_set_primvar, primvar_name="isMatteObject", collection_path=collection_path),
            ),
            (
                "Toggle Hide From Camera",
                partial(self.click_set_primvar, primvar_name="hideForCamera", collection_path=collection_path),
            ),
            (
                "Toggle Is Light",
                partial(self.click_set_primvar, primvar_name="isLight", collection_path=collection_path),
            ),
        ]

        menu = ContextMenuExtension.uiMenu(
            f' {omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_create.svg")}  Rendering',
            style={"secondary_color": 0xFFFFFFFF},
        )
        self._menu_cache.append(menu)
        with menu:
            for action in actions:
                self.menu_item(
                    f' {omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_scope.svg")}  {action[0]}',
                    triggered_fn=action[1],
                )


class ContextMenu:
    def __init__(self):
        from omni.kit.widget.stage import ContextMenu as StageContextMenu

        self.stage_menu_items = StageContextMenu.add_create_menu(self.generate_create_for_stage_widget())

    @classmethod
    def generate_create_for_stage_widget(cls) -> Dict:
        context_menu = omni.kit.context_menu.get_instance()
        menu_item = {
            "name": "Collection",
            "glyph": "menu_duplicate.svg",
            "show_fn": [context_menu.is_prim_selected, context_menu.can_be_copied],
            "onclick_fn": ContextMenu.create_collection,
        }
        return menu_item

    @classmethod
    def material_features_supported(cls, event=None) -> bool:
        """
        material assignment for collections was introduced in omni.usd.
        Do we have a compatible version?
        """

        def resolve_version(available: Tuple, required: Tuple):
            """
            consider using https://github.com/python-semver/python-semver
            """
            if available[0] < required[0]:
                return False
            if available[0] > required[0]:
                return True
            if available[0] == required[0]:
                if available[1] < required[1]:
                    return False
                if available[1] > required[1]:
                    return True
                if available[1] == required[1]:
                    if available[2] < required[2]:
                        return False
                    if available[2] >= required[2]:
                        return True
            return False

        manager = omni.kit.app.get_app().get_extension_manager()
        kit_build_str = omni.kit.app.get_app().get_build_version()
        kit_parts = kit_build_str.split("+")
        version_parts = kit_parts[0].split(".")
        kit_version_major = int(version_parts[0])

        omni_usd_extension_path = manager.get_enabled_extension_id("omni.usd")
        omni_usd_current_version = omni_usd_extension_path.split("-")[1]
        parts = omni_usd_current_version.split(".")
        omni_usd_version_tuple = [int(parts[0]), int(parts[1]), int(parts[2])]

        if kit_version_major >= 101 and kit_version_major < 102 and resolve_version(omni_usd_version_tuple, (1, 3, 1)):
            return True
        elif kit_version_major >= 102 and resolve_version(omni_usd_version_tuple, (1, 4, 1)):
            return True
        return False

    @classmethod
    def _generate_menu(cls) -> List:
        # setup menu
        context_menu = omni.kit.context_menu.get_instance()
        menu_list = [
            # Prim
            {"populate_fn": ContextMenu.show_expandrules_menu, "show_fn": [ContextMenu.is_collection_selected]},
            {"name": ""},
            {
                "name": "Create Collection",
                "glyph": "menu_duplicate.svg",
                "show_fn": [
                    context_menu.is_prim_selected,
                    ContextMenu.is_not_under_collection,
                    context_menu.can_be_copied,
                ],
                "onclick_fn": ContextMenu.create_collection,
            },
            # Collection
            {
                "name": "Duplicate",
                "glyph": "menu_duplicate.svg",
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.duplicate_collection,
            },
            {
                "name": "Rename",
                "glyph": "menu_rename.svg",
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.menu_rename_collection_dialog,
            },
            {
                "name": "Delete",
                "glyph": "menu_delete.svg",
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.delete_collection,
            },
            {
                "name": "Clear",
                "glyph": "menu_delete.svg",  # TODO
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.clear_collection,
            },
            {
                "name": "Block",
                "glyph": "menu_delete.svg",  # TODO
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.block_collection,
            },
            {
                "name": "Assign Material",
                "glyph": "menu_material.svg",
                "show_fn": [
                    ContextMenu.is_collection_selected,
                    # context_menu.is_material_count, # are there any materials in the scene?
                    partial(ContextMenu.material_features_supported),
                ],
                "onclick_fn": ContextMenu.bind_material_to_prim_dialog,
            },
            {
                "name": "Select Contents",
                "glyph": "menu_delete.svg",  # TODO
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.select_collection_contents,
            },
            {
                "name": "Toggle Visibility",
                "glyph": "menu_delete.svg",  # TODO
                "show_fn": [ContextMenu.is_collection_selected],
                "onclick_fn": ContextMenu.toggle_visibility,
            },
            {"populate_fn": ContextMenu.show_actions_menu, "show_fn": [ContextMenu.is_collection_selected]},
            # Collection Content (Prim or Property)
            {"name": ""},
            {
                "name": "Remove from Collection",
                "glyph": "menu_link.svg",
                "show_fn": ContextMenu.is_under_collection_and_is_directly_included,
                "onclick_fn": ContextMenu.remove_from_collection,
            },
            {"name": ""},
            {
                "name": "Exclude from Collection",
                "glyph": "menu_link.svg",
                "show_fn": ContextMenu.is_under_collection_and_is_indirectly_included,
                "onclick_fn": ContextMenu.exclude_from_collection,
            },
            # Common
            {"name": ""},
            {"name": "Copy Path", "glyph": "menu_link.svg", "onclick_fn": ContextMenu.copy_path},
        ]
        # get any existing items
        menu_list += omni.kit.context_menu.get_menu_dict("omni.kit.widget.collection", "")
        return menu_list

    def on_mouse_event(self, event):

        # check its expected event
        if event.type != int(omni.kit.ui.MenuEventType.ACTIVATE):
            return

        # get context menu core functionality & check its enabled
        context_menu = omni.kit.context_menu.get_instance()
        if context_menu is None:
            carb.log_error("context_menu is disabled!")
            return

        # get stage
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_error("stage not avaliable")
            return None

        # get parameters passed by event
        prim_path = event.payload["prim_path"]

        # setup objects, this is passed to all functions
        objects = {}
        objects["stage_win"] = self._stage_win
        objects["node_open"] = event.payload["node_open"]
        objects["stage"] = stage
        objects["model_item"] = event.item

        prim_list = []
        # TODO: Work out what this hover stuff is for..
        hovered_prim = None
        paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if len(paths) > 0:
            hovered_prim = event.payload["prim_path"]
            for path in paths:
                prim = stage.GetPrimAtPath(path)
                if prim:
                    prim_list.append(prim)
                    if prim == hovered_prim:
                        hovered_prim = None

        elif prim_path is not None:
            prim = stage.GetPrimAtPath(prim_path)
            if prim:
                prim_list.append(prim)

        if prim_list:
            objects["prim_list"] = prim_list
        if hovered_prim:
            objects["hovered_prim"] = stage.GetPrimAtPath(hovered_prim)

        menu_list = self._generate_menu()
        context_menu.show_context_menu("omni.kit.widget.collection", objects, menu_list)

    def is_under_collection(objects):
        item = objects["model_item"]
        return hasattr(item, "owning_collection")

    def is_under_collection_and_is_directly_included(objects):
        item = objects["model_item"]
        bb = (
            item.item_type in ["CollectionPrimContentItem", "CollectionPrimPropertyContentItem"]
            and item.is_explicit_collection_item()
        )
        return bb

    def is_under_collection_and_is_indirectly_included(objects):
        item = objects["model_item"]
        bb = (
            item.item_type in ["CollectionPrimContentItem", "CollectionPrimPropertyContentItem"]
            and item.is_explicit_collection_item() == False
        )
        return bb

    def is_not_under_collection(objects):
        item = objects["model_item"]
        return item.item_type not in ["Collection", "CollectionPrimContentItem", "CollectionPrimPropertyContentItem"]

    def is_collection_selected(objects):
        item = objects["model_item"]
        if item:
            return item.path.pathString.find(".collection:") != -1
        return False

    def delete_collection(objects):
        item = objects["model_item"]
        if item:
            omni.kit.commands.execute("DeleteCollection", collection_path=item.path.pathString)

    def duplicate_collection(objects):
        item = objects["model_item"]
        if item:
            omni.kit.commands.execute("DuplicateCollection", collection_path=item.path.pathString)

    def clear_collection(objects):
        item = objects["model_item"]
        if item:
            omni.kit.commands.execute("ClearCollection", collection_path=item.path.pathString)

    def remove_from_collection(objects):
        item = objects["model_item"]
        collection_path = item.owning_collection.GetCollectionPath().pathString
        for prim in objects["prim_list"]:
            omni.kit.commands.execute(
                "RemoveItemFromCollection", prim_or_prop_path=prim.GetPath().pathString, collection_path=collection_path
            )

    def exclude_from_collection(objects):
        item = objects["model_item"]
        collection_path = item.owning_collection.GetCollectionPath().pathString
        omni.kit.commands.execute(
            "ExcludeItemFromCollection", prim_or_prop_path=item.path.pathString, collection_path=collection_path
        )

    def create_collection(objects):
        prim_list = objects["prim_list"]
        for p in prim_list:
            omni.kit.commands.execute("CreateCollection", prim_path=p.GetPath().pathString)

    def block_collection(objects):
        item = objects["model_item"]
        if item:
            omni.kit.commands.execute("BlockCollection", collection_path=item.path.pathString)

    def select_collection_contents(objects):
        item = objects["model_item"]
        if item:
            omni.kit.commands.execute("SelectPrimsInCollection", collection_path=item.path.pathString)

    def toggle_visibility(objects):
        collection_path = objects["model_item"].path
        collection_helper = usd.CollectionHelper(collection_path)

        prims = collection_helper.get_all_members(prims_only=True)
        imageable_prims = [prim for prim in prims if prim.IsA(UsdGeom.Imageable)]
        paths = [prim.GetPath() for prim in imageable_prims]

        # Get the first Selected Imageable prim visibility to remain consistent with property window
        stage = omni.usd.get_context().get_stage()
        for target in stage.GetPropertyAtPath(f"{collection_path}:includes").GetTargets():
            if not target.isPropertyPath() and (target_prim := stage.GetPrimAtPath(target)).IsA(UsdGeom.Imageable):
                visibility = (
                    UsdGeom.Imageable(target_prim).ComputeVisibility(Usd.TimeCode.Default()) == UsdGeom.Tokens.inherited
                )
                # Set the collection visibility to the inverse of the current visibility state
                omni.kit.commands.execute("SetCollectionVisibility", selected_paths=paths, visible=not visibility)
                return

        carb.log_warn("Unable to toggle visibility. No valid UsdGeom.Imageable found in collection.")

    def menu_rename_collection_dialog(objects):
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_error("stage not avaliable")
            return None

        ContextMenu.rename_collection_dialog(objects)

    def bind_material_to_prim_dialog(objects):
        class PrimLikeInterface(object):
            def __init__(self, item, stage):
                super().__init__()
                self.item = item
                self.stage = stage

            def GetPath(self):
                return self.item.path

            def GetPrim(self):
                prim_path = self.GetPath().GetPrimPath()
                return self.stage.GetPrimAtPath(prim_path)

        item = objects["model_item"]
        if item:
            omni.kit.context_menu.get_instance().bind_material_to_prims_dialog(
                objects["stage"], [PrimLikeInterface(item, objects["stage"])]
            )

    def copy_path(objects):
        item = objects["model_item"]
        path = item.path.pathString

        try:
            import pyperclip

            pyperclip.copy(path)
        except ImportError:
            carb.log_warn("Could not import pyperclip.")

    def show_expandrules_menu(objects):
        item = objects["model_item"]
        CustomExpansionRuleMenu().build_menu(item)

    def show_actions_menu(objects):
        item = objects["model_item"]
        ActionsMenu().build_menu(item.path.pathString)

    # ---------------------------------------------- menu onClick functions ----------------------------------------------

    def rename_collection(stage, helper, window, field_widget):
        if window:
            window.visible = False

        if field_widget:
            old_collection_name = helper.get_collection_name()
            if helper.get_collection_name() != field_widget.model.get_value_as_string():
                old_prim_name = old_collection_name
                new_prim_name = field_widget.model.get_value_as_string()

                if Sdf.Path.IsValidPathString(new_prim_name):
                    omni.kit.commands.execute(
                        "RenameCollection",
                        old_collection_path=helper.get_full_path().pathString,
                        new_collection_name=new_prim_name,
                    )
                else:
                    carb.log_error(f"Cannot rename {old_prim_name} to {new_prim_name} as its not a valid USD path")

    def rename_collection_dialog(objects):
        item = objects["model_item"]
        helper = usd.CollectionHelper(item.path.pathString)
        window = ui.Window(
            "Rename " + helper.get_collection_name() + "###context_menu_rename",
            width=200,
            height=0,
            flags=ui.WINDOW_FLAGS_NO_RESIZE | ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_MODAL,
        )
        with window.frame:
            with ui.VStack(
                height=0,
                spacing=5,
                name="top_level_stack",
                style={"VStack::top_level_stack": {"margin": 5}, "Button": {"margin": 0}},
            ):
                new_name_widget = ui.StringField()
                new_name_widget.model.set_value(helper.get_collection_name())
                new_name_widget.focus_keyboard()

                ui.Spacer(width=5, height=5)
                with ui.HStack(spacing=5):
                    ui.Button(
                        "Ok",
                        identifier="Button_Ok",
                        clicked_fn=partial(
                            ContextMenu.rename_collection, objects["stage"], helper, window, new_name_widget
                        ),
                    )
                    ui.Button(
                        "Cancel",
                        identifier="Button_Cancel",
                        clicked_fn=partial(ContextMenu.rename_collection, objects["stage"], helper, window, None),
                    )

                    editing_started = False

                    def on_begin():
                        nonlocal editing_started
                        editing_started = True

                    def on_end():
                        nonlocal editing_started
                        editing_started = False

                    def widget_pressed_key(key_index, key_mod, key_down):
                        nonlocal editing_started
                        if key_index == 51 and key_mod == 0 and key_down and editing_started:
                            on_end()
                            ContextMenu.rename_collection(objects["stage"], helper, window, new_name_widget)

                    new_name_widget.set_key_pressed_fn(widget_pressed_key)
                    new_name_widget.model.add_begin_edit_fn(lambda m: on_begin())
                    new_name_widget.model.add_end_edit_fn(lambda m: on_end())

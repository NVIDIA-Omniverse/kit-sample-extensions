# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Any, Dict, List, Optional

import omni.kit.commands
import omni.kit.undo
import omni.kit.viewport.utility
import omni.usd
from omni.usd.commands import DeletePrimsCommand, UsdStageHelper
from pxr import Sdf, Usd

from ..prims import PRIM_NS, valid_ui_prim_categories, valid_ui_prim_types
from ..prims.prim_properties import create_prim_properties


def getStageDefaultPrimPath(stage):
    if stage.HasDefaultPrim():
        return stage.GetDefaultPrim().GetPath()
    else:
        return Sdf.Path.absoluteRootPath


class CreateUIFrame(omni.kit.commands.Command, UsdStageHelper):
    _selection: omni.usd.Selection
    _previously_selected_paths: list[str] | None

    def __init__(
        self,
        prim_path: Optional[str] = None,
        select_new_prim: bool = True,
        attributes: Dict[str, Any] = {},
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
        target: str = "window",
    ):
        UsdStageHelper.__init__(self, stage, context_name)
        self._prim_path = prim_path
        self._prim_type = "Frame"
        self._attributes = attributes if attributes else {}
        self._selection = self._get_context().get_selection()
        self._select_new_prim = select_new_prim
        self._previously_selected_paths = None
        self._target = target
        self._frame_prim = None
        self._model = None
        self._delegate = None
        self._window = None
        self._view = None

    def do(self):
        from ..extension import _extension_instance

        stage = self._get_stage()

        self._previously_selected_paths = self._selection.get_selected_prim_paths()
        self._selection.clear_selected_prim_paths()

        if not self._prim_path:
            if len(self._previously_selected_paths) == 1:
                self._prim_path = f"{self._previously_selected_paths[0]}/{self._prim_type}"
            else:
                self._prim_path = getStageDefaultPrimPath(stage).AppendChild(self._prim_type)

        self._prim_path = Sdf.Path(omni.usd.get_stage_next_free_path(stage, self._prim_path, False))

        with omni.kit.undo.group():
            prim_command_result = omni.kit.commands.execute(
                "CreateUIPrimCommand",
                prim_type="Frame",
                prim_path=self._prim_path,
                attributes=self._attributes,
                select_new_prim=self._select_new_prim,
                stage=stage,
            )
            if prim_command_result[0]:
                self._frame_prim = prim_command_result[1]
            else:
                self._frame_prim = omni.usd.get_prim_at_path(self._prim_path, stage)

            _extension_instance._execute_view(self._frame_prim, self._target)
            return self._frame_prim

    def undo(self):
        self._view = None
        self._window = None
        self._delegate = None
        self._model = None
        self._frame_prim = None

        # Restore selection
        if self._previously_selected_paths is not None:
            self._selection.set_selected_prim_paths(self._previously_selected_paths, False)


class CreateViewportUIFrame(CreateUIFrame, UsdStageHelper):
    def __init__(
        self,
        prim_path: Optional[str] = None,
        select_new_prim: bool = True,
        attributes: Dict[str, Any] = {},
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
    ):
        CreateUIFrame.__init__(self, prim_path, select_new_prim, attributes, stage, context_name, "viewport")


class CreateWindowUIFrame(CreateUIFrame, UsdStageHelper):
    def __init__(
        self,
        prim_path: Optional[str] = None,
        select_new_prim: bool = True,
        attributes: Dict[str, Any] = {},
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
    ):
        CreateUIFrame.__init__(self, prim_path, select_new_prim, attributes, stage, context_name, "window")


class CreateUIPrimCommand(omni.kit.commands.Command, UsdStageHelper):
    def __init__(
        self,
        prim_type: str,
        prim_path: Optional[str] = None,
        select_new_prim: bool = True,
        attributes: Dict[str, Any] = {},
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
    ):
        UsdStageHelper.__init__(self, stage, context_name)
        self._prim = None
        self._prim_type = prim_type
        self._prim_path = prim_path
        self._attributes = attributes if attributes else {}
        self._selection = self._get_context().get_selection()
        self._select_new_prim = select_new_prim
        self._previously_selected_paths = None
        self._created_scopes: List[str] = list()

    def do(self):
        if self._prim_type not in valid_ui_prim_types:
            raise Exception(f"prim_type {self._prim_type} not supported UI Prim type")

        stage = self._get_stage()
        if not stage:
            raise Exception("Stage does not exist.")

        self._previously_selected_paths = self._selection.get_selected_prim_paths()
        self._selection.clear_selected_prim_paths()

        if not self._prim_path:
            if self._prim_type in valid_ui_prim_categories.get("Style", []):
                scope_name = "Styles"
            elif self._prim_type in ["ViewportButton", "ViewportCircle"]:
                scope_name = "Viewport"
            else:
                scope_name = "UI"
            # We don't want to worry about selections of other random primitives, just UIPrims.
            if len(self._previously_selected_paths) == 1 and scope_name in self._previously_selected_paths[0]:
                # TODO: When prim creation driven by model, be prepared to update creation targeting logic
                # if the selection is a container, create prim as a child
                # if the selection is a widget, create prim as a sibling
                selected_prim_path = Sdf.Path(self._previously_selected_paths[0])
                selected_prim_type_name = stage.GetPrimAtPath(selected_prim_path).GetTypeName()
                if selected_prim_type_name.startswith(PRIM_NS):
                    selected_prim_type = selected_prim_type_name.split(PRIM_NS)[1]
                    nesters = []
                    sibling_makers = []
                    if self._prim_type == "Style":
                        nesters = ["StyleContainer"]
                        sibling_makers = ["Style"]
                    elif self._prim_type == "StyleContainer":
                        pass
                    else:
                        nesters = valid_ui_prim_categories.get("Containers", [])
                        sibling_makers = valid_ui_prim_categories.get("Widgets", [])
                    if selected_prim_type in nesters:
                        self._prim_path = f"{self._previously_selected_paths[0]}/{self._prim_type}"
                    elif selected_prim_type in sibling_makers:
                        parent_prim_path = selected_prim_path.GetParentPath()
                        self._prim_path = f"{parent_prim_path}/{self._prim_type}"

            if not self._prim_path:
                self._prim_path = getStageDefaultPrimPath(stage).AppendChild(scope_name).AppendChild(self._prim_type)

        self._prim_path = Sdf.Path(omni.usd.get_stage_next_free_path(stage, self._prim_path, False))

        with omni.kit.undo.group():
            parent_path = self._prim_path.GetParentPath()
            create_scopes = []
            self._created_scopes
            while parent_path != getStageDefaultPrimPath(stage) and parent_path != "/":
                create_scopes.append(parent_path)
                parent_path = parent_path.GetParentPath()
            for scope in create_scopes:
                if not stage.GetPrimAtPath(scope):
                    stage.DefinePrim(scope, "Scope")
                    self._created_scopes.append(scope)

            self._prim = stage.DefinePrim(self._prim_path, f"{PRIM_NS}{self._prim_type}")

            # Schema not used for anything currently
            self._prim.AddAppliedSchema(f"OMNIUIAPI")
            self._prim_path = self._prim.GetPath().pathString
            if self._select_new_prim:
                self._selection.set_prim_path_selected(self._prim_path, True, True, True, True)
            with Sdf.ChangeBlock():
                for attr in self._attributes:
                    self._prim.GetProperty(attr).Set(self._attributes[attr])
                create_prim_properties(self._prim_type, self._prim)

            return self._prim

    def undo(self):
        delete_cmd = DeletePrimsCommand([self._prim_path])
        delete_cmd.do()
        if self._created_scopes:
            delete_cmd = DeletePrimsCommand(self._created_scopes)
            delete_cmd.do()

        # Restore selection
        if self._previously_selected_paths is not None:
            self._selection.set_selected_prim_paths(self._previously_selected_paths, False)


class ParentToViewportCommand(omni.kit.commands.Command, UsdStageHelper):
    def __init__(self, prim_path: str = "", stage: Usd.Stage | None = None, context_name: str = ""):
        UsdStageHelper.__init__(self, stage, context_name)
        self._prim_path = prim_path
        self._selection: omni.usd.Selection = self._get_context().get_selection()  # type: ignore

    def do(self):
        from ..extension import _extension_instance

        selected_prim: Usd.Prim
        if stage := self._get_stage():
            if not self._prim_path:
                selected_paths = self._selection.get_selected_prim_paths()
                if len(selected_paths) != 1:
                    raise Exception(f"Can only parent a single element to the viewport.")
                self._prim_path = selected_paths[0]
            if selected_prim := stage.GetPrimAtPath(Sdf.Path(self._prim_path)):  # type: ignore
                prim_type: str = selected_prim.GetTypeName()  # type: ignore
                if not prim_type.startswith(PRIM_NS):
                    raise Exception("Can only parent UI Primitives to viewport")
                if "Frame" not in prim_type:
                    raise Exception("Can only parent Frame Primitives to viewport")
                _extension_instance._execute_view(selected_prim, "viewport")

    def undo(self):
        from ..extension import _extension_instance

        if (stage := self._get_stage()) and (prim := stage.GetPrimAtPath(self._prim_path)):
            _extension_instance._execute_view(prim, "remove viewport")


class RemoveViewportPrim(omni.kit.commands.Command, UsdStageHelper):
    def __init__(self):
        UsdStageHelper.__init__(self, None, None)

    def do(self):
        if avw := omni.kit.viewport.utility.get_active_viewport_window(window_name="Viewport"):
            if frame := avw.get_frame("Data Driven Viewport Frame"):
                frame.destroy()


class ReorderUIPrimsCommand(omni.kit.commands.Command, UsdStageHelper):
    def __init__(
        self,
        direction: str,
        prim_paths: Optional[List[str]] = None,
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
    ):
        UsdStageHelper.__init__(self, stage, context_name)
        self._prim = None
        self._direction = direction
        self._prim_paths = prim_paths
        self._selection = self._get_context().get_selection()

    def do(self):
        stage = self._get_stage()
        if not stage:
            return

        self._previous_prim_parents = {}

        if not self._prim_paths:
            self._prim_paths = self._selection.get_selected_prim_paths()

        self._prim_parent_sources = {}
        self._prim_parent_new = {}

        for prim_path in self._prim_paths:
            prim_path = Sdf.Path(prim_path)
            parent_prim_path = prim_path.GetParentPath()
            parent_prim = stage.GetPrimAtPath(parent_prim_path)
            if parent_prim not in self._prim_parent_sources:
                self._prim_parent_sources[parent_prim_path] = {}
                self._prim_parent_new[parent_prim_path] = {}
            children = parent_prim.GetChildren()
            for i, child in enumerate(children):
                child_path = child.GetPath()
                self._prim_parent_sources[parent_prim_path][i] = child_path
                self._prim_parent_new[parent_prim_path][i] = child_path

        for parent in self._prim_parent_new:
            children = self._prim_parent_new.get(parent, {})

            if self._direction == "Down":  # invert eval order for Down to ensure flow
                children_items = reversed(children.items())
            else:
                children_items = children.items()

            for i, child in children_items:
                if child in self._prim_paths:
                    if self._direction == "Up":
                        new_index = i - 1
                    elif self._direction == "Down":
                        new_index = i + 1
                    else:
                        continue
                    if children.get(new_index):
                        temp = children[new_index]
                        if temp not in self._prim_paths:
                            children[new_index] = child
                            children[i] = temp

        with omni.kit.undo.group():
            for parent in self._prim_parent_new:
                parent_prim = stage.GetPrimAtPath(parent)
                children = self._prim_parent_new.get(parent, {})
                ordered_children = sorted(children.items())

                for i, child in ordered_children:
                    path_from = child
                    path_to = Sdf.Path(str(path_from) + "_reorder_tmp")
                    omni.kit.commands.execute(
                        "MovePrim", path_from=str(path_from), path_to=str(path_to), destructive=False
                    )
                    omni.kit.commands.execute(
                        "MovePrim", path_from=str(path_to), path_to=str(path_from), destructive=False
                    )

    def undo(self):
        pass


def register_commands():
    omni.kit.commands.register(CreateWindowUIFrame)
    omni.kit.commands.register(CreateViewportUIFrame)
    omni.kit.commands.register(CreateUIPrimCommand)
    omni.kit.commands.register(ReorderUIPrimsCommand)
    omni.kit.commands.register(ParentToViewportCommand)
    omni.kit.commands.register(RemoveViewportPrim)


def deregister_commands():
    omni.kit.commands.unregister(ReorderUIPrimsCommand)
    omni.kit.commands.unregister(CreateUIPrimCommand)
    omni.kit.commands.unregister(CreateViewportUIFrame)
    omni.kit.commands.unregister(CreateWindowUIFrame)
    omni.kit.commands.unregister(ParentToViewportCommand)
    omni.kit.commands.unregister(RemoveViewportPrim)

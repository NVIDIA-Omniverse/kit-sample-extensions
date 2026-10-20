# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import functools
from collections.abc import Callable
from typing import Any, List, Optional

import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.ui as ui
import omni.usd
from omni.kit.widget.stage import UsdStageHelper
from pxr import Sdf, Usd

HEADER_DICT = {0: "Variant Set", 1: "Variant"}


class AllowedTokenItem(ui.AbstractItem):
    def __init__(self, name):
        super().__init__()
        self.model = ui.SimpleStringModel(name)


class VariantComboboxModel(ui.AbstractItemModel, UsdStageHelper):
    def __init__(self, stage: Usd.Stage, prim_path: Sdf.Path, variant_set_name: str):
        super(VariantComboboxModel, self).__init__()
        UsdStageHelper.__init__(self, stage)

        self._prim_path = prim_path

        self._variant_set_name = variant_set_name
        self._variant_names = []

        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(self._current_index_changed)

        self._popup = None
        self._block_open_popup_dialog = False

        self._has_index = False
        self._update_value()
        self._has_index = True

    def _block_open_popup_dialog_dec(fn: Callable) -> Any:
        """Decorator to block the opening of the popup window"""

        def wrapper(self, *args, **kwargs):
            self._block_open_popup_dialog = True
            fn(self, *args, **kwargs)
            self._block_open_popup_dialog = False

        return wrapper

    def get_item_children(self, item: AllowedTokenItem) -> List[str]:
        self._update_value()
        return self._variant_names

    def get_item_value_model(self, item: AllowedTokenItem, column_id: int):
        if item is None:
            return self._current_index

        return item.model

    def set_value(self, value: str):
        if value == self._read_value():
            return

        stage = self._get_stage()
        current_selection = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if current_selection:
            if self._block_open_popup_dialog:
                return
            if len(current_selection) == 1 and current_selection[0] == self._prim_path:
                self.__set_values([self._prim_path], value)
                return

            paths_with_vset = []
            for path in current_selection:
                prim = stage.GetPrimAtPath(path)
                if prim.IsValid():
                    vsets = prim.GetVariantSets()
                    if not vsets.HasVariantSet(self._variant_set_name):
                        continue
                    vset = vsets.GetVariantSet(self._variant_set_name)
                    if not vset.HasAuthoredVariant(value):
                        continue
                    paths_with_vset.append(path)
            paths_with_vset.insert(0, self._prim_path)
            if len(paths_with_vset) > 1:
                self._open_popup_dialog(
                    "There is a selection.\n" "Do you want to apply the variant change to your selection?",
                    functools.partial(self._close_popup_dialog_variant_value_changed, paths_with_vset, value),
                )
                return
        self.__set_values([self._prim_path], value)

    @_block_open_popup_dialog_dec
    def _close_popup_dialog_variant_value_changed(self, paths: List[str], value: str, apply_on_selection: bool):
        """Called after the user close the dialog that asks if the user wants
        to set the change on the selection"""
        if self._popup:
            self._popup.visible = False
        if apply_on_selection:
            self.__set_values(paths, value)
        else:
            self.__set_values([self._prim_path], value)

    def __set_values(self, paths: List[str], value: str):
        with omni.kit.undo.group():
            for path in paths:
                omni.kit.commands.execute(
                    "SelectVariantPrimCommand", prim_path=path, vset_name=self._variant_set_name, var_name=value
                )

    def _open_popup_dialog(self, message: str, fn: Callable):
        """Open a popup dialog

        Args:
            message: message to show
            fn: function to execute when buttons are clicked. Depending of the mode,
                different args are given
        """
        flags = ui.WINDOW_FLAGS_NO_RESIZE
        flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        flags |= ui.WINDOW_FLAGS_MODAL
        self._popup = ui.Window("Warning", width=400, height=130, flags=flags)
        with self._popup.frame:
            with ui.VStack(name="root", style={"VStack::root": {"margin": 10}}, height=0, spacing=20):
                ui.Label(message, alignment=ui.Alignment.CENTER)
                with ui.HStack():
                    ui.Spacer()
                    ui.Button("Yes", width=100, height=25, clicked_fn=functools.partial(fn, True))
                    ui.Button("No", width=100, height=25, clicked_fn=functools.partial(fn, False))
                    ui.Spacer()
        self._popup.visible = True

    def _current_index_changed(self, model: ui.SimpleIntModel) -> None:
        if not self._has_index:
            return

        index = model.as_int
        if self.set_value(self._variant_names[index].model.get_value_as_string()):
            self._item_changed(None)

    def _update_variant_names(self) -> None:
        self._variant_names = []

        vset = self._get_variant_set()
        if vset:
            vnames = vset.GetVariantNames()

            self._variant_names.append(AllowedTokenItem(""))  # Empty variant
            for name in vnames:
                self._variant_names.append(AllowedTokenItem(name))

    def _update_value(self) -> None:
        self._update_variant_names()

        index = -1
        for i in range(0, len(self._variant_names)):
            if self._variant_names[i].model.get_value_as_string() == self._read_value():
                index = i
                break

        if index != -1 and self._current_index.as_int != index:
            self._current_index.set_value(index)
            self._item_changed(None)

    def _read_value(self) -> str:
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        vsets = prim.GetVariantSets()
        vset = vsets.GetVariantSet(self._variant_set_name)
        return vset.GetVariantSelection()

    def _get_variant_set(self) -> Optional[Usd.VariantSet]:
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if prim.IsValid():
            vsets = prim.GetVariantSets()
            return vsets.GetVariantSet(self._variant_set_name)
        return None

    def destroy(self):
        self._popup = None


class VariantSetModelItem(ui.AbstractItem):
    """Variant set item of the list model"""

    def __init__(self, stage: Usd.Stage, variant_set: Usd.VariantSet, path: Sdf.Path):
        """
        Init

        Args:
            stage: the current stage
            variant_set: the variant set of the prim
            path: the usd prim path
        """
        super(VariantSetModelItem, self).__init__()
        self.__stage = stage
        self.__path = path
        self.__variant_model = None
        self.variant_set_name = variant_set.GetName()

    @property
    def path(self) -> Sdf.Path:
        return self.__path

    def get_variant_model(self) -> VariantComboboxModel:
        if self.__variant_model is None:
            self.__variant_model = VariantComboboxModel(self.__stage, self.__path, self.variant_set_name)
        return self.__variant_model

    def destroy(self):
        if self.__variant_model is not None:
            self.__variant_model.destroy()
            self.__variant_model = None

    def __repr__(self):
        return f'"{self.variant_set_name}"'


class VariantSetTreeModel(ui.AbstractItemModel):
    """List variant set model"""

    def __init__(self, stage: Usd.Stage, path: Sdf.Path):
        super(VariantSetTreeModel, self).__init__()

        if stage:
            self._prim = stage.GetObjectAtPath(path)
            self.variant_sets = self._prim.GetVariantSets()
            self.items = [
                VariantSetModelItem(
                    stage,
                    self.variant_sets.GetVariantSet(variant_set_name),
                    path,
                    # self.set_variants,
                )
                for variant_set_name in self.variant_sets.GetNames()
            ]
        else:
            self._prim = None

    def on_selection_changed(self):
        """Reset the model"""
        for item in self.items:
            self._item_changed(item)

    def get_item_children(self, item: VariantSetModelItem) -> list:
        """Returns all the children when the widget asks it."""
        if item is not None:
            return []

        return [child_item for child_item in self.items]

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return len(HEADER_DICT.keys())

    def get_item_value_model(self, item, column_id):
        """
        Return value model.
        It's the object that tracks the specific value.
        In our case we use ui.SimpleStringModel.
        """
        return item.variant_set_name

    def destroy(self):
        for item in self.items:
            item.destroy()
        self.items = []

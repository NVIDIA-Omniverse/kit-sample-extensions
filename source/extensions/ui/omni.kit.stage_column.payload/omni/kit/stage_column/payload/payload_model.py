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

import omni.client
import omni.kit.app
import omni.kit.commands
import omni.ui as ui
import omni.usd
from omni.kit.widget.stage import UsdStageHelper
from pxr import Sdf, Usd


class UsdPrimPayloadModel(ui.AbstractValueModel, UsdStageHelper):
    """
    A helper model of UsdStageWatch that behaves like a model that watches
    a USD stage. It doesn't work properly if UsdStageWatch does not
    create it.
    """

    def __init__(self, stage: Usd.Stage, path: Sdf.Path):
        """
        ## Arguments:
            `stage`: USD Stage
            `path`: The full path to the watched property
        """
        ui.AbstractValueModel.__init__(self)
        UsdStageHelper.__init__(self, stage)

        if stage:
            self._prim = stage.GetObjectAtPath(path)
        else:
            self._prim = None

        if self._prim:
            self._path = path
        else:
            self._path = None

        self._popup = None
        self._block_open_popup_dialog = False

    def _block_open_popup_dialog_dec(fn: Callable) -> Any:
        """Decorator to block the opening of the popup window"""

        def wrapper(self, *args, **kwargs):
            self._block_open_popup_dialog = True
            fn(self, *args, **kwargs)
            self._block_open_popup_dialog = False

        return wrapper

    def destroy(self):
        """Called before destroying"""
        pass

    def _get_prim(self) -> Optional[object]:
        """Utility function to get the prim for the payload."""
        if self._prim is None:
            return None
        prim = self._prim
        if not prim.IsValid() and self._path:
            # the prim itself might have expired, try to acquire the prim again if we have a prim path
            prim = self._get_stage().GetObjectAtPath(self._path)
        return prim

    def _get_load_value(self):
        self._prim = self._get_prim()
        if self._prim is None:
            return False
        return self._prim.IsLoaded()

    def on_usd_changed(self):
        """Called by the stage model when the visibility is changed"""
        self._value_changed()

    def get_value_as_bool(self) -> Optional[bool]:
        """Reimplemented get bool"""
        value = self._get_load_value()
        if not value:
            return
        return value

    def get_value_as_float(self) -> Optional[float]:
        """Reimplemented get bool"""
        value = self._get_load_value()
        if not value:
            return
        return float(value)

    def get_value_as_int(self) -> Optional[int]:
        """Reimplemented get bool"""
        value = self._get_load_value()
        if not value:
            return
        return int(value)

    def get_value_as_string(self) -> Optional[str]:
        """Reimplemented get bool"""
        value = self._get_load_value()
        if not value:
            return
        return str(value)

    @property
    def valid_payload(self) -> bool:
        self._prim = self._get_prim()
        if self._prim is None:
            return False
        ref_and_layers = omni.usd.get_composed_payloads_from_prim(self._prim, False)

        if len(ref_and_layers) == 0:
            return False

        for ref, layer in ref_and_layers:
            if ref.assetPath:
                status, _ = omni.client.stat(layer.ComputeAbsolutePath(ref.assetPath))
                if status != omni.client.Result.OK:
                    return False

        return True

    def set_value(self, value: Any):
        """Reimplemented set bool"""
        if not self._path:
            return

        stage = self._get_stage()
        loadable = [sdf_path.pathString for sdf_path in stage.FindLoadable()]
        current_selection = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if current_selection:
            if self._block_open_popup_dialog:
                return
            if len(current_selection) == 1 and current_selection[0] == self._path:
                self.__set_values([self._path], value)
                return
            if len(current_selection) == 1 and current_selection[0] not in loadable:
                self.__set_values([self._path], value)
                return

            paths_with_payload = [path for path in current_selection if path in loadable]
            paths_with_payload.insert(0, self._path)
            if len(paths_with_payload) > 1:
                self._open_popup_dialog(
                    "There is a selection.\n" "Do you want to apply the payload change to your selection?",
                    functools.partial(self._close_popup_dialog_payload_value_changed, paths_with_payload, value),
                )
                return
        self.__set_values([self._path], value)

    @_block_open_popup_dialog_dec
    def _close_popup_dialog_payload_value_changed(self, paths: List[str], value: bool, apply_on_selection: bool):
        """Called after the user close the dialog that asks if the user wants
        to set the change on the selection"""
        if self._popup:
            self._popup.visible = False
        if apply_on_selection:
            self.__set_values(paths, value)
        else:
            self.__set_values([self._path], value)

    def __set_values(self, paths: List[str], value: bool):
        omni.kit.commands.execute("SetPayLoadLoadSelectedPrimsCommand", selected_paths=paths, value=value)

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

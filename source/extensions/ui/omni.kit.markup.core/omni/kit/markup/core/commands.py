# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import ctypes
import os
from datetime import datetime
from typing import Callable, cast

import carb
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
import omni.usd.commands
from omni.kit.async_engine import run_coroutine
from omni.kit.viewport.utility import get_active_viewport_window
from PIL import Image
from pxr import Sdf, Usd, UsdGeom

from .common import MARKUP_ROOT_PRIM_PATH, SETTINGS_MARKUP_ROOT
from .viewport_markup import ViewportMarkup

SETTINGS_MARKUP_ACTIVE = SETTINGS_MARKUP_ROOT + "active_markup"

SETTINGS_MARKUP_ROOT = "/persistent/exts/omni.kit.tool.markup/"
SETTINGS_VIEWPORT_RECT = SETTINGS_MARKUP_ROOT + "viewport_rect"
# this setting is for hide the markup panel
# but still show the markup element to capture the markup thumbnail
MARKUP_TOOL_HIDE = f"{SETTINGS_MARKUP_ROOT}tool_hide"
NAV_OP_PATH = "/exts/omni.kit.tool.navigation/activeOperation"


def create_data_only_prim(stage, prim_path: str):
    edit_target = stage.GetEditTarget()
    current_layer = edit_target.GetLayer()

    with Sdf.ChangeBlock():
        prim_spec = Sdf.CreatePrimInLayer(current_layer, prim_path)
        prim_spec.specifier = Sdf.SpecifierDef
        ignore_prim_attr = Sdf.AttributeSpec(prim_spec, "omni:ignorePrim", Sdf.ValueTypeNames.Bool)
        ignore_prim_attr.specifier = Sdf.SpecifierDef
        ignore_prim_attr.default = True
        ignore_prim_attr.custom = True

    prim = stage.GetPrimAtPath(prim_path)
    omni.usd.editor.set_hide_in_stage_window(prim, True)
    return prim


class TakeMarkupScreenshotCommand(omni.kit.commands.Command):
    def __init__(self):
        self._settings = carb.settings.get_settings()

    def do(self):
        return run_coroutine(self.get_raw_data_async_save())

    async def get_raw_data_async_save(self):
        """
        Gets the framebuffer contents.

        It's async because the data becames available the next frame.
        """
        import omni.kit.app
        import omni.kit.renderer.capture

        self._settings.set(MARKUP_TOOL_HIDE, True)
        self._settings.set("/app/window/hideUi", True)

        # We want to hold for a few frames to ensure that all of the UI is in fact hidden.
        # otherwise there is a better chance of catching the viewport in a transitory state. -Bob
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        renderer_capture = omni.kit.renderer.capture.acquire_renderer_capture_interface()
        renderer_capture.capture_next_frame_swapchain_callback(self._on_full_window_captured)
        await omni.kit.app.get_app().next_update_async()
        renderer_capture.wait_async_capture()

    def _on_full_window_captured(self, buffer, buffer_size, width, height, format):
        try:
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
        except Exception as e:  # pragma: no cover
            carb.log_error(f"[Waypoint] Failed to get capture buffer: {e}")
            return None

        window = get_active_viewport_window()
        frame = window.get_frame("markup_elements_frame")
        frame_rect = [
            frame.screen_position_x,
            frame.screen_position_y,
            frame.screen_position_x + frame.width,
            frame.screen_position_y + frame.height,
        ]
        viewport_rect = self._settings.get(SETTINGS_VIEWPORT_RECT) or frame_rect

        # Constrcut Image object
        buffer = content.contents
        im = Image.frombytes("RGBA", (width, height), buffer)

        # Check if the user specified the screenshots folder.
        screenshot_path = self._settings.get_as_string("/persistent/app/captureFrame/path")
        if screenshot_path:
            if not os.path.exists(screenshot_path):  # pragma: no cover
                os.makedirs(screenshot_path)
            if os.path.isdir(screenshot_path):
                # Filename is generated from the root layer, and the markup primtiives name.
                now = datetime.now()
                date_time = now.strftime("%Y-%m-%d %H.%M.%S")
                markup_name = self._settings.get_as_string(SETTINGS_MARKUP_ACTIVE)
                capture_filename = f"Screenshot {date_time!s}_{markup_name}.png"
                # crop viewport window from whole window image
                im = im.crop(viewport_rect)  # type: ignore
                im.save(os.path.join(screenshot_path, capture_filename), "png")
            else:  # pragma: no cover
                carb.log_error(f"Can't save screenshot to {screenshot_path!s} because it is not a directory")

        self._settings.set(MARKUP_TOOL_HIDE, False)
        self._settings.set("/app/window/hideUi", False)


class CreateMarkupEntryCommand(omni.kit.commands.Command):
    def __init__(
        self,
        entry_name: str = "",
        on_create_fn: "Callable[[Usd.Prim], None]|None" = None,
        sidecar_data=None,
        on_undo_fn: "Callable[..., None]|None" = None,
    ):
        if not entry_name:
            entry_name = "Markup_00"
        self._stage: Usd.Stage = omni.usd.get_context().get_stage()
        entry_name = (
            entry_name if entry_name.startswith(MARKUP_ROOT_PRIM_PATH) else f"{MARKUP_ROOT_PRIM_PATH}/{entry_name}"
        )
        self._name = cast(str, omni.usd.get_stage_next_free_path(self._stage, entry_name, False))
        self._on_create_fn = on_create_fn
        self._on_undo_fn = on_undo_fn
        self._sidecar_data = sidecar_data
        self._vm: "ViewportMarkup|None" = None

    def do(self) -> "ViewportMarkup|None":
        root = self._stage.GetPrimAtPath(MARKUP_ROOT_PRIM_PATH)
        if not root:
            create_data_only_prim(self._stage, MARKUP_ROOT_PRIM_PATH)

        create_data_only_prim(self._stage, self._name)
        prim = self._stage.GetPrimAtPath(self._name)
        if prim:
            self._vm = ViewportMarkup(prim.GetName(), sidecar_data=self._sidecar_data)
            self._vm.create(self._on_create_fn)
            return self._vm

    def undo(self):
        if callable(self._on_undo_fn):
            self._on_undo_fn(self._vm)
        else:
            omni.usd.commands.DeletePrimsCommand([self._name]).do()


class DeleteMarkupEntryCommand(omni.kit.commands.Command):
    def __init__(self, entry_name: str):
        self._stage: Usd.Stage = omni.usd.get_context().get_stage()
        self._entry_name = (
            entry_name if entry_name.startswith(MARKUP_ROOT_PRIM_PATH) else f"{MARKUP_ROOT_PRIM_PATH}/{entry_name}"
        )

    def do(self):
        omni.kit.commands.execute("DeletePrimsCommand", paths=[self._entry_name])

    # def undo(self):
    #     pass


class UpdateMarkupEntryCommand(omni.kit.commands.Command):
    """
    Example usaged:
    >>> omni.usd.commands.execute(
    >>>     "UpdateMarkupEntry",
    >>>     entry_name="/Viewport_Markups/Markup_0",
    >>>     comment=(Sdf.ValueTypeNames.String, "This is a markup"), )

    """

    def __init__(self, entry_name: str, **data: "dict[str, tuple[Sdf.ValueTypeName, object]]"):
        self._stage: Usd.Stage = omni.usd.get_context().get_stage()
        self._name = entry_name
        self._data = data

    def do(self):
        prim: Usd.Prim = cast(Usd.Prim, self._stage.GetPrimAtPath(self._name))
        for name, (type_name, value) in self._data.items():
            at = prim.GetAttribute(name)
            if at:
                omni.kit.commands.execute(
                    "ChangePropertyCommand",
                    prop_path=at.GetPath(),
                    value=value,
                    prev=at.Get(),
                    type_to_create_if_not_exist=type_name,
                )

    # def undo(self):
    #     pass


class RenameMarkupEntryCommand(omni.kit.commands.Command):

    def __init__(
        self,
        entry_name: str = "",
        new_name: str = "",
        on_move_fn: Callable[[Sdf.Path, Sdf.Path], None] = lambda new, old: None,
    ):
        self._stage: Usd.Stage = omni.usd.get_context().get_stage()
        self._name = (
            entry_name if entry_name.startswith(MARKUP_ROOT_PRIM_PATH) else f"{MARKUP_ROOT_PRIM_PATH}/{entry_name}"
        )
        new_name = (
            new_name if new_name.startswith(MARKUP_ROOT_PRIM_PATH) else "/".join([MARKUP_ROOT_PRIM_PATH, new_name])
        )
        self._new_name = cast(str, omni.usd.get_stage_next_free_path(self._stage, new_name, False))
        self._on_move_fn = on_move_fn

    def do(self):
        omni.kit.commands.execute(
            "MovePrimsCommand", paths_to_move={self._name: self._new_name}, on_move_fn=self._on_move_fn
        )


class CreateMarkupElementCommand(omni.kit.commands.Command):
    def __init__(self, markup: str, element_type: str, **data: "dict[str, tuple[Sdf.ValueTypeName, object]]"):
        self._markup = markup
        self._name: str = None
        self._type = element_type
        self._data = data

    def do(self):
        stage: Usd.Stage = omni.usd.get_context().get_stage()
        self._name = cast(str, omni.usd.get_stage_next_free_path(stage, f"{self._markup}/{self._type}_0", False))

        create_data_only_prim(stage, self._name)
        prim = stage.GetPrimAtPath(self._name)
        if prim:
            omni.kit.commands.execute(
                "CreateUsdAttributeCommand",
                prim=prim,
                attr_name="type",
                attr_type=Sdf.ValueTypeNames.String,
                attr_value=self._type,
            )
            for name, (type_name, value) in self._data.items():
                omni.kit.commands.execute(
                    "CreateUsdAttributeCommand", prim=prim, attr_name=name, attr_type=type_name, attr_value=value
                )

        return prim.GetName(), self._name

    def undo(self):
        omni.usd.commands.DeletePrimsCommand([self._name]).do()


class DeleteMarkupElementCommand(omni.kit.commands.Command):
    def __init__(self, element_name: str):
        self._stage: Usd.Stage = omni.usd.get_context().get_stage()
        self._element_name = element_name
        self._delete_cmd = omni.usd.commands.DeletePrimsCommand([self._element_name])

    def do(self):
        return self._delete_cmd.do()

    def undo(self):
        return self._delete_cmd.undo()


class UpdateMarkupElementCommand(omni.kit.commands.Command):
    """
    Example usage:
    >>> omni.usd.commands.execute(
    >>>     "UpdateMarkupElement",
    >>>     element="/Viewport_Markups/Markup_0/Label0",
    >>>     text=(Sdf.ValueTypeNames.String, "This is a markup"), )

    """

    def __init__(self, element: str, **data: "dict[str, tuple[Sdf.ValueTypeName, object]]"):
        self._name = Sdf.Path(element)
        self._data = data

    def do(self):
        stage: Usd.Stage = omni.usd.get_context().get_stage()
        prim: Usd.Prim = cast(Usd.Prim, stage.GetPrimAtPath(self._name))
        assert prim.IsValid()
        if prim.IsValid():
            for name, (type_name, value) in self._data.items():
                if prim.HasAttribute(name):
                    prev_value = prim.GetAttribute(name).Get()
                else:
                    prev_value = None
                omni.kit.commands.execute(
                    "ChangePropertyCommand",
                    prop_path=self._name.AppendProperty(name),
                    value=value,
                    prev=prev_value,
                    type_to_create_if_not_exist=type_name,
                )

    def undo(self):
        pass

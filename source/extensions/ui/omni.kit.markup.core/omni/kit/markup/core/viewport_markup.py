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
import importlib
from typing import Callable, List, Optional, Tuple

import carb
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.timeline
import omni.ui as ui
import omni.usd
import omni.usd.commands
from omni.kit.async_engine import run_coroutine
from omni.kit.waypoint.core.external import UsdBakedPreview
from omni.kit.waypoint.core.settings import AbstractWaypointSetting, CameraSetting, GeneralSetting, ThumbnailSetting
from PIL import Image
from pxr import Sdf, Usd

from .common import CURRENT_TOOL_PATH, MARKUP_ROOT_PRIM_PATH, SETTINGS_MARKUP_ROOT, ApproveType
from .markup_usd import MarkupUsd

SETTINGS_MARKUP_ROOT = "/persistent/exts/omni.kit.tool.markup/"
SETTINGS_VIEWPORT_RECT = SETTINGS_MARKUP_ROOT + "viewport_rect"
# this setting is for hide the markup panel
# but still show the markup element to capture the markup thumbnail
MARKUP_TOOL_HIDE = f"{SETTINGS_MARKUP_ROOT}tool_hide"
NAV_OP_PATH = "/exts/omni.kit.tool.navigation/activeOperation"
HIDE_IN_STAGE_WINDOW = "hide_in_stage_window"
THUMBNAIL_SIZE = (160, 90)


def set_hide_in_stage_window(prim, hide):
    # prim.SetMetadata(HIDE_IN_STAGE_WINDOW, hide)
    pass


class MarkupThumbnailSetting(ThumbnailSetting):
    def __init__(self, sidecar_data=None):
        super().__init__(sidecar_data)
        self._settings = carb.settings.get_settings()
        self._capture_callback = None

    async def get_raw_data_async_save(self, capture_callback) -> None:
        """
        Gets the framebuffer contents.

        It's async because the data becames available the next frame.
        """

        # OM-55628 - Hide/restore floating dialogs so they don't appear in thumbnails.
        self._settings.set("/app/window/hideUi", True)
        # We want to hold for a few frames to ensure that all of the UI is in fact hidden.
        # otherwise there is a better chance of catching the viewport in a transitory state. -Bob
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()  # type: ignore

        self._capture_callback = capture_callback
        self._settings.set(MARKUP_TOOL_HIDE, True)
        if not self._renderer_capture:
            module_omni_renderer_capture = importlib.import_module("omni.kit.renderer.capture")
            self._renderer_capture = module_omni_renderer_capture.acquire_renderer_capture_interface()

        self._renderer_capture.capture_next_frame_swapchain_callback(self._on_full_window_captured)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self._renderer_capture.wait_async_capture()

        # OM-55628 - Hide/restore floating dialogs so they don't appear in thumbnails.
        self._settings.set("/app/window/hideUi", False)

    def _on_full_window_captured(self, buffer, buffer_size, width, height, format):
        self._settings.set(MARKUP_TOOL_HIDE, False)
        self._settings.set(CURRENT_TOOL_PATH, "navigation")
        # self._settings.set(NAV_OP_PATH, "orbit")

        try:
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
        except Exception as e:  # pragma: no cover
            carb.log_error(f"[Markup] Failed to get capture buffer: {e}")
            if self.on_created_fn is not None:
                self.on_created_fn(False)
            return None

        # Constrcut Image object
        buffer = content.contents
        im = Image.frombytes("RGBA", (width, height), buffer)

        # crop viewport window from whole window image
        left, top, right, bottom = [0, 0, *THUMBNAIL_SIZE]  # type: ignore
        viewport_rect = self._settings.get(SETTINGS_VIEWPORT_RECT)
        if viewport_rect is not None:  # pragma: no cover
            dpi_scale = ui.Workspace.get_dpi_scale()
            bottom = viewport_rect[3] * dpi_scale
            left = viewport_rect[0] * dpi_scale
            right = viewport_rect[2] * dpi_scale
            top = viewport_rect[1] * dpi_scale
        width = right - left
        height = bottom - top
        if width / height > THUMBNAIL_SIZE[0] / THUMBNAIL_SIZE[1]:  # pragma: no cover
            left = (width - height * THUMBNAIL_SIZE[0] / THUMBNAIL_SIZE[1]) / 2
            right = width - left
        elif width / height < THUMBNAIL_SIZE[0] / THUMBNAIL_SIZE[1]:  # pragma: no cover
            top = (height - width * THUMBNAIL_SIZE[1] / THUMBNAIL_SIZE[0]) / 2
            bottom = height - top

        viewport_area = [left, top, right, bottom]
        im = im.crop(viewport_area)  # type: ignore

        # Generate thumbnail
        im.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        # Save to prim
        with self.edit_context:
            baked = UsdBakedPreview(self.prim)
            # Baking the thumbnail at its actual dimensions keeps them from breaking all the time.
            try:
                baked.set_baked_preview_data(im.tobytes(), im.width, im.height, format)
            except AttributeError:  # pragma: no cover
                # trying to update on an out-dated session
                return
            if self.on_created_fn is not None:
                self.on_created_fn(True)
            if self._capture_callback:
                self._capture_callback()


class MarkupApproveSetting(AbstractWaypointSetting):
    def __init__(self, sidecar_data=None):
        super().__init__(sidecar_data)
        self._sidecar_data = sidecar_data
        self._settings = carb.settings.get_settings()
        self._approve_type: ApproveType = ApproveType.NONE

    @property
    def approval_type(self) -> ApproveType:  # pragma: no cover
        return self._approve_type

    def set_approve_type(self, approve_type: ApproveType, usd_prim: Usd.Prim) -> None:
        self._approve_type = approve_type
        self.save(usd_prim)

    def save_to_usd(self, prim: Usd.Prim) -> None:
        with self.edit_context:
            self._save_attribute(prim, "approval", self._approve_type.value, Sdf.ValueTypeNames.Int)
            if self._sidecar_data:  # pragma: no cover
                self._sidecar_data.save()

    def load_from_usd(self, prim: Usd.Prim):
        val = prim.GetAttribute("approval").Get()
        val = val if val is not None else ApproveType.NONE
        self._approve_type = ApproveType(val)

    def get_name(self):
        return "Approve"


# A markup instance
class ViewportMarkup:
    def __init__(self, name, parent_path="", *, sidecar_data=None):
        self._usd_prim = None
        self._init(name, parent_path)
        self.__sidecar_data = sidecar_data

        self._general_setting = GeneralSetting(sidecar_data)
        self._thumbnail_setting = MarkupThumbnailSetting(sidecar_data)
        self._camera_setting = CameraSetting(sidecar_data)
        self._approve_setting = MarkupApproveSetting(sidecar_data)
        self._markup_settings = [
            self._general_setting,
            self._camera_setting,
            # Thumbanil is the last one to notify creation done after thumbnail generated
            self._approve_setting,
            self._thumbnail_setting,
        ]

    @property
    def edit_context(self) -> Usd.EditContext:
        return (
            self.__sidecar_data.edit_context
            if self.__sidecar_data
            else Usd.EditContext(omni.usd.get_context().get_stage(), Usd.EditTarget(None))
        )

    def __repr__(self):
        return f'"{self._name}"'

    def __str__(self):
        return f'"{self._name}"'

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def path(self) -> str:
        return self._get_usd_prim().GetPath().pathString

    @property
    def thumbnail(self) -> Optional[str]:
        return self._thumbnail_setting.thumbnail_path

    @property
    def thumbnail_data(self) -> Optional[Tuple[bytes, int, int]]:
        return self._thumbnail_setting.thumbnail_data

    @property
    def create_time(self) -> Optional[str]:
        return self._general_setting.data["create_time"]

    @property
    def created_by(self) -> Optional[str]:
        return self._general_setting.data["created_by"]

    @property
    def comment(self) -> str:
        return self._general_setting.data["comment"]

    @comment.setter
    def comment(self, comment: str):
        self._general_setting.set_comment(comment)

    @property
    def frame(self) -> float:
        return self._general_setting.data.get("frame", 0.0)

    @frame.setter
    def frame(self, frame: float):
        self._general_setting.set_frame(frame)

    @property
    def approval_type(self) -> ApproveType:
        return self._approve_setting.approval_type

    @property
    def camera_prim(self) -> Optional[Usd.Prim]:
        # Camera may not be captured
        return self._camera_setting.camera_prim

    @property
    def usd_prim(self) -> Optional[Usd.Prim]:
        # Camera may not be captured
        return self._get_usd_prim()

    @property
    def is_dirty(self) -> bool:
        for setting in self._markup_settings:
            if setting.is_dirty():
                return True
        return False

    @property
    def info(self) -> Optional[List[List[str]]]:
        info = []
        for setting in self._markup_settings:
            if setting.info:
                info.extend(setting.info)
        return info

    def recall(
        self,
        without_camera=False,
        enable_settings: Optional[List[str]] = None,
        disable_settings: Optional[List[str]] = None,
    ):
        recall_disable_settings = []
        if disable_settings is not None:
            recall_disable_settings.extend(disable_settings)
        if enable_settings is not None:
            for name in enable_settings:
                while name in recall_disable_settings:
                    recall_disable_settings.remove(name)

        usd_prim = self._get_usd_prim()
        if usd_prim is not None:
            if without_camera:
                if self._camera_setting.get_name() not in recall_disable_settings:
                    recall_disable_settings.append(self._camera_setting.get_name())

            for setting in self._markup_settings:
                if setting.get_name() not in recall_disable_settings:
                    setting.recall(usd_prim)
        else:  # pragma: no cover
            carb.log_warn("Failed to get prim of current viewport markup.")

    def rename(self, new_name):
        if not Sdf.Path.IsValidPathString(new_name):
            return False

        usd_prim = self._get_usd_prim()
        if usd_prim is not None:
            old_path = self.get_usd_prim_path()
            self._name = new_name
            new_path = self.get_usd_prim_path()
            move_dict = {old_path: new_path}
            with self.edit_context:
                omni.kit.commands.execute(
                    "MovePrimsCommand", paths_to_move=move_dict, on_move_fn=self._on_rename_fn, destructive=False
                )
                for setting in self._markup_settings:
                    setting.update(omni.usd.get_context().get_stage().GetPrimAtPath(new_path))
            return True
        else:  # pragma: no cover
            return False

    def create(self, on_created_fn: "Callable[..., None]|None" = None):
        capture_disable_settings = []
        self._thumbnail_setting.on_created_fn = on_created_fn
        for setting in self._markup_settings:
            setting.create(setting.get_name() not in capture_disable_settings)

        # Save current data (of models) to USD prim
        usd_prim = self._get_usd_prim()
        if usd_prim is not None:
            for setting in self._markup_settings:
                if setting.is_valid():
                    setting.save(usd_prim)

        self._hide_markup_root()

    def create_from_prim(self, prim: Usd.Prim) -> bool:
        prim_path = prim.GetPath().pathString
        parent_path, _, markup_name = prim_path.rpartition("/")

        self._init(markup_name, parent_path)

        carb.log_info(f"load {markup_name}")
        for setting in self._markup_settings:
            setting.load(prim)
            carb.log_info(f" {setting.get_name()}: {setting.valid}")

        self._hide_markup_root()
        return True

    def delete(self):
        for setting in self._markup_settings:
            setting.delete()

        stage = omni.usd.get_context().get_stage()
        if stage and stage.GetPrimAtPath(self.get_usd_prim_path()):  # type: ignore
            with self.edit_context:
                omni.kit.commands.execute("DeletePrims", paths=[self.get_usd_prim_path()], destructive=False)
        self._init()

    def get_usd_prim_path(self) -> str:
        return self._parent_path + "/" + self._name

    def _init(self, name="", parent_path=""):
        self._name = name
        if len(parent_path) > 0:
            self._parent_path = parent_path
        else:
            self._parent_path = MARKUP_ROOT_PRIM_PATH
        self._thumbnail = None
        self._usd_obj = None
        self._usd_prim = None

    def _on_rename_fn(self, old_prim_name: Sdf.Path, new_prim_name: Sdf.Path):
        pass

    def _hide_markup_root(self) -> None:
        usd_obj = self._get_usd_obj()
        markup_root_prim = usd_obj.get_prim(MARKUP_ROOT_PRIM_PATH)
        if markup_root_prim:
            set_hide_in_stage_window(markup_root_prim, True)

    def _get_usd_obj(self) -> MarkupUsd:
        if self._usd_obj is None:
            self._usd_obj = MarkupUsd()
        else:
            self._usd_obj.update_stage(omni.usd.get_context().get_stage())
        return self._usd_obj

    def _get_usd_prim(self) -> Usd.Prim:
        if not self._usd_prim:
            prim_path = self.get_usd_prim_path()
            self._usd_prim = self._get_usd_obj().get_prim(prim_path)
        return self._usd_prim

    def refresh_thumbnail(self, refresh_callback):
        self._thumbnail_setting.prim = self._get_usd_prim()
        run_coroutine(self._thumbnail_setting.get_raw_data_async_save(refresh_callback))

    # Markup Approval
    def approve(self) -> None:
        self._approve_setting.set_approve_type(ApproveType.APPROVED, self.usd_prim)

    def reject(self) -> None:
        self._approve_setting.set_approve_type(ApproveType.REJECTED, self.usd_prim)

    def reset_approval(self):
        self._approve_setting.set_approve_type(ApproveType.NONE, self.usd_prim)

    async def wait(self):
        for i in range(8):
            await omni.kit.app.get_app().next_update_async()

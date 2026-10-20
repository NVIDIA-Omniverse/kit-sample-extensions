# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import functools
import traceback
from asyncio.tasks import Task
from typing import Optional

import carb
import omni.kit.app
import omni.ui as ui
from carb.eventdispatcher import Event, get_eventdispatcher
from omni.kit.widget.material_preview import MaterialPreviewProducer
from pxr import Sdf

# The number of frames with no stage modification to update the relevant stage
DELAY_FRAMES = 5


class MaterialPreviewImage:
    """
    An Image widget to show material preview.
    Refer to omni.kit.window.material_preview.MaterialPreviewViewport
    """

    def __init__(self):
        self._material_path: Sdf.Path = None
        self._ui_built: bool = False
        self._material_preview_producer = None

        self._frame = ui.Frame()
        self._frame.set_build_fn(self._build_ui)

    def destroy(self):
        self._viewport_image = None
        if self._material_preview_producer:
            self._material_preview_producer.destroy()
            self._material_preview_producer = None
            self._update_sub = None

    @property
    def visible(self):
        return self._frame.visible

    @visible.setter
    def visible(self, value):
        self._frame.visible = value

    @property
    def material(self):
        return self._material_path.pathString

    @material.setter
    def material(self, path):
        self._material_path = Sdf.Path(path)
        if self._ui_built:
            self._material_preview_producer.set_material(self._material_path)

    async def capture_thumbnail_async(self):
        return await self._material_preview_producer.set_captured_data_async()

    def capture_thumbnail(self) -> None:
        self._material_preview_producer.set_captured_data()

    def _build_ui(self) -> None:
        self._material_preview_producer = MaterialPreviewProducer()
        self._material_preview_producer.set_material(self._material_path)
        self._width = None
        self._height = None
        self.__task: Optional[Task] = None

        with ui.ZStack():
            self._viewport_provider = ui.ImageProvider()
            self._viewport_image = ui.ImageWithProvider(
                self._viewport_provider,
                alignment=ui.Alignment.CENTER,
                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                style_type_name_override="SingleMaterial.Image",
            )
            self._loading_label = ui.Label(
                "Loading preview...", alignment=ui.Alignment.CENTER, style_type_name_override="EmptyNotification.Label"
            )

        self._drawable_change_sub = self._material_preview_producer.set_on_drawable_changed_fn(
            self.__on_drawable_changed
        )
        self._time_interval = 0
        self._update_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.window.material.MaterialPreviewImage",
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=self._on_update,
        )
        self._ui_built = True

    def __on_drawable_changed(self) -> None:
        """Called by material_preview_producer when the render is updated"""
        gpu_reference = self._material_preview_producer.gpu_reference
        if not bool(gpu_reference):
            return

        # Needing to pass tests between old (broken MaterialPreviewProducer) and new (fixed MaterialPreviewProducer)
        # Quick check to detect whether extenion is using legacy (broken) APIs by testing if gpu_reference
        # is PyCapsule should accomplish this without heavy ctypes dependency
        #
        t = type(gpu_reference)
        is_legacy_object = (t.__module__ == "builtins") and (t.__name__ == "PyCapsule")

        # Build a tuple of (gpu_reference)
        args = (gpu_reference,)
        if is_legacy_object:
            # Edit arg-tuple to select proper set_image_data method variant
            resolution = self._material_preview_producer.resolution
            args = (args[0], resolution[0], resolution[1], ui.TextureFormat.RGBA8_UNORM)

        self._viewport_provider.set_image_data(*args)

        # Render was successfully updated, hide the "Loading" label and kill update subscription
        self._loading_label.visible = False
        self._update_sub = None

    def _on_update(self, event: Event):
        self._time_interval += event["dt"]
        dot_count = (int(self._time_interval * 2)) % 3
        self._loading_label.text = "Loading preview" + "." * dot_count

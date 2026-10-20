# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["SimpleViewportWidget"]

import asyncio
import functools
import traceback
from asyncio.tasks import Task
from typing import Optional

import carb
import carb.events
import carb.settings
import omni.hydratexture
import omni.kit.app
import omni.kit.extensionwindow
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import Event, get_eventdispatcher
from pxr import Gf, Sdf, UsdGeom

# OMPE-57994: hydra_texture events is updated to Events 2.0 in 108.2 so here try to add transition code to accommodate both
_is_legacy_hydra_texture_event = not hasattr(omni.hydratexture, "GLOBAL_EVENT_DRAWABLE_CHANGED")

# The number of frames with no stage modification to update the relevant stage
DELAY_FRAMES = 5


def handle_exception(func):  # pragma: no cover
    """
    Decorator to print exception in async functions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


class SimpleViewportWidget:
    """
    Widget with simple viewport that shows already opened USD context.

    It's unused and it's here for example reasons.
    """

    def __init__(self, context_name: str, hydra_texture_name: str, **kwargs):
        self._context_name = context_name
        self._context = omni.usd.get_context(context_name)

        # Additional viewport prints errors when DLSS is ON (OM-31146)
        self._settings = carb.settings.get_settings()
        aa = self._settings.get("/rtx/post/aa/op")
        if aa == 3:
            # Turn off DLSS
            self._settings.set("/rtx/post/aa/op", 1)

        self._hydra_texture_factory = omni.hydratexture.acquire_hydra_texture_factory_interface()

        # It will be changed once hydra_texture is initialized
        self._width = 32
        self._height = 32
        self.__task: Optional[Task] = None

        self._hydra_texture = self._hydra_texture_factory.create_hydra_texture(
            hydra_texture_name,
            self._width,
            self._height,
            self._context_name,
            is_async=self._settings.get("/app/asyncRendering"),
        )

        self._camera_path: Sdf.Path = Sdf.Path(self._hydra_texture.get_camera_path())

        # We need to react ASAP on the drawable change - so subscribing to PUSH to specific event type
        if _is_legacy_hydra_texture_event:
            event_stream = self._hydra_texture.get_event_stream()
            self._drawable_change_sub = event_stream.create_subscription_to_push_by_type(
                omni.hydratexture.EVENT_TYPE_DRAWABLE_CHANGED,
                self._on_drawable_changed_legacy,
                name="Material Preview drawable change",
            )
        else:
            self._drawable_change_sub = get_eventdispatcher().observe_event(
                observer_name="Material Preview drawable change",
                event_name=omni.hydratexture.GLOBAL_EVENT_DRAWABLE_CHANGED,
                filter=self._hydra_texture.get_event_key(),  # very important to specify this for filtering
                on_event=self._on_drawable_changed,
            )

        self._frame = ui.Frame(**kwargs)

        with self._frame:
            self._viewport_provider = ui.ImageProvider()
            self._viewport_image = ui.ImageWithProvider(
                self._viewport_provider, computed_content_size_changed_fn=self._content_size_changed
            )

    def destroy(self):
        self._viewport_image = None
        self._viewport_provider = None

        self._frame = None

        self._drawable_change_sub = None
        self._hydra_engine_change_sub = None

        self._hydra_texture = None

        self._hydra_texture_factory = None
        self._settings = None

        self._context = None

    def set_active_camera(self, camera: Sdf.Path):
        """Sets the active camera in the viewport to a USD camera."""
        self._camera_path = camera
        self._hydra_texture.set_camera_path(camera.pathString)

    def _update_drawable(self, result_handle: Optional[int]):
        if result_handle is None:
            carb.log_error("No result_handle during EVENT_TYPE_DRAWABLE_CHANGED")
            return

        gpu_reference = self._hydra_texture.get_drawable_resource(result_handle)
        if not gpu_reference:
            carb.log_error("No gpu_reference during EVENT_TYPE_DRAWABLE_CHANGED")
            return

        self._viewport_provider.set_image_data(gpu_reference)

    def _on_drawable_changed_legacy(self, event: carb.events.IEvent):
        if event.type != omni.hydratexture.EVENT_TYPE_DRAWABLE_CHANGED:
            carb.log_error("Wrong event captured for DRAWABLE_CHANGED!")
            return

        result_handle = event.payload.get("result_handle", None)
        self._update_drawable(result_handle)

    def _on_drawable_changed(self, event: Event):
        self._update_drawable(event["result_handle"])

    def _content_size_changed(self):
        width = int(self._viewport_image.computed_content_width)
        height = int(self._viewport_image.computed_content_height)
        if self._width != width or self._height != height:
            self._width = width
            self._height = height

        self.__delay_frames = DELAY_FRAMES
        if self.__task is None or self.__task.done():
            self.__task = asyncio.ensure_future(self.__resize_hydra_texture())

    @handle_exception
    async def __resize_hydra_texture(self):
        """Called to update the dirty data in the next frame"""
        while self.__delay_frames > 0:
            await omni.kit.app.get_app().next_update_async()
            self.__delay_frames -= 1

        # Pump the changes to the model.
        if self._hydra_texture:
            self._hydra_texture.width = self._width
            self._hydra_texture.height = self._height

        self.__set_perspective()

        self.__task = None

    def __set_perspective(self):
        """Set the aspect ratio to match resolution"""
        stage = self._context.get_stage() if self._context else None
        if not stage:
            return

        camera_prim = stage.GetPrimAtPath(self._camera_path)
        if not camera_prim or not camera_prim.IsA(UsdGeom.Camera):
            return

        camera = UsdGeom.Camera(camera_prim)
        gf_camera = camera.GetCamera()
        gf_camera.SetPerspectiveFromAspectRatioAndFieldOfView(
            aspectRatio=self._width / self._height,
            fieldOfView=gf_camera.GetFieldOfView(Gf.Camera.FOVHorizontal),
            direction=Gf.Camera.FOVHorizontal,
        )
        camera.SetFromCamera(gf_camera)

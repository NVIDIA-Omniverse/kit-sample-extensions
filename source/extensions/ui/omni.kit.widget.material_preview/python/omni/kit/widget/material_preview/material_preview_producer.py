# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["class MaterialPreviewProducer"]

import asyncio
import importlib
import random
import string
from typing import List, Optional, Tuple

import carb.settings
import omni.hydratexture
import omni.kit.renderer.capture
import omni.usd
from carb.eventdispatcher import Event, get_eventdispatcher
from omni.kit.app import queue_event, register_event_alias
from pxr import Gf, Sdf, UsdGeom

try:
    # OMPE-80508: `convert_raw_bytes_to_list` is only re-exported by the public package from the kit
    # release that moved the capture bindings into it. On older kit it lives in the deprecated
    # `omni.kit.renderer_capture` bindings module, which that release keeps as a shim.
    from omni.kit.renderer.capture import convert_raw_bytes_to_list
except ImportError:  # pragma: no cover - older kit
    from omni.kit.renderer_capture import convert_raw_bytes_to_list

from .relevant_stage import RelevantStage
from .stage_duplicate_utils import copy_prim
from .swatch_utils import get_default_camera, get_swatch_layer
from .usd_baked_preview import UsdBakedPreview

# OMPE-57994: hydra_texture events is updated to Events 2.0 in 108.2 so here try to add transition code to accommodate both
_is_legacy_hydra_texture_event = not hasattr(omni.hydratexture, "GLOBAL_EVENT_DRAWABLE_CHANGED")


class MaterialPreviewProducer:
    """
    This object creates a new USD context and Hydra texture. It watches the
    given shader and synchronizes it with the source context. The purpose of
    this class is to return the GPU ID of the viewport to use in
    ImageProvider.
    """

    class _Event(set):
        """
        A list of callable objects. Calling an instance of this will cause a
        call to each item in the list in ascending order by index.
        """

        def __call__(self, *args, **kwargs):
            """Called when the instance is “called” as a function"""
            # Call all the saved functions
            for f in self:
                f(*args, **kwargs)

        def __repr__(self):
            """
            Called by the repr() built-in function to compute the “official”
            string representation of an object.
            """
            return f"MaterialPreviewProducer_Event({set.__repr__(self)})"

    class _EventSubscription:
        """
        Event subscription.

        _Event has callback while this object exists.
        """

        def __init__(self, event, fn):
            """
            Save the function, the event, and add the function to the event.
            """
            self._fn = fn
            self._event = event
            event.add(self._fn)

        def __del__(self):
            """Called by GC."""
            self._event.remove(self._fn)

    def __init__(
        self,
        source_context_name: str = "",
        shader_path: Optional[Sdf.Path] = None,
        swatch_layer_path: Optional[str] = None,
        camera_path: Optional[Sdf.Path] = None,
        hydra_engine_name: str = "rtx",
    ):
        """
        The object is created unititialized. It will be automatically
        initialized when requesting GPU ID.

        ### Arguments:

            `source_context_name : str`
                The name of the USD context with the given shader

            `shader_path : Optional[Sdf.Path]`
                The path to the shader to synchtonize

            `swatch_layer_path : Optional[str]`
                The usd scene with the swatch

            `camera_path : Optional[Sdf.Path]`
                The path to the camera in the swatch scene.
        """

        self._source_context_name = source_context_name
        self._source_shader_path: Optional[Sdf.Path] = shader_path
        self._swatch_layer_path = swatch_layer_path

        self._target_context_name = None

        # It will create an empty context
        self._relevant_stage = None

        # Camera path is from the layer if the given one is None
        self._camera_path: Sdf.Path = camera_path or Sdf.Path()

        self._settings = None
        self._hydra_texture_factory = None
        self._hydra_texture = None
        self.__current_result_handle = None
        self.__paused = False

        # Default resolution
        self._resolution = None

        self.__on_drawable_changed = self._Event()
        self.__on_baked_preview_changed = self._Event()

        self._renderer_capture = None
        self.__capture_futures = []
        self.__hydra_engine_name = hydra_engine_name

    def initialize(self):
        """
        Initialize the object
        """
        if self._relevant_stage is not None:
            return

        # Random name for the material preview context
        letters = string.ascii_uppercase
        self._target_context_name = self._source_context_name + "_" + "".join(random.choice(letters) for i in range(5))

        # It will create an empty context
        self._relevant_stage = RelevantStage(self._target_context_name, self._source_context_name)
        self._relevant_stage.set_root_changed_fn(self.__on_material_changed)
        self.clear()
        if self._source_shader_path:
            # Copy the layer to the empty context
            layer = get_swatch_layer(self._source_shader_path, self._swatch_layer_path)
            self.submit_layer(layer)

            self.set_listen_root(self._source_shader_path)

            # Copy shader from the source context
            self.__copy_shader()
        else:
            layer = None

        # Camera path is from the layer if the given one is None
        self._camera_path = (
            self._camera_path
            or Sdf.Path("/" + self._target_context_name + str(get_default_camera(layer)))
            or Sdf.Path("/OmniverseKit_Persp")
        )

        self._settings = carb.settings.get_settings()

        self._hydra_texture_factory = omni.hydratexture.acquire_hydra_texture_factory_interface()

        # Default resolution. Set property, it will set self._resolution and the camera perspective.
        self.resolution = [256, 256]

        # Resolve the renderer to use
        # 1. Read from hydra_engine_name passed to contructor
        # 2. Fallback to global setting: /renderer/active
        # 3. Fallback to global setting: /renderer/enabled
        # 4. Fallback to rtx
        #
        hydra_engine_name = self.__hydra_engine_name
        if hydra_engine_name is None:
            hydra_engine_name = self._settings.get("/renderer/active")
            if hydra_engine_name is None:
                hydra_engine_name = self._settings.get("/renderer/enabled")
                if hydra_engine_name is None:
                    hydra_engine_name = "rtx"

        # Additional viewport prints errors when DLSS is ON (OM-31146)
        if hydra_engine_name == "rtx":
            if self._settings.get("/rtx/post/aa/op") == 3:
                # Turn off DLSS
                self._settings.set("/rtx/post/aa/op", 1)

        # Make sure the renderer is attached to the target-usd-context
        #
        target_context = omni.usd.get_context(self._target_context_name)
        if hydra_engine_name not in target_context.get_attached_hydra_engine_names():
            omni.usd.add_hydra_engine(hydra_engine_name, target_context)

        self._hydra_texture = self._hydra_texture_factory.create_hydra_texture(
            name=self._target_context_name,
            width=self._resolution[0],
            height=self._resolution[1],
            usd_context_name=self._target_context_name,
            usd_camera_path=self._camera_path.pathString,
            hydra_engine_name=hydra_engine_name,
            is_async=self._settings.get("/app/asyncRendering"),
        )
        # Call through to property setter to handle the pause now
        if self.__paused:
            self.paused = self.__paused

        if _is_legacy_hydra_texture_event:
            event_stream = self._hydra_texture.get_event_stream()
            self.__drawable_changed_subscription = event_stream.create_subscription_to_push_by_type(
                omni.hydratexture.EVENT_TYPE_DRAWABLE_CHANGED,
                self.__on_hydra_texture_drawable_changed_legacy,
                name="Material Preview Producer drawable change",
            )
        else:
            self.__drawable_changed_subscription = carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="Material Preview Producer drawable change",
                event_name=omni.hydratexture.GLOBAL_EVENT_DRAWABLE_CHANGED,
                filter=self._hydra_texture.get_event_key(),  # very important to specify this for filtering
                on_event=self.__on_hydra_texture_drawable_changed,
            )

    def destroy(self):
        self.__on_drawable_changed = None
        self.__on_baked_preview_changed = None
        self.__drawable_changed_subscription = None

        self._renderer_capture = None
        self._hydra_texture = None
        self._hydra_texture_factory = None
        self._settings = None

        if self._relevant_stage:
            self._relevant_stage.destroy()
        self._relevant_stage = None

        self._context = None

    def set_on_baked_preview_changed_fn(self, callback_fn):
        """
        Callback when any property of the material is changed.
        """
        return self._EventSubscription(self.__on_baked_preview_changed, callback_fn)

    def set_on_drawable_changed_fn(self, callback_fn):
        """
        Callback when the resolution is changed. When it happened, the
        user should recreate ui.ImageProvider.
        """
        return self._EventSubscription(self.__on_drawable_changed, callback_fn)

    def set_material(self, shader_path: Sdf.Path):
        """The path to the shader to watch"""
        if self._source_shader_path == shader_path:
            return

        self._source_shader_path = shader_path

        self.initialize()
        self.__copy_shader()
        self.__bind_shader()

        self.set_listen_root(shader_path)

    @property
    def material_path(self):
        """The path to the shader to watch"""
        return self._source_shader_path

    @material_path.setter
    def material_path(self, path):
        """The path to the shader to watch"""
        self.set_material(path)

    @property
    def gpu_reference(self):
        """Opaque GPU reference"""
        if self.__current_result_handle is not None:
            gpu_reference = self._hydra_texture.get_drawable_resource(self.__current_result_handle)
            return gpu_reference if gpu_reference else None

        if self._hydra_texture is None:
            self.initialize()
            return

        carb.log_error("Cannot call get_raw_data_async at arbitrary times, must be durring frame delivery callback")
        return None

    @property
    def resolution(self):
        self.initialize()
        return [self._hydra_texture.width, self._hydra_texture.height]

    @resolution.setter
    def resolution(self, value):
        if self._resolution == value:
            return

        self._resolution = value[:]
        if self._hydra_texture:
            self._hydra_texture.width = self._resolution[0]
            self._hydra_texture.height = self._resolution[1]

        self.__set_perspective()

    @property
    def paused(self):
        return self.__paused

    @paused.setter
    def paused(self, value):
        self.__paused = bool(value)
        if self._hydra_texture:
            self._hydra_texture.set_updates_enabled(self.__paused)

    @property
    def camera_prim(self):
        context = omni.usd.get_context(self._target_context_name)
        if not context:
            return None

        stage = context.get_stage()
        if not stage:
            return None

        camera_prim = stage.GetPrimAtPath(self._camera_path)
        if not camera_prim or not camera_prim.IsA(UsdGeom.Camera):
            return None

        return camera_prim

    @property
    def ready_for_capture(self) -> bool:  # pragma: no cover
        return True

    async def get_raw_data_async(self) -> Tuple[List[int], int, int, int, int]:
        """
        Gets the framebuffer contents.

        It's async because the data becames available the next frame.
        """
        self.__capture_futures.append(asyncio.Future())
        return await self.__capture_futures[-1]

    async def set_captured_data_async(self):
        if self._relevant_stage is None:
            return None

        data = await self.get_raw_data_async()
        if not data:
            return None

        buffer, buffer_size, width, height, format = data

        # Save preview to the current prim
        context = omni.usd.get_context(self._source_context_name)
        stage = context.get_stage()
        if not stage:
            return None

        prim = stage.GetPrimAtPath(self._source_shader_path)
        if not prim:
            return None

        baked = UsdBakedPreview(prim)
        baked.set_baked_preview_data(buffer, width, height, format)
        return (buffer, width, height)

    def set_captured_data(self):
        """Captures the framebuffer and saves it to the current material"""
        asyncio.ensure_future(self.set_captured_data_async())

    def get_captured_raw_data(self) -> Optional[Tuple[List[int], int, int]]:
        """Returns baked preview (data, width, height)"""
        # Save preview to the current prim
        context = omni.usd.get_context(self._source_context_name)
        stage = context.get_stage()
        if not stage:
            return

        prim = stage.GetPrimAtPath(self._source_shader_path)
        if not prim:
            return

        baked = UsdBakedPreview(prim)
        return baked.get_baked_preview_data()

    def set_listen_root(self, root: Sdf.Path):
        """Set path that is synchronized with the swatch stage"""
        self.initialize()
        if root:
            self._relevant_stage.set_listen_root(root)

    def clear(self):
        """Clear the swatch stage"""
        self.initialize()
        self._relevant_stage.clear()
        self._camera_path = Sdf.Path()

    def submit_layer(self, delta_layer: Sdf.Layer):
        """Sent the given layer to the swatch stage"""
        self.initialize()
        self._relevant_stage.submit_layer(delta_layer)

    def submit_text(self, delta_text: str):
        """Sent the given layer as text to the swatch stage"""
        self.initialize()
        self._relevant_stage.submit_text(delta_text)

    def submit_camera(self, camera: Sdf.Path):
        """Set the camera"""
        self.initialize()
        if self._camera_path != camera:
            self._camera_path = camera
            self._hydra_texture.set_camera_path(camera.pathString)
            self.__set_perspective()

    def __set_perspective(self):
        """Set the aspect ratio to match resolution"""
        context = omni.usd.get_context(self._target_context_name)
        if not context:
            return

        stage = context.get_stage()
        if not stage:
            return

        camera_prim = stage.GetPrimAtPath(self._camera_path)
        if not camera_prim or not camera_prim.IsA(UsdGeom.Camera):
            return

        camera = UsdGeom.Camera(camera_prim)
        gf_camera = camera.GetCamera()
        gf_camera.SetPerspectiveFromAspectRatioAndFieldOfView(
            aspectRatio=float(self._resolution[0]) / float(self._resolution[1]),
            fieldOfView=gf_camera.GetFieldOfView(Gf.Camera.FOVHorizontal),
            direction=Gf.Camera.FOVHorizontal,
        )
        camera.SetFromCamera(gf_camera)

    def __bind_shader(self):
        """Bind the shader to the swatch"""
        target_context = omni.usd.get_context(self._target_context_name)
        if not target_context:
            return

        target_stage = target_context.get_stage()
        if not target_stage:
            return

        tagret_layer = target_stage.GetRootLayer()

        # Get default prim
        if tagret_layer.HasDefaultPrim():
            default_prim_name = tagret_layer.defaultPrim
        else:
            children = target_stage.GetRootLayer().pseudoRoot.nameChildren
            if not children:
                # There are no prims
                return
            default_prim_name = children[0].name

        default_prim_path = Sdf.Path("/" + self._target_context_name + "/" + default_prim_name)

        # Bind material to the default prim
        swatch = target_stage.GetPrimAtPath(default_prim_path)
        rel = swatch.CreateRelationship("material:binding", False)
        self._target_shader_path = Sdf.Path("/" + self._target_context_name + str(self._source_shader_path))
        rel.SetTargets([self._target_shader_path])
        rel.SetMetadata("bindMaterialAs", "weakerThanDescendants")

    def __copy_shader(self):
        """Copy the shader from the source context to the swatch context"""
        source_context = omni.usd.get_context(self._source_context_name)
        if not source_context:
            return

        source_stage = source_context.get_stage()
        if not source_stage:
            return

        # TODO: Copy to the buffer and pass using submit_layer
        target_context = omni.usd.get_context(self._target_context_name)
        if not target_context:
            return

        target_stage = target_context.get_stage()
        if not target_stage:
            return

        # Pre-create parents of material
        for parent in self._source_shader_path.GetParentPath().GetPrefixes():
            target_stage.DefinePrim(parent, "Scope")

        # Copying a material from MarblesAssets takes 0.0225s
        # Copy material to the preview context
        copy_prim(source_stage.GetPrimAtPath(self._source_shader_path), target_stage, self._target_context_name)
        # Another way is using flattening. But copying a material from MarblesAssets takes 3.2314s
        # flatten_layer = source_stage.Flatten()
        # Sdf.CopySpec(flatten_layer, self._source_shader_path, target_stage.GetRootLayer(), self._source_shader_path)

    def __schedule_captures(self):
        assert self.__current_result_handle is not None
        assert len(self.__capture_futures) > 0

        # Swap self.__capture_futures to local variable so any subsequent requests go to next rendered frame
        capture_futures, self.__capture_futures = self.__capture_futures, []
        if not self._renderer_capture:
            self._renderer_capture = omni.kit.renderer.capture.acquire_renderer_capture_interface()

        rp_resource = self._hydra_texture.get_drawable_resource(self.__current_result_handle)
        if not rp_resource:
            # Log an error but make sure all async awaits complete (they will need to handle this error case)
            # Since set_captured_data_async sets a precedence of None as a possible value returned, use that
            carb.log_error("No resource for current render")
            for ftr in capture_futures:
                ftr.set_result(None)
            return

        def on_capture(buffer, buffer_size, width, height, pixel_format):
            # Existing API assumes a list of bytes, so do conversion now
            # This can cost us in terms of performance as it means nobody can operate on the cheaper
            # buffer object, but the API is public methods and unclear who else uses it
            # On the plus side, there is a win in the case that multiple consumers want to converto to a list.
            #
            buf_list = convert_raw_bytes_to_list(buffer, buffer_size, width, height, pixel_format)
            for ftr in capture_futures:
                if not ftr.done():
                    ftr.set_result((buf_list, buffer_size, width, height, pixel_format))

        self._renderer_capture.capture_next_frame_rp_resource_callback(on_capture, rp_resource)

    def __on_hydra_texture_drawable_changed_legacy(self, event: carb.events.IEvent):
        """Called by the hydra texture when the resolution is changed"""
        if event.type != omni.hydratexture.EVENT_TYPE_DRAWABLE_CHANGED:
            carb.log_error("Wrong event captured for DRAWABLE_CHANGED!")
            return

        # Cache self.__current_result_handle for a moment so existing stateless API
        # that assumes GPU textures have an infinite lifetime works if called properly.
        try:
            self.__current_result_handle = event.payload.get("result_handle", None)
            if self.__capture_futures:
                self.__schedule_captures()
            self.__on_drawable_changed()
        finally:
            self.__current_result_handle = None

    def __on_hydra_texture_drawable_changed(self, event: Event):
        # Cache self.__current_result_handle for a moment so existing stateless API
        # that assumes GPU textures have an infinite lifetime works if called properly.
        try:
            self.__current_result_handle = event["result_handle"]
            if self.__capture_futures:
                self.__schedule_captures()
            self.__on_drawable_changed()
        finally:
            self.__current_result_handle = None

    def __on_material_changed(self, properties):
        """Called by RelevantStage when the root material is changed"""
        for property in properties:
            if property.name == UsdBakedPreview.ATTR_NAME:
                self.__on_baked_preview_changed()

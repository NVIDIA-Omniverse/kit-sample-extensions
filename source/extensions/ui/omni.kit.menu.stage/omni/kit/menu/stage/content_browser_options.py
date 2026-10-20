"""This module provides tools for managing content browser integration options that add file-based assets to a USD stage through context menus and dynamic placement based on current scene selection or viewport parameters."""

import os
from functools import partial

import omni.kit.commands
import omni.kit.context_menu
import omni.usd
from carb import log_error, settings
from omni.kit.commands import create
from pxr import Gf, Sdf, Tf, Usd, UsdGeom


class ContentBrowserOptions:
    """Class for managing options in the content browser integration.

    This class facilitates the registration of additional context menus within the content browser to assist in adding file-based assets to a USD stage. It listens for content browser load and unload events and configures corresponding actions, allowing users to add files as references or payloads depending on the current scene selection or active viewport. The class dynamically determines placement by computing positions from selected prims or by querying viewport parameters, ensuring that new prims are positioned appropriately whether the user has an active selection or not.

    The class is intended for use within the Omni kit environment where extensions and commands interplay to enhance content management workflows. It does not accept any initialization parameters.
    """

    def __init__(self):
        """Initializes the ContentBrowserOptions instance."""
        pass

    def startup(self):
        """Starts up ContentBrowserOptions by subscribing to extension events and loading the content browser."""
        self._settings = settings.get_settings()
        self._content_browser = None
        manager = omni.kit.app.get_app().get_extension_manager()
        self._content_browser_sub = manager.subscribe_to_extension_enable(
            on_enable_fn=lambda _: self._on_content_browser_load(),
            on_disable_fn=lambda _: self._on_content_browser_unload(),
            ext_name="omni.kit.window.content_browser",
            hook_name="omni.kit.menu.stage omni.kit.window.content_browser listener",
        )

        self._on_content_browser_load()

    def shutdown(self):
        """Shuts down ContentBrowserOptions by unsubscribing from events and unloading the content browser."""
        self._content_browser_sub = None
        self._on_content_browser_unload()

    def _on_content_browser_load(self):
        try:
            import omni.kit.window.content_browser

            self._content_browser = omni.kit.window.content_browser.get_content_window()

            def is_usd_file(path):
                return omni.usd.is_usd_writable_filetype(path)

            if self._content_browser is not None:
                self._content_browser.add_context_menu(
                    "Add at Current Selection",
                    "plus.svg",
                    lambda _, path: self._add_file_to_stage(path, self._settings, False),
                    is_usd_file,
                )
                self._content_browser.add_context_menu(
                    "Replace Current Selection",
                    "plus.svg",
                    lambda _, path: self._add_file_to_stage(path, self._settings, True),
                    is_usd_file,
                )

        except (ImportError, ModuleNotFoundError):
            pass

    def _on_content_browser_unload(self):
        if self._content_browser is not None:
            self._content_browser.delete_context_menu("Replace Current Selection")
            self._content_browser.delete_context_menu("Add to Stage")
        self._content_browser = None

    @staticmethod
    def _add_file_to_stage(file_path: str, settings: settings.ISettings, replace_selection: bool):
        """
        Add reference/payload to stage from file.

        If has a reference or payload selected, honor that type when doing replace at selected.
        If multi selection, honor the first.
        Otherwise honor the preferences setting.

        Where the new prim is placed depends on the current selection:

        If one or more prims is selected, the new prim is placed at the average position of those prims' transforms.

        If replace_selection is True, the selected prims are deleted before the new prim is added,
        and the new one is added as a child of the selected prims' first common parent.

        If nothing is selected, the new prim is placed on the ground plane in front of the camera
        (or, if the camera is not looking at the ground, at the camera's target point).
        In this case, the first instance of a Viewport 2 window is preferred; if this is unavailable,
        we fall back to a Viewport 1 version.
        """

        context = omni.usd.get_context()
        stage = context.get_stage()

        if stage is None:
            log_error(f"No valid stage found; cannot add reference to {file_path}.")
            return

        success = ContentBrowserOptions._add_to_stage_using_selection(context, stage, file_path, replace_selection)
        if not success:
            success = ContentBrowserOptions._add_to_stage_using_vp2(context, stage, file_path, settings)
        if not success:
            success = ContentBrowserOptions._add_to_stage_using_vp1(context, stage, file_path, settings)
        if not success:
            # If all else fails, just add the reference at the origin
            ContentBrowserOptions._add_to_stage_helper(context, stage, file_path, Gf.Vec3d(0))

    @staticmethod
    def _add_to_stage_using_selection(
        context: omni.usd.UsdContext, stage: Usd.Stage, file_path: str, replace_selection: bool
    ):

        # Get selection and average position of selected prims
        selection = context.get_selection()
        selected_prims = [
            stage.GetPrimAtPath(path)
            for path in selection.get_selected_prim_paths()
            if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
        ]

        if len(selected_prims) == 0:
            return False

        position = Gf.Vec3d(0)
        for prim in selected_prims:
            position += omni.usd.get_world_transform_matrix(prim).ExtractTranslation()
        position /= len(selected_prims)

        ContentBrowserOptions._add_to_stage_helper(
            context, stage, file_path, position, replace_selection, selected_prims
        )

        return True

    @staticmethod
    def _add_to_stage_using_vp2(context, stage, file_path, settings):
        vp2_api = None
        try:
            import omni.kit.viewport.window as vp2

            usd_context_name = ""
            # Since this option occurs from the content browser's context menu, we don't have a good basis
            # for choosing which vp2 window we should use for placement. So we're just using the first one.
            windows = list(vp2.get_viewport_window_instances(usd_context_name))
            if len(windows):
                vp2_api = windows[0].viewport_api
        except ImportError:
            pass

        if vp2_api:
            resolution = vp2_api.resolution
            pixel = (int(resolution[0] * 0.5), int(resolution[1] * 0.5))

            # the VP2 version of add_to_stage is still synchronous,
            # but we get the picked world-space position in a callback
            callback = partial(
                ContentBrowserOptions._add_to_stage_using_vp2_helper,
                context,
                stage,
                file_path,
                settings,
                vp2_api.camera_path,
            )
            vp2_api.request_query(
                pixel,
                lambda path, pos, *args: callback(Gf.Vec3d(*pos) if path else None),
                query_name="omni.kit.menu.stage.add_file_to_stage",
            )

            return True

        return False

    @staticmethod
    def _add_to_stage_using_vp2_helper(context, stage, file_path, settings, camera_path, position):
        if position is None:
            position = Gf.Vec3d(0)
            prim = stage.GetPrimAtPath(camera_path)
            camera = UsdGeom.Camera(prim) if prim else None
            if camera:
                grid_plane = settings.get("/app/viewport/grid/plane")
                o = Gf.Vec3d(0)
                frustum = camera.GetCamera().frustum
                c = frustum.GetPosition()
                d = frustum.ComputeViewDirection()

                # If no intersection is found, just use the camera's target
                _, position = ContentBrowserOptions._get_grid_intersection(
                    grid_plane, c, d, frustum.ComputeLookAtPoint()
                )

        ContentBrowserOptions._add_to_stage_helper(context, stage, file_path, position)

    @staticmethod
    def _add_to_stage_using_vp1(context, stage, file_path, settings):  # pragma: no cover
        """Deprecated."""

        viewport = None
        try:
            import omni.kit.viewport_legacy as viewport_legacy

            viewport = viewport_legacy.get_viewport_interface().get_viewport_window()
        except ImportError:
            pass

        if viewport:
            # If nothing is selected, we're going to raycast to the ground plane...
            active_camera = viewport.get_active_camera()
            ok, x, y, z = viewport.get_camera_target(active_camera)
            if ok:
                target = Gf.Vec3d(x, y, z)
            else:
                target = Gf.Vec3d(0, 0, 1)
            ok, x, y, z = viewport.get_camera_position(active_camera)
            if ok:
                camera_pos = Gf.Vec3d(x, y, z)
            else:
                camera_pos = Gf.Vec3d(0)
            direction = (target - camera_pos).GetNormalized()

            grid_plane = settings.get("/app/viewport/grid/plane")

            # If no intersection is found, just use the camera's target
            _, position = ContentBrowserOptions._get_grid_intersection(grid_plane, camera_pos, direction, target)

            ContentBrowserOptions._add_to_stage_helper(context, stage, file_path, position)

            return True

        return False

    @staticmethod
    def _add_to_stage_helper(
        context: omni.usd.UsdContext,
        stage: Usd.Stage,
        file_path: str,
        position: Gf.Vec3d,
        replace_selection: bool = False,
        selected_prims=[],
    ):
        # Reference or Payload for new prim
        dd_import = settings.get_settings().get("/persistent/app/stage/dragDropImport")
        create_as_payload = dd_import == "payload"
        if len(selected_prims) > 0:
            for prim in selected_prims:
                if prim.HasAuthoredReferences():
                    create_as_payload = False
                    break
                if prim.HasAuthoredPayloads():
                    create_as_payload = True
                    break

        # Parent path for new prim
        if replace_selection and len(selected_prims) > 0:
            parent_path = Sdf.Path.emptyPath
            for prim in selected_prims:
                if parent_path == Sdf.Path.emptyPath:
                    parent_path = prim.GetParent().GetPath()
                else:
                    parent_path = parent_path.GetCommonPrefix(prim.GetParent().GetPath())
        elif stage.HasDefaultPrim():
            parent_path = stage.GetDefaultPrim().GetPath()
        else:
            parent_path = Sdf.Path.absoluteRootPath

        with omni.kit.undo.group():
            # If replacing, delete selected prims before adding new reference to prevent potential name collision
            if replace_selection:
                context_menu = omni.kit.context_menu.get_instance()
                if context_menu is None:
                    log_error("Context menu is disabled.")
                    return
                can_delete = context_menu.can_delete({"prim_list": selected_prims})
                if not can_delete:
                    log_error("Selected prims are not eligible for replacement.")
                    return
                selected_prim_paths = [prim.GetPath() for prim in selected_prims]
                omni.kit.commands.execute("DeletePrimsCommand", paths=selected_prim_paths)

            # Create reference/payload and translate it to position
            prim_name = Tf.MakeValidIdentifier(os.path.splitext(os.path.basename(file_path))[0])
            prim_path = omni.usd.get_stage_next_free_path(stage, parent_path.AppendPath(prim_name).pathString, False)

            cmd_name = "CreatePayloadCommand" if create_as_payload else "CreateReferenceCommand"
            omni.kit.commands.execute(
                cmd_name, usd_context=context, path_to=prim_path, asset_path=file_path, instanceable=False
            )

            omni.kit.commands.execute("TransformPrimSRTCommand", path=prim_path, new_translation=position)

    @staticmethod
    def _get_grid_intersection(grid_plane, camera_position, camera_direction, default_value):
        c = camera_position
        d = camera_direction
        o = Gf.Vec3d(0)

        if grid_plane == "XY":
            n = Gf.Vec3d(0, 0, 1)
        elif grid_plane == "YZ":
            n = Gf.Vec3d(1, 0, 0)
        else:
            n = Gf.Vec3d(0, 1, 0)

        dot = d.GetDot(n)
        smallNumber = 1e-6
        position = default_value
        intersection = False
        if abs(dot) > smallNumber:
            t = (o - c).GetDot(n) / dot
            if t > 0:
                position = c + t * d
                intersection = True

        return intersection, position

# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["register_actions", "deregister_actions"]

from typing import Optional, Union

import carb
import omni.usd
from pxr import Sdf, Tf, Usd, UsdGeom, UsdLux

from .utility import _get_rig_name, _get_rig_names_and_paths, _make_light_mode_setting_key

_g_light_rig_hid_vp_lights = False


# Ideally CreateReferenceCommand would be used, but there are some issues with how it
# tries to create unique prims in the stage, make all paths relative, and only supports Usd.Stage.Define (no pure overs)
# The one thing that is nice about CreateReferenceCommand is that it handles differing up-axis between stage and reference.
# So we repeat that behavior here, but NOTE: This is not dynamic, changing stage-up does not affect the adjustment once
# it has been created (though adding/replacing with a new rig will trigger the adjustment)
def _add_rig_reference(light_rig_prim: Usd.Prim, rig_path: str):
    from pxr import Gf

    light_rig_prim.GetReferences().SetReferences([Sdf.Reference(rig_path)])

    xformable = UsdGeom.Xformable(light_rig_prim)

    # Helper method to return values indicating no adjustment was required
    def _require_no_adjustment():
        # Make sure to clear any prior adjustments that were applied
        xformable.ClearXformOpOrder()
        return (None, None)

    # Can't query metadata on Sdf.Layer easily via Python, so need to go thorugh UsdGeom with a Usd.Stage
    # First check that the reference succeeded and the layer is reachable.
    asset_layer = Sdf.Layer.FindOrOpen(rig_path)
    if not asset_layer:
        return _require_no_adjustment()

    ref_stage = Usd.Stage.Open(asset_layer, sessionLayer=None)
    if not ref_stage:
        return _require_no_adjustment()

    ref_up = UsdGeom.GetStageUpAxis(ref_stage).upper()
    cur_up = UsdGeom.GetStageUpAxis(light_rig_prim.GetStage()).upper()
    if ref_up == cur_up:
        return _require_no_adjustment()

    adjustment = None
    if cur_up == UsdGeom.Tokens.y:
        if ref_up == UsdGeom.Tokens.z:
            adjustment = Gf.Matrix4d(0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1)
        else:
            adjustment = Gf.Matrix4d(0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1)
    elif cur_up == UsdGeom.Tokens.z:
        if ref_up == UsdGeom.Tokens.y:
            adjustment = Gf.Matrix4d(0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1)
        else:
            adjustment = Gf.Matrix4d(0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1)
    else:
        if ref_up == UsdGeom.Tokens.y:
            adjustment = Gf.Matrix4d(0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1)
        else:
            adjustment = Gf.Matrix4d(0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1)

    # Can set to any existing attributes but CANNOT CREATE them as the caller is in an Sd.ChangeBlock
    if adjustment:
        op_order_attr = xformable.GetXformOpOrderAttr()
        if op_order_attr:
            op_order = op_order_attr.Get()
            if op_order and ("xformOp:transform" in op_order):
                transform_attr = light_rig_prim.GetProperty("xformOp:transform")
                if transform_attr:
                    transform_attr.Set(adjustment)
                    adjustment = None
                    xformable = None

    return (xformable, adjustment)


def _clear_usd_references(stage: Usd.Stage, prim_path: str):
    # Disable any existing rig by removing references
    # Doing this first should remove any extra lights that would be toggled in session-layer visibility below
    prim = stage.GetPrimAtPath(prim_path)
    if prim and prim.IsDefined():
        prim.GetReferences().SetReferences([])
    return prim


def _set_lighting_mode(
    lighting_mode: Optional[Union[str, int]] = None,
    usd_context: Optional[omni.usd.UsdContext] = None,
    viewport=None,
    *args,
    **kwargs,
):
    # If not omni.usd.UsdContext is provided, get one from the Viewport or active Viewport
    if not usd_context:
        if not viewport:
            try:
                import omni.kit.viewport.utility

                viewport = omni.kit.viewport.utility.get_active_viewport()
            except ImportError:
                carb.log_warn("omni.kit.viewport.utility is unavailable.")

            if not viewport:
                carb.log_warn(
                    "Not able to set the lighting mode, an omni.usd.UsdContext was not provided and no active Viewport"
                )
                return (False, None, None)

        usd_context = viewport.usd_context
        if not usd_context:
            carb.log_warn(
                "Not able to set the lighting mode, an omni.usd.UsdContext was not provided and the the Viewport didn't have one."
            )
            return (False, None, None)

    settings = carb.settings.get_settings()
    # Per-stage setting to signal a change for consumers of the info
    light_mode_setting_key = _make_light_mode_setting_key(usd_context)
    # Get the current lighting mode in the setting for return and to compare to what is being set
    prev_lighting_mode = settings.get(light_mode_setting_key)

    # lighting_mode="" or lighting_mode=None is stage-lighting (no overrides)
    # we just use a better name internally to avoid lighting_mode==""
    if not prev_lighting_mode:
        prev_lighting_mode = "stage"

    # Helper function for standardizzed return value, defaulting to failure
    def issue_return(success: bool = False):
        return (success, "" if lighting_mode == "stage" else lighting_mode, prev_lighting_mode)

    # lighting_mode may be an integer constant referencing an item in the light-rig list
    # otherwise (if not int-0, move no lighting-mode to easier to read "stage" for now)
    if not lighting_mode and not isinstance(lighting_mode, int):
        lighting_mode = "stage"

    stage = usd_context.get_stage()
    if not stage:
        carb.log_warn("Not able to set the lighting mode, the omni.usd.UsdContext had no stage.")
        return issue_return()

    # lighting_mode may be an integer constant referencing an item in the light-rig list
    asset_path = None
    is_camera_mode = lighting_mode == "camera"
    is_light_rig = not is_camera_mode and (lighting_mode != "stage") and (lighting_mode != "off")

    # Now reduce the lighting mode to a rig name and path
    if is_light_rig:
        # Special case set_lighting_mode(-1) to use the setting and not require clients to know about it
        if lighting_mode == -1:
            dftl_lighting_mode = settings.get("/exts/omni.kit.viewport.menubar.lighting/defaultRig")
            if dftl_lighting_mode is None:
                carb.log_error("Not able to set the lighting mode, no default lighting rig is set")
                return issue_return()
            lighting_mode = dftl_lighting_mode

        names_and_paths = _get_rig_names_and_paths("omni.kit.viewport.menubar.lighting")
        if not names_and_paths:
            return issue_return()

        index = 0
        for name, path in names_and_paths:
            if (index == lighting_mode) or (name == lighting_mode):
                lighting_mode, asset_path = name, str(path)
                break
            index = index + 1

        if asset_path is None:
            carb.log_warn(f"Not able to set the lighting mode, no lighting rig found for {lighting_mode}")
            return issue_return()

        # Ideally we could early exit when lighting_mode == prev_lighting_mode, but that
        # doesn't work across multiple stage opens.
        if lighting_mode == prev_lighting_mode:
            carb.log_info("Skipping change in lighting mode as it is already applied")
            return issue_return()

    # No need to do anything if lighting mode is and will be stage
    if (lighting_mode != "stage") or (prev_lighting_mode != "stage"):
        import omni.usd

        from .utility import VisibilityEdit

        # Where the light rig will be attached
        rig_prim_path = "/OmniKit_Viewport_LightRig"

        # Simple callback for scene traversal that return whether the prim is a Light
        def is_a_light(prim: Usd.Prim, prim_path: Sdf.Path):
            return prim.HasAPI(UsdLux.LightAPI)

        # XXX: Note, VisibilityEdit is always run.  In theory this could be ellided based on whether
        # prev_lighting_mode was "stage" or not, but because new lights can be created and show up in
        # other modes, it is always run for now.

        with Usd.EditContext(stage, stage.GetSessionLayer()):
            # This needs to be done outside of the change-block
            api_types_for_prune = ["LightAPI"]
            if is_light_rig:
                light_rig_prim = stage.OverridePrim(rig_prim_path)

                # Care has to be taken to not create xform-ops inside the ChangeBlock, but they can be set to
                xformable, adjustment = None, None

                # UsdRt currently require the clearing of references to happen outside of the Sdf.ChangeBlock
                light_rig_prim = _clear_usd_references(stage, rig_prim_path)

                with Sdf.ChangeBlock():
                    # Pass None as prim-to-show, and is_a_light as prim-to-hide
                    VisibilityEdit(stage, None, is_a_light, api_types_for_prune=api_types_for_prune).run()

                    # Use CreateReferenceCommand as it will handle differences in stage-up
                    xformable, adjustment = _add_rig_reference(light_rig_prim, asset_path)
                    omni.usd.editor.set_hide_in_stage_window(light_rig_prim, True)
                    omni.usd.editor.set_no_delete(light_rig_prim, True)

                usd_context.set_pickable(rig_prim_path, False)

                if xformable and adjustment:
                    xformable.AddXformOp(UsdGeom.XformOp.TypeTransform).Set(adjustment)
            else:
                # UsdRt currently require the clearing of references to happen outside of the Sdf.ChangeBlock
                light_rig_prim = _clear_usd_references(stage, rig_prim_path)

                # OMPE-99588: no outer ChangeBlock so VisibilityEdit can flush restore notices separately
                if lighting_mode == "stage":
                    # Pass is_a_light as prim-to-show, and None as prim-to-hide
                    VisibilityEdit(stage, is_a_light, None, api_types_for_prune=api_types_for_prune).run()
                else:
                    with Sdf.ChangeBlock():
                        # Pass None as prim-to-show, and is_a_light as prim-to-hide
                        VisibilityEdit(stage, None, is_a_light, api_types_for_prune=api_types_for_prune).run()

    # Hide the Viewport light sprites if requested
    if settings.get("/exts/omni.kit.viewport.menubar.lighting/defaultRigHidesViewportLights"):
        global _g_light_rig_hid_vp_lights
        lighting_bits = 1 << 8
        options = settings.get("/persistent/app/viewport/displayOptions") or 0
        if is_light_rig:
            if options & lighting_bits:
                _g_light_rig_hid_vp_lights = True
                settings.set("/persistent/app/viewport/displayOptions", options & ~(lighting_bits))
        elif _g_light_rig_hid_vp_lights:
            _g_light_rig_hid_vp_lights = False
            settings.set("/persistent/app/viewport/displayOptions", options | lighting_bits)

    # Remove the "stage" synonym local to this function and set to "no lighting mode" when enabling stage lighting
    result = issue_return(True)

    # Set the lighting mode setting path for any consumers watching
    if settings.get(light_mode_setting_key) != result[1]:
        settings.set(light_mode_setting_key, result[1])

    # Make sure to set view-based lighting setting to be picked up by renderer
    if bool(settings.get("/rtx/useViewLightingMode")) != is_camera_mode:
        settings.set("/rtx/useViewLightingMode", is_camera_mode)

    return result


def _import_light_rig(path_to: Optional[str] = None, usd_context_name: str = "", exclusive_select: bool = True):
    import omni.kit.commands

    usd_context = omni.usd.get_context(usd_context_name)
    if not usd_context:
        raise RuntimeError(f"UsdContext named '{usd_context_name}' was not found")
        return False
    stage = usd_context.get_stage()
    if not stage:
        raise RuntimeError(f"UsdContext named '{usd_context_name}' had no stage")
        return False

    rig_prim_path = "/OmniKit_Viewport_LightRig"
    light_rig_prim = stage.GetPrimAtPath(rig_prim_path)
    if not light_rig_prim:
        raise RuntimeError(f"UsdContext named '{usd_context_name}' had no light rig")
        return False

    rig_import_section = "/exts/omni.kit.viewport.menubar.lighting/rigImport"
    rig_root_path = carb.settings.get_settings().get(f"{rig_import_section}/root")
    rig_root_path = Sdf.Path(rig_root_path) if rig_root_path else None
    if path_to is None:
        prim_name_key = f"{rig_import_section}/primName"
        path_to = carb.settings.get_settings().get(prim_name_key)
        # Try old setting
        if not path_to:
            deprecated_key = f"{rig_import_section}PrimName"
            path_to = carb.settings.get_settings().get(deprecated_key)
            if path_to:
                carb.log_warn("'{deprecated_key}' is deprecated, please use '{prim_name_key}'")
        if not path_to:
            path_to = carb.settings.get_settings().get(_make_light_mode_setting_key(usd_context))

    if path_to:
        path_to = Tf.MakeValidIdentifier(path_to)
        if rig_root_path and not path_to.startswith(rig_root_path.pathString):
            path_to = rig_root_path.AppendChild(path_to).pathString

    with omni.kit.undo.group():
        if rig_root_path:
            rig_root_prim = stage.GetPrimAtPath(rig_root_path)
            traversal_limit = carb.settings.get_settings().get(f"{rig_import_section}/lightRemovalLimit")
            if not rig_root_prim:
                omni.kit.commands.execute(
                    "CreatePrimWithDefaultXformCommand",
                    prim_type="Xform",
                    prim_path=rig_root_path,
                    select_new_prim=False,
                    stage=stage,
                )
            elif traversal_limit:

                def collect_prims_to_remove(
                    root_prim: Usd.Prim, can_remove_root: bool, traversal_limit: int, level: int
                ):
                    if level >= traversal_limit:
                        return []
                    children = root_prim.GetChildren()
                    if len(children) == 0:
                        return [root_prim.GetPath()] if can_remove_root else []

                    level = level + 1
                    objects_to_remove = []
                    for child in children:
                        if child.HasAPI(UsdLux.LightAPI):
                            objects_to_remove.append(child.GetPath())
                        elif child.IsA(UsdGeom.Xform) or child.IsA(UsdGeom.Scope):
                            objects_to_remove += collect_prims_to_remove(child, True, traversal_limit, level)

                    if can_remove_root:
                        if len(objects_to_remove) == len(children):
                            objects_to_remove = [root_prim.GetPath()]

                    return objects_to_remove

                omni.kit.commands.execute(
                    "DeletePrimsCommand",
                    paths=collect_prims_to_remove(rig_root_prim, False, traversal_limit, 0),
                    stage=stage,
                )

        # Get the next free path after any removal has taken place
        if path_to:
            path_to = omni.usd.get_stage_next_free_path(stage, path_to, prepend_default_prim=not bool(rig_root_path))

        omni.kit.commands.execute(
            "CopyPrimCommand",
            path_from=rig_prim_path,
            path_to=path_to,
            duplicate_layers=True,
            combine_layers=True,
            flatten_references=True,
            exclusive_select=exclusive_select,
        )

        imported_prim = stage.GetPrimAtPath(path_to)
        if not imported_prim:
            raise RuntimeError(f"CopyPrimCommand failed to import lights into '{path_to}'")
            return False

        omni.usd.editor.set_hide_in_stage_window(imported_prim, False)
        omni.usd.editor.set_no_delete(imported_prim, False)
        return True

    # Likely an exception was thrown in above with sceop, making this unreachable
    return False


class RegisteredActions:
    _ACTION_TAG = "Viewport Lighting Menu Actions"

    def __init__(self, extension_id: str):
        action_registry = None
        self.__extension_id = None

        try:
            import omni.kit.actions.core

            action_registry = omni.kit.actions.core.get_action_registry()
        except (ImportError, AttributeError):
            import traceback

            carb.log_error(traceback.format_exc())

        if not action_registry:
            return

        # Signal that de-registration should occur on destruction
        self.__extension_id = extension_id

        action_registry.register_action(
            extension_id,
            "set_lighting_mode_off",
            lambda: _set_lighting_mode("off"),
            display_name="Disable Stage Lighting",
            description="Disable all of the lights for a stage in the active Viewport or one provided.",
            tag=self._ACTION_TAG,
        )

        action_registry.register_action(
            extension_id,
            "set_lighting_mode_stage",
            lambda: _set_lighting_mode("stage"),
            display_name="Enable Stage Lighting",
            description="Enable any previously disabled lights for a stage in the active Viewport or one provided.",
            tag=self._ACTION_TAG,
        )

        action_registry.register_action(
            extension_id,
            "set_lighting_mode_camera",
            lambda: _set_lighting_mode("camera"),
            display_name="Enable Camera Lighting",
            description="Enable camera lighting mode for a stage.  This look is renderer specific but will often ignore any stage lights.",
            tag=self._ACTION_TAG,
        )

        action_registry.register_action(
            extension_id,
            "set_lighting_mode_rig",
            _set_lighting_mode,
            display_name="Enable Rig Lighting",
            description="Disable all stage lighting and add a single reference to a provided light rig.",
            tag=self._ACTION_TAG,
        )

        action_registry.register_action(
            extension_id,
            "import_lighting_rig",
            _import_light_rig,
            display_name="Import Current Lighting Rig",
            description="Import the current lighting-menu light rig into the stage.",
            tag=self._ACTION_TAG,
        )

    def __del__(self):
        self.destroy()

    def destroy(self):
        extension_id, self.__extension_id = self.__extension_id, None
        if extension_id:
            import omni.kit.actions

            action_registry = omni.kit.actions.core.get_action_registry()
            action_registry.deregister_all_actions_for_extension(extension_id)

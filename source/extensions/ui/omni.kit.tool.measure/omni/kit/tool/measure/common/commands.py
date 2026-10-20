# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import math
from typing import List, Sequence, Union

import carb
import omni.kit.app
import omni.kit.commands as commands
import omni.usd as ou
from omni.kit import undo
from pxr import Gf, Sdf, Usd, UsdGeom

from ..manager import MeasurementManager
from ..system import MeasurePayload, MeasurePrim
from .constant import DistanceType, LabelSize, MeasureMode, Precision, UnitType


class CreateMeasurementCommand(commands.Command):
    def __init__(self, measure_payload: MeasurePayload):
        self._payload: MeasurePayload = measure_payload

    def do(self):
        with undo.disabled():
            MeasurementManager()._create_internal(self._payload)

    def undo(self):
        # Set the created prim to be deletable
        measure_prim: MeasurePrim = MeasurementManager().read(self._payload.uuid)
        measure_prim._prim.SetMetadata("no_delete", False)

        with undo.disabled():
            MeasurementManager().delete(measure_prim.uuid)


class CreateMeasurementPointToPointCommand(commands.Command):
    def __init__(
        self,
        prim_paths: List[str],
        points: List[Gf.Vec3d],
        unit_type: UnitType = UnitType.CENTIMETERS,
        precision: Precision = Precision.HUNDRETH,
        label_size: LabelSize = LabelSize.MEDIUM,
    ):
        self._prim_paths = prim_paths
        self._points = MeasurePayload.world_to_local_points(points, prim_paths)
        self._unit_type = unit_type
        self._precision = precision
        self._label_size = label_size

    def do(self):
        with undo.disabled():
            payload: MeasurePayload = MeasurePayload()
            payload.prim_paths = self._prim_paths
            payload.points = self._points
            payload.tool_mode = MeasureMode.POINT_TO_POINT
            payload.unit_type = self._unit_type
            payload.precision = self._precision
            payload.label_size = self._label_size
            self._payload: MeasurePayload = payload
            MeasurementManager()._create_internal(payload)

    def undo(self):
        # Set the created prim to be deletable
        measure_prim: MeasurePrim = MeasurementManager().read(self._payload.uuid)
        measure_prim._prim.SetMetadata("no_delete", False)

        with undo.disabled():
            MeasurementManager().delete(measure_prim.uuid)


class RemoveMeasurementCommand(commands.Command):
    """
    Command that removes the measurement from Measurement Manager and Clears drawing
    Undo recreates the measurement as a new measurement from scratch.
    """

    def __init__(self, measure_prim: MeasurePrim):
        self._measure_prim: MeasurePrim = measure_prim
        self._payload: MeasurePayload = self._measure_prim.payload

    # Find the Measure + Draw node associated with the UUID and destroy it
    def do(self) -> None:
        # unlock prim for delete
        self._measure_prim._prim.SetMetadata("no_delete", False)
        # Delete the prim
        commands.execute("DeletePrims", paths=[self._measure_prim.path])
        undo.get_undo_stack().pop()

    def undo(self) -> None:
        with undo.disabled():
            # Recreate the measurement using the cached payload
            self._payload.visible = True  # Ensure the measurement is visible.

            MeasurementManager().create(self._payload)

        # Clear selection
        selection = ou.get_context().get_selection()
        selection.clear_selected_prim_paths()


class FramePointsCommand(commands.Command):
    """
    Transform a primitive to encompass the bounds of a list of points.

    Args:
        prim_to_move: Path to the primitive that is being moved.
        points(Sequence[Gf.Vec3d]): Sequence of points to use to calculate the bounds to frame.
        time_code(Usd.TimeCode): Timecode to set values at.
        usd_context_name(str): Name of the usd context to work on.
        aspect_ratio(float): Width / Height of the final image.
        use_horizontal_fov(bool): Whether to use a camera's horizontal or vertical field of view for framing.
        horizontal_fov(float): Default horizontal field-of-view to use for framing if one cannot be calculated.
        zoom(float): Final zoom in or out of the framed box. Values above 0.5 move further away and below 0.5 go closer.
    """

    def __init__(
        self,
        prim_to_move: Union[str, Sdf.Path],
        points: Sequence[Gf.Vec3d],
        time_code: Usd.TimeCode = None,
        usd_context_name: str = "",
        aspect_ratio: float = 1,
        use_horizontal_fov: bool = None,
        zoom: float = 0.45,
        horizontal_fov: float = 0.20656116130367255,
    ):
        self.__usd_context_name = usd_context_name
        self.__prim_to_move = prim_to_move
        self.__time_code = time_code if time_code is not None else Usd.TimeCode.Default()
        self.__points = points
        self.__created_property = False
        self.__aspect_ratio = abs(aspect_ratio) or 1.0
        self.__horizontal_fov = horizontal_fov
        self.__use_horizontal_fov = use_horizontal_fov
        self.__zoom = zoom

    def __compute_local_transform(self, stage: Usd.Stage):
        prim = stage.GetPrimAtPath(self.__prim_to_move)
        if not prim:
            carb.log_warn(f"Framing of UsdPrims failed, {self.__prim_to_move} doesn't exist")
            return None, None, None, None

        local_xform, world_xform = None, None
        xformable = UsdGeom.Xformable(prim)
        if xformable:
            local_xform = xformable.GetLocalTransformation(self.__time_code)

        imageable = UsdGeom.Imageable(prim)
        if imageable:
            parent_xform = imageable.ComputeParentToWorldTransform(self.__time_code)
            if not local_xform:
                world_xform = imageable.ComputeLocalToWorldTransform(self.__time_code)
                local_xform = world_xform * parent_xform.GetInverse()
            if not world_xform:
                world_xform = parent_xform * local_xform
            return local_xform, parent_xform, world_xform, prim

        carb.log_warn(f"Framing of UsdPrims failed, {self.__prim_to_move} isn't UsdGeom.Xformable or UsdGeom.Imageable")
        return None, None, None, None

    def __calculate_distance(self, radius, prim):
        camera = UsdGeom.Camera(prim)
        h_fov_rad, v_fov_rad = self.__horizontal_fov, self.__horizontal_fov
        if camera:
            focalLength = camera.GetFocalLengthAttr()
            h_aperture = camera.GetHorizontalApertureAttr()
            v_aperture = camera.GetVerticalApertureAttr()
            if focalLength and (h_aperture or v_aperture):
                focalLength = focalLength.Get(self.__time_code)
                if h_aperture and not v_aperture:
                    v_aperture = h_aperture
                elif v_aperture and not h_aperture:
                    h_aperture = v_aperture
                h_aperture = h_aperture.Get(self.__time_code)
                v_aperture = v_aperture.Get(self.__time_code)

                if camera.GetProjectionAttr().Get(self.__time_code) == "orthographic":
                    new_horz_ap = (max(0.001, radius) / Gf.Camera.APERTURE_UNIT) * 2.0
                    if new_horz_ap != h_aperture:
                        new_vert_ap = v_aperture * ((new_horz_ap / h_aperture) if h_aperture else new_horz_ap)
                        return (new_horz_ap, new_vert_ap), (h_aperture, v_aperture)

                # Real fov's are 2x these, but only need the half for triangle calculation
                h_fov_rad = math.atan(
                    (h_aperture * Gf.Camera.APERTURE_UNIT) / (2.0 * focalLength * Gf.Camera.FOCAL_LENGTH_UNIT)
                )
                v_fov_rad = math.atan(
                    (v_aperture * Gf.Camera.APERTURE_UNIT) / (2.0 * focalLength * Gf.Camera.FOCAL_LENGTH_UNIT)
                )

        def fit_horizontal():
            if self.__use_horizontal_fov is not None:
                return self.__use_horizontal_fov
            conform = carb.settings.get_settings().get("/app/hydra/aperture/conform")
            if conform == 0 or conform == "vertical":
                return False

            is_fit = conform == 2 or conform == "fit"
            if is_fit or (conform == 3 or conform == "crop"):
                fov_aspect = h_fov_rad / v_fov_rad
                return not (is_fit ^ (fov_aspect > self.__aspect_ratio))
            return True

        if fit_horizontal():
            v_fov_rad = h_fov_rad / self.__aspect_ratio
        else:
            h_fov_rad = v_fov_rad * self.__aspect_ratio

        # Calculate the distance to encompass radius from the fovs
        dist = radius / math.tan(min(h_fov_rad, v_fov_rad))
        return (dist, dist), False

    def do(self):
        # Prims to frame bounds can be slightly more expensive than this, so validate we can move what was requested first
        usd_context = ou.get_context(self.__usd_context_name)
        stage = usd_context.get_stage()
        local_xform, parent_xform, world_xform, prim = self.__compute_local_transform(stage)
        if not prim:
            return False

        aabbox = Gf.Range3d()
        if len(self.__points) > 0:
            range_max = Gf.Vec3d(self.__points[0])
            range_min = Gf.Vec3d(self.__points[0])
            for i in range(len(self.__points) - 1):
                point = self.__points[i + 1]
                range_max[0] = max(range_max[0], point[0])
                range_max[1] = max(range_max[1], point[1])
                range_max[2] = max(range_max[2], point[2])
                range_min[0] = min(range_min[0], point[0])
                range_min[1] = min(range_min[1], point[1])
                range_min[2] = min(range_min[2], point[2])
            aabbox.UnionWith(Gf.Range3d(range_min, range_max))

        if aabbox.IsEmpty():
            carb.log_warn(f"Framing of UsdPrims {self.__prims_to_frame} resulted in an empty bounding-box")
            return

        if True:
            # Orient the aabox to the camera
            target = aabbox.GetMidpoint()
            tr0 = Gf.Matrix4d().SetTranslate(-target)
            local_rot = Gf.Matrix4d().SetRotate(local_xform.GetOrthonormalized().ExtractRotationQuat())
            tr1 = Gf.Matrix4d().SetTranslate(target)
            # And compute the new range
            aabbox = Gf.BBox3d(aabbox, tr0 * local_rot * tr1).ComputeAlignedRange()
        # Compute where to move in the parent space
        aabbox = Gf.BBox3d(aabbox, parent_xform.GetInverse()).ComputeAlignedRange()
        # Target is in parent-space (just like the camera / object we're moving)
        target = aabbox.GetMidpoint()
        # Frame against the aabox's bounding sphere
        radius = aabbox.GetSize().GetLength() * self.__zoom

        # TODO: Get rid of some of this complication due to Viewport-1
        values, ortho_props = self.__calculate_distance(radius, prim)
        prim_path = prim.GetPath()

        # For perspective, we really need the eye (it's translation)
        # For ortho, only needed to get coi (length to target)
        eye_dir = Gf.Vec3d(0, 0, values[0] if not ortho_props else 50000)
        eye = target + local_xform.TransformDir(eye_dir)

        # Mark center-of-interest accordingly (just length from target in local-space)
        coi_value = Gf.Vec3d(0, 0, -(eye - target).GetLength())
        coi_attr_name = "omni:kit:centerOfInterest"
        coi_attr = prim.GetAttribute(coi_attr_name)
        if not coi_attr:
            prev_coi = coi_value
            self.__created_property = True
        else:
            prev_coi = coi_attr.Get()

        commands.execute(
            "ChangePropertyCommand",
            prop_path=prim_path.AppendProperty(coi_attr_name),
            value=coi_value,
            prev=prev_coi,
            type_to_create_if_not_exist=Sdf.ValueTypeNames.Vector3d,
            usd_context_name=self.__usd_context_name,
            is_custom=True,
            variability=Sdf.VariabilityUniform,
        )

        if ortho_props:
            # Using time here causes issues with Viewport-1, so use default time for now
            time = self.__time_code if False else Usd.TimeCode.Default()
            commands.execute(
                "ChangePropertyCommand",
                prop_path=prim_path.AppendProperty("horizontalAperture"),
                value=values[0],
                prev=ortho_props[0],
                timecode=time,
                usd_context_name=self.__usd_context_name,
            )
            commands.execute(
                "ChangePropertyCommand",
                prop_path=prim_path.AppendProperty("verticalAperture"),
                value=values[1],
                prev=ortho_props[1],
                timecode=time,
                usd_context_name=self.__usd_context_name,
            )

        new_local_xform = Gf.Matrix4d(local_xform)
        new_local_xform.SetTranslateOnly(eye)

        had_transform_at_key = False
        had_matrix = False
        if not self.__time_code.IsDefault():
            xformable = UsdGeom.Xformable(prim)
            if xformable:
                for xform_op in xformable.GetOrderedXformOps():
                    had_matrix = xform_op.GetOpType() == UsdGeom.XformOp.TypeTransform
                    had_transform_at_key = had_transform_at_key or (xform_op.GetNumTimeSamples() > 0)

        if had_matrix:
            commands.execute(
                "TransformPrimCommand",
                path=self.__prim_to_move,
                new_transform_matrix=new_local_xform,
                old_transform_matrix=local_xform,
                time_code=self.__time_code,
                had_transform_at_key=had_transform_at_key,
                usd_context_name=self.__usd_context_name,
            )
        else:
            commands.execute(
                "TransformPrimSRTCommand",
                path=self.__prim_to_move,
                new_translation=new_local_xform.Transform(Gf.Vec3d(0, 0, 0)),
                time_code=self.__time_code,
                had_transform_at_key=had_transform_at_key,
                usd_context_name=self.__usd_context_name,
            )

    def undo(self):
        if not self.__created_property:
            return
        usd_context = ou.get_context(self.__usd_context_name)
        stage = usd_context.get_stage()
        if not stage:
            return
        prim = stage.GetPrimAtPath(self.__prim_to_move)
        if not prim:
            return
        prim.RemoveProperty("omni:kit:centerOfInterest")
        self.__created_property = False


class _RestoreMeasurementOnUndo(omni.kit.commands.Command):
    """
    Restore measurements on undo. (Does nothing on do or redo.)

    This command is for internal use only. It may be changed or removed
    without notice.

    Args:
        measurements (List[(str, str)])
            The measurements to be restored.
    """

    # When the source prim for a connection is deleted OG removes all traces of the
    # connection. If the deletion is undone OG has no way of knowing that the restored
    # prim had a connection which should also be restored. This command is used to
    # restore those connections on undo.
    def __init__(self, measurements: List[MeasurePrim]):
        self._measurements: List[MeasurePrim] = measurements.copy()
        self.__recreate_task = None
        self._remove_command = []

    def destroy(self):
        if self.__recreate_task:
            if not self.__recreate_task.done():
                self.__recreate_task.cancel()
            self.__recreate_task = None

    def do(self):
        for measurement in self._measurements:
            command = RemoveMeasurementCommand(measurement)
            self._remove_command.append(command)
            command.do()

    def undo(self):
        # We cannot do the reconnection yet because prim delete won't have created the prim's yry
        if self.__recreate_task is None or self.__recreate_task.done():
            self.__recreate_task = asyncio.ensure_future(self.__do_recreate())

    async def __do_recreate(self):
        # Give OG a chance to create the prim's Node.
        await omni.kit.app.get_app().next_update_async()

        for command in self._remove_command:
            command.undo()
        self.__recreate_task = None


def register() -> None:
    commands.register(_RestoreMeasurementOnUndo)
    commands.register(CreateMeasurementCommand)
    commands.register(RemoveMeasurementCommand)


def unregister() -> None:
    commands.unregister(_RestoreMeasurementOnUndo)
    commands.unregister(CreateMeasurementCommand)
    commands.unregister(RemoveMeasurementCommand)

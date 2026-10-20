import sys
from pathlib import Path

import carb
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import frame_viewport_selection
from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils

CAMERA_FOV_PATH = "/persistent/exts/omni.kit.viewport.navigation.camera_manipulator/fov"
CAMERA_PATH = "/OmniverseKit_Persp"
BBOX_OFFSET = 1000
DOUBLE_MAX = sys.float_info.max


def navigation_frame():
    frame_viewport_selection()


def get_icon_path(filename: str) -> str:
    ext_path = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
    return ext_path.joinpath("icons").joinpath(filename).as_posix()


# OMFP-2306: set the perspective camera focal length to 8mm
def set_camera_fov(*arg):
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(CAMERA_PATH)
    if prim:
        attr = prim.GetAttribute("focalLength")
        if attr:
            with Usd.EditContext(stage, stage.GetSessionLayer()):
                fov = carb.settings.get_settings().get(CAMERA_FOV_PATH)
                if fov is not None:
                    attr.Set(fov)


def _as_range3d(usdrt, val):
    """The _worldExtent value as a usdrt.Gf.Range3d.

    Fabric's usdrt returns a Gf.Range3d. The OVStage-backed usdrt of Kit 111 returns the same extent as plain
    (min, max) values, so convert it; anything else is treated as no extent.
    """
    if val is None or isinstance(val, usdrt.Gf.Range3d):
        return val
    try:
        values = list(val)
        if len(values) == 2:
            lo, hi = values
        elif len(values) == 6:
            lo, hi = values[:3], values[3:]
        else:
            carb.log_warn(f"fit_camera: _worldExtent has an unexpected shape ({len(values)} values); ignoring it")
            return None
        return usdrt.Gf.Range3d(usdrt.Gf.Vec3d(*lo), usdrt.Gf.Vec3d(*hi))
    except (TypeError, ValueError) as error:
        carb.log_warn(f"fit_camera: _worldExtent value {type(val).__name__} is not a range ({error}); ignoring it")
        return None


# OMFP-2890:
# If camera is outside the scene bounds - bring it back in and make it look at the center of the scene.
# Run this only if USDRT is available and Fabric is populated. USD bounds compute is too expensive.
def fit_camera():
    try:
        import usdrt
    except:
        return False

    stage = omni.usd.get_context().get_stage()

    # Get the scene bounds from Fabric.
    idx = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
    usdrt_stage = usdrt.Usd.Stage.Attach(idx)
    if not usdrt_stage:
        return False

    usdrt_bbox = usdrt.Gf.Range3d()
    for usd_prim in stage.GetPrimAtPath("/").GetChildren():
        _type = usd_prim.GetTypeName()
        if _type == "Xform" and _type != "Camera" and "Environment" not in str(usd_prim.GetName()):
            usdrt_path = usdrt.Sdf.Path(str(usd_prim.GetPrimPath()))
            if usdrt_prim := usdrt_stage.GetPrimAtPath(usdrt_path):
                if usdrt_attr := usdrt_prim.GetAttribute("_worldExtent"):
                    val = _as_range3d(usdrt, usdrt_attr.Get())
                    if val is not None and not val.IsEmpty():
                        usdrt_bbox.UnionWith(val)

    _min = usdrt_bbox.GetMin()
    _max = usdrt_bbox.GetMax()
    # USDRT started returning big values for bounding boxes with 0 size
    if _min[0] == DOUBLE_MAX:
        _min[0] = 0
    if _min[1] == DOUBLE_MAX:
        _min[1] = 0
    if _min[2] == DOUBLE_MAX:
        _min[2] = 0
    if _max[0] == -DOUBLE_MAX:
        _max[0] = 0
    if _max[1] == -DOUBLE_MAX:
        _max[1] = 0
    if _max[2] == -DOUBLE_MAX:
        _max[2] = 0
    _offset = usdrt.Gf.Vec3d(BBOX_OFFSET, BBOX_OFFSET, BBOX_OFFSET)
    _min -= _offset
    _max += _offset

    # compute positional offset
    outside = False
    prim = stage.GetPrimAtPath(CAMERA_PATH)
    mtx = UsdGeom.XformCache(Usd.TimeCode(0)).GetLocalToWorldTransform(prim)
    pos = mtx.ExtractTranslation()
    for i in range(3):
        if pos[i] < _min[i]:
            pos[i] = _min[i]
            outside = True
        elif pos[i] > _max[i]:
            pos[i] = _max[i]
            outside = True

    # adjust the perspective camera transformation matrix
    if outside:
        mtx = mtx.SetTranslateOnly(pos)
        with Usd.EditContext(stage, stage.GetSessionLayer()):
            UsdGeom.Xformable(prim).MakeMatrixXform().Set(mtx)
        ctr = usdrt_bbox.GetMidpoint()
        aim = Gf.Vec3d(ctr[0], ctr[1], ctr[2])
        unroll_camera(aim=aim)

    return True


def unroll_camera(aim=None):
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(CAMERA_PATH)
    if prim:
        mtx = UsdGeom.XformCache(Usd.TimeCode(0)).GetLocalToWorldTransform(prim)
        pos = mtx.ExtractTranslation()
        if not aim:
            aim = mtx.Transform(Gf.Vec3d(0, 0, -1))
        up = omni.usd.get_context().get_stage().GetMetadata("upAxis")
        up = Gf.Vec3d(0, 0, 1) if up == "Z" else Gf.Vec3d(0, 1, 0)
        mtx = mtx.SetLookAt(pos, aim, up).GetInverse().SetTranslateOnly(pos)
        with Usd.EditContext(stage, stage.GetSessionLayer()):
            UsdGeom.Xformable(prim).MakeMatrixXform().Set(mtx)

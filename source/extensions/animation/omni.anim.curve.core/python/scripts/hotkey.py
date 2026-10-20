# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["Hotkey"]

import omni.appwindow
from pxr import UsdGeom


# Add Transform Keys for the hotkey S
def anim_hotkey_callback():
    prim_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
    stage = omni.usd.get_context().get_stage()
    if not stage or not prim_paths or len(prim_paths) == 0:
        return
    keyable_xform_attr_names = [
        "xformOp:translate",
        "xformOp:rotateX",
        "xformOp:rotateY",
        "xformOp:rotateZ",
        "xformOp:rotateXYZ",
        "xformOp:rotateXZY",
        "xformOp:rotateYXZ",
        "xformOp:rotateYZX",
        "xformOp:rotateZXY",
        "xformOp:rotateZYX",
        "xformOp:scale",
        "visibility",
    ]
    curve_names = []
    for path in prim_paths:
        if path is not None:
            prim = stage.GetPrimAtPath(path)
            if prim and prim.IsA(UsdGeom.Xformable):
                for attr_name in keyable_xform_attr_names:
                    attr = prim.GetAttribute(attr_name)
                    if attr:
                        curve_names.append(attr.GetPath().pathString)
    if len(curve_names) > 0:
        omni.kit.commands.execute("SetAnimCurveKeys", paths=curve_names)

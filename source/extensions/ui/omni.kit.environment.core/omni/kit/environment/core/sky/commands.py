# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
from typing import Any, Dict, List, Optional

import carb
import omni.kit.commands
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux

from ..constants import ENVIRONMENT_PRIM_ROOT, EnvironmentProperties


class CreateDynamicSkyCommand(omni.kit.commands.Command):
    """
    Create dynamic sky undoable **Command**.

    Args:
        sky_url (str): Url of sky
        sky_path (str): Prim path to create sky
    """

    def __init__(self, sky_url: str, sky_path: str):
        self._sky_url = sky_url
        self._sky_path = sky_path

    def do(self):
        stage = omni.usd.get_context().get_stage()
        sky_prim = stage.DefinePrim(self._sky_path, "Xform")
        if sky_prim:
            sky_prim.GetReferences().AddReference(self._sky_url)
            upAxis = UsdGeom.GetStageUpAxis(stage)
            if upAxis == "Z":
                self._set_sky_rotation(sky_prim, Gf.Vec3d(90, 0, 0))
            else:
                self._set_sky_rotation(sky_prim, Gf.Vec3d(0, 0, 0))
        else:
            carb.log_warn(f"failed to create prim {self._sky_path}")

    def undo(self):
        stage = omni.usd.get_context().get_stage()
        sky_prim = stage.GetPrimAtPath(self._sky_path)
        if sky_prim:
            omni.usd.commands.DeletePrimsCommand([sky_prim.GetPath().pathString]).do()

    def _set_sky_rotation(self, prim, rot):
        properties = prim.GetPropertyNames()
        if "xformOp:rotateXYZ" in properties:
            rotation = prim.GetAttribute("xformOp:rotateXYZ")
            rotation.Set(rot)
        elif "xformOp:rotateZYX" in properties:
            rotation = prim.GetAttribute("xformOp:rotateZYX")
            rotation.Set(rot)
        elif "xformOp:transform" in properties:
            carb.log_info("Object missing rotation op. Adding it.")
            xform = UsdGeom.Xformable(prim)
            xform_op = xform.AddXformOp(UsdGeom.XformOp.TypeRotateXYZ, UsdGeom.XformOp.PrecisionDouble, "")
            rotate = Gf.Vec3d(rot[0], rot[1], rot[2])
            xform_op.Set(rotate)


class CreateHdriSkyCommand(omni.kit.commands.Command):
    """
    Create hdri sky undoable **Command**.

    Args:
        sky_url (str): Url of sky
        sky_path (str): Prim path to create sky
    """

    def __init__(self, sky_url: str, sky_path: str):
        self._sky_url = sky_url
        self._sky_path = sky_path

    def do(self):
        with omni.kit.undo.group():
            if hasattr(UsdLux.Tokens, "inputsIntensity"):
                omni.kit.commands.execute(
                    "CreatePrimCommand",
                    prim_path=self._sky_path,
                    prim_type="DomeLight",
                    select_new_prim=False,
                    attributes={
                        UsdLux.Tokens.inputsIntensity: 1000,
                        UsdLux.Tokens.inputsSpecular: 1,
                        UsdLux.Tokens.inputsTextureFile: self._sky_url,
                        UsdLux.Tokens.inputsTextureFormat: UsdLux.Tokens.latlong,
                        UsdGeom.Tokens.visibility: "inherited",
                    },
                )
            else:
                omni.kit.commands.execute(
                    "CreatePrimCommand",
                    prim_path=self._sky_path,
                    prim_type="DomeLight",
                    select_new_prim=False,
                    attributes={
                        UsdLux.Tokens.intensity: 1000,
                        UsdLux.Tokens.specular: 1,
                        UsdLux.Tokens.textureFile: self._sky_url,
                        UsdLux.Tokens.textureFormat: UsdLux.Tokens.latlong,
                        UsdGeom.Tokens.visibility: "inherited",
                    },
                )

            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(self._sky_path)
            if prim:
                attributes = {
                    "shaping:cone:angle": 180,
                    "shaping:focusTint": Gf.Vec3f(0, 0, 0),
                    "shaping:focus": 0,
                }
                for name in attributes:
                    attr = prim.GetAttribute(name)
                    if attr:
                        attr.Set(attributes[name])

                # OM-41370: Default enable "visible in primary Ray"
                omni.kit.commands.execute(
                    "ChangePropertyCommand",
                    prop_path=f"{self._sky_path}.visibleInPrimaryRay",
                    value=True,
                    prev=True,
                    type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
                )

                if self._get_usdlux_version(prim) >= 2505:
                    up_axis = UsdGeom.GetStageUpAxis(stage)
                    rot = Gf.Vec3d(270, 0, 0) if up_axis == "Y" else Gf.Vec3d(90, 0, 0)
                    self._set_sky_rotation(prim, rot)

    def undo(self):
        pass

    def _get_usdlux_version(self, prim: Usd.Prim) -> int:
        attr = prim.GetAttribute("omni:rtx:usdluxVersion")
        if attr and attr.HasValue():
            try:
                v = attr.Get()
                return int(v) if isinstance(v, (int, float)) else 2411
            except Exception:
                pass
        return 2411

    def _set_sky_rotation(self, prim, rot):
        properties = prim.GetPropertyNames()
        if "xformOp:rotateXYZ" in properties:
            rotation = prim.GetAttribute("xformOp:rotateXYZ")
            rotation.Set(rot)
        elif "xformOp:rotateZYX" in properties:
            rotation = prim.GetAttribute("xformOp:rotateZYX")
            rotation.Set(rot)
        elif "xformOp:transform" in properties:
            carb.log_info("Object missing rotation op. Adding it.")
            xform = UsdGeom.Xformable(prim)
            xform_op = xform.AddXformOp(UsdGeom.XformOp.TypeRotateXYZ, UsdGeom.XformOp.PrecisionDouble, "")
            rotate = Gf.Vec3d(rot[0], rot[1], rot[2])
            xform_op.Set(rotate)


omni.kit.commands.register_all_commands_in_module(__name__)

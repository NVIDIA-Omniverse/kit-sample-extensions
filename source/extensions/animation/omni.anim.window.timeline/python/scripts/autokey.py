# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import List

import omni.anim.curve.core
import omni.kit.commands
import omni.timeline
import omni.usd
from pxr import Sdf

from .utils import add_xform_keys, get_auto_key_all_xform

# An animation key will be automatically added after followed commands executed
# - TransformMultiPrimsSRTCpp
# - ChangeProperty
# - ToggleVisibilitySelectedPrims
# - TransformPrimSRT


class CommandCallbackBase:
    def __init__(self, command_name: str, callback_type):
        self._id = omni.kit.commands.register_callback(command_name, callback_type, self._callback)

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._id:
            omni.kit.commands.unregister_callback(self._id)
            self._id = None

    def _callback(self, info):
        pass


class TransformMultiPrimsSRTCppWatcher(CommandCallbackBase):
    def __init__(self):
        super().__init__("TransformMultiPrimsSRTCpp", omni.kit.commands.POST_DO_CALLBACK)

    def _callback(self, info):
        # Get the command's 'paths' argument.
        paths: List[str] = info.get("paths", None)
        if not paths:
            return

        update_attrs = []
        if info.get("new_translations", None):
            update_attrs.append("xformOp:translate")

        if info.get("new_rotation_eulers", None):
            update_attrs.append("xformOp:rotateX")
            update_attrs.append("xformOp:rotateY")
            update_attrs.append("xformOp:rotateZ")
            update_attrs.append("xformOp:rotateXYZ")
            update_attrs.append("xformOp:rotateXZY")
            update_attrs.append("xformOp:rotateYXZ")
            update_attrs.append("xformOp:rotateYZX")
            update_attrs.append("xformOp:rotateZXY")
            update_attrs.append("xformOp:rotateZYX")

        if info.get("new_scales", None):
            update_attrs.append("xformOp:scale")

        AutoKeyGenerator.auto_keys(paths, update_attrs)


class ChangePropertyWatcher(CommandCallbackBase):
    def __init__(self):
        super().__init__("ChangeProperty", omni.kit.commands.POST_DO_CALLBACK)

    def _callback(self, info):
        # Get the command's 'prop_path' argument.
        prop_path: Sdf.Path = info.get("prop_path", None)
        if not prop_path:
            return

        AutoKeyGenerator.auto_keys([prop_path.GetPrimPath().pathString], [prop_path.name])


class ToggleVisibilitySelectedPrimsWatcher(CommandCallbackBase):
    def __init__(self):
        super().__init__("ToggleVisibilitySelectedPrims", omni.kit.commands.POST_DO_CALLBACK)

    def _callback(self, info):
        selected_paths: List[str] = info.get("selected_paths", None)
        if not selected_paths:
            return

        AutoKeyGenerator.auto_keys(selected_paths, ["visibility"])


class TransformPrimSRTWatcher(CommandCallbackBase):
    def __init__(self):
        super().__init__("TransformPrimSRT", omni.kit.commands.POST_DO_CALLBACK)

    def _callback(self, info):
        path = info.get("path", None)
        if not path:
            return

        if isinstance(path, Sdf.Path):
            path = path.pathString

        update_attrs = []
        if info.get("new_translation", None):
            update_attrs.append("xformOp:translate")

        if info.get("new_rotation_euler", None):
            update_attrs.append("xformOp:rotateX")
            update_attrs.append("xformOp:rotateY")
            update_attrs.append("xformOp:rotateZ")
            update_attrs.append("xformOp:rotateXYZ")
            update_attrs.append("xformOp:rotateXZY")
            update_attrs.append("xformOp:rotateYXZ")
            update_attrs.append("xformOp:rotateYZX")
            update_attrs.append("xformOp:rotateZXY")
            update_attrs.append("xformOp:rotateZYX")

        if info.get("new_scale", None):
            update_attrs.append("xformOp:scale")

        AutoKeyGenerator.auto_keys([path], update_attrs)


class AutoKeyGenerator:
    def __init__(self):
        self._transform_watcher = TransformMultiPrimsSRTCppWatcher()
        self._property_watcher = ChangePropertyWatcher()
        self._visiblity_watcher = ToggleVisibilitySelectedPrimsWatcher()
        self._camera_watcher = TransformPrimSRTWatcher()

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._transform_watcher:
            self._transform_watcher.destroy()
            self._transform_watcher = None
        if self._property_watcher:
            self._property_watcher.destroy()
            self._property_watcher = None
        if self._visiblity_watcher:
            self._visiblity_watcher.destroy()
            self._visiblity_watcher = None
        if self._camera_watcher:
            self._camera_watcher.destroy()
            self._camera_watcher = None

    @staticmethod
    def auto_keys(changed_prim_paths: List[str], changed_attrs: List[str]):
        key_attrs = []
        curved_prim_paths = []
        curve_plugin = omni.anim.curve.core.acquire_interface()

        # only update exist curve, so check if the changed path is exist curve
        for prim_path in changed_prim_paths:
            curves = curve_plugin.get_curves(prim_path)
            if not curves:
                continue

            curved_prim_paths.append(prim_path)
            curve_tokens = curves.keys()

            for attr_name in changed_attrs:
                if attr_name in curve_tokens:
                    key_attrs.append(prim_path + "." + attr_name)
                else:
                    if attr_name + ":x" in curve_tokens:
                        key_attrs.append(prim_path + "." + attr_name + "|x")
                    if attr_name + ":y" in curve_tokens:
                        key_attrs.append(prim_path + "." + attr_name + "|y")
                    if attr_name + ":z" in curve_tokens:
                        key_attrs.append(prim_path + "." + attr_name + "|z")
                    if attr_name + ":w" in curve_tokens:
                        key_attrs.append(prim_path + "." + attr_name + "|w")

        if len(key_attrs) > 0:
            omni.kit.commands.execute("SetAnimCurveKeys", paths=key_attrs)

        if get_auto_key_all_xform():
            stage = omni.usd.get_context().get_stage()
            add_xform_keys(curved_prim_paths, stage)

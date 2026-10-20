# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb
from pxr import Sdf, Usd, UsdGeom, UsdShade


# This is a placeholder for Usd.Attribute as that class cannot be created unless attached to a prim
class PlaceholderAttribute:
    def __init__(
        self,
        name,
        prim: Usd.Prim = None,
        value_type_name: Sdf.ValueTypeName = None,
        metadata=None,
    ):
        self._name = name
        self._prim = prim
        self._value_type_name = value_type_name
        self._metadata = metadata if metadata else {}

    def Get(self, time_code=0):
        if self._metadata:
            custom_data = self._metadata.get("customData")
            if custom_data is not None and "default" in custom_data:
                return custom_data["default"]

            type_name = self.GetTypeName()
            default = self._metadata.get("default")
            if default is not None:
                return default
            elif type_name:
                return type_name.defaultValue

        carb.log_warn("PlaceholderAttribute.Get() customData.default or default not found in metadata")
        return None

    def GetName(self):
        return self._name

    def GetPath(self):
        if self._prim:
            return self._prim.GetPath()
        return None

    def ValueMightBeTimeVarying(self):
        return False

    def GetMetadata(self, token):
        if token in self._metadata:
            return self._metadata[token]
        return False

    def GetAllMetadata(self):
        return self._metadata

    def GetPrim(self):
        return self._prim

    def GetTypeName(self) -> Sdf.ValueTypeName:
        if self._value_type_name:
            return self._value_type_name

        type_name_key = self._metadata.get(Sdf.PrimSpec.TypeNameKey)
        if not type_name_key:
            carb.log_warn("PlaceholderAttribute.CreateAttribute() error TypeNameKey")
            return None
        carb.log_warn(f"type_name_key = {type_name_key}")

        self._value_type_name = Sdf.ValueTypeNames.Find(type_name_key)

        return self._value_type_name

    def CreateAttribute(self, set_default_value: bool = True):
        try:
            if not self._name:
                carb.log_warn("PlaceholderAttribute.CreateAttribute() error no attribute name")
                return None

            if not self._prim:
                carb.log_warn("PlaceholderAttribute.CreateAttribute() error no target prim")
                return None

            type_name = self.GetTypeName()

            if self._name.startswith("primvars:"):
                pv = UsdGeom.PrimvarsAPI(self._prim)
                attribute = UsdGeom.PrimvarsAPI(self._prim).CreatePrimvar(self._name[9:], type_name).GetAttr()
            elif self._prim.GetTypeName() == "Shader":
                shader = UsdShade.Shader(self._prim)
                sdr_shader_node = shader.GetShaderNodeForSourceType("mdl")
                sdr_shader_property = (
                    sdr_shader_node.GetShaderInput(self._name)
                    if sdr_shader_node and hasattr(sdr_shader_node, "GetShaderInput")
                    else None
                )
                if not sdr_shader_property:
                    raise RuntimeError(
                        f'Shader node has no input "{self._name}" (OmniSdrShaderNode uses GetShaderInput)'
                    )
                ndr_sdr_type_indicator = sdr_shader_property.GetTypeAsSdfType()
                property_type_name = Sdf.ValueTypeNames.Find(ndr_sdr_type_indicator[1]) or ndr_sdr_type_indicator[0]
                attribute = shader.CreateInput(self._name, property_type_name).GetAttr()
            else:
                attribute = self._prim.CreateAttribute(self._name, type_name, custom=False)

            filter = {"customData", "displayName", "displayGroup", "documentation"}
            filter = {}
            if attribute:
                for key in self._metadata:
                    if key not in filter:
                        attribute.SetMetadata(key, self._metadata[key])
                if set_default_value:
                    attribute.Set(self.Get())
                    carb.log_warn("Placeholder Attribute Set/Get")
                    carb.log_warn(f"Attribute = {attribute}")
                    carb.log_warn(f"value = {self.Get()}")

            return attribute
        except Exception as exc:
            carb.log_warn(f"PlaceholderAttribute.CreateAttribute() error {exc}")
        return None

    def HasAuthoredConnections(self):
        return False

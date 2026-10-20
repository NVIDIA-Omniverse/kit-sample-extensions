# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pprint import pprint
from typing import List, Optional, Tuple, Union

import omni.ui as ui
from pxr import Sdf, Usd, Vt

from ..prims import PRIM_NS
from ..properties.prim_properties import ATTR_NS, prim_properties, prim_style_properties
from ..properties.property_enums import (
    PropertyMode,
    PropertyType,
    StylePropertyType,
    get_property_enum_options,
    get_style_property_enum_options,
)
from .valid import valid_selector_states, valid_ui_prim_types


def get_sdf_type_name(property_type: Union[PropertyType, StylePropertyType]):
    typename = property_type.name

    # temporary typehacks until handled more directly
    if typename in ["LENGTH"]:
        typename = "FLOAT"
    elif typename in ["CALLABLE"]:
        typename = "STRING"
    elif typename in ["ENUM"]:
        typename = "TOKEN"
    elif typename in ["COLOR"]:
        typename = "COLOR4F"

    for name in dir(Sdf.ValueTypeNames):
        value_type_name = getattr(Sdf.ValueTypeNames, name)
        if str(value_type_name).lower() == typename.lower():
            return value_type_name
    return None  # Usd.Relationship


def remove_property_as_usd_attribute(prim: Usd.Prim, attr_name: str):
    if prim.HasAttribute(attr_name):
        prim.RemoveProperty(attr_name)


def create_property_as_usd_attribute(
    prim: Usd.Prim,
    attr_name: str,
    property_name: str,
    property_type: Union[PropertyType, StylePropertyType],
    property_default: Optional[Union[str, float, int, bool]],
    property_mode: PropertyMode = PropertyMode.RW,
):
    if prim.HasAttribute(attr_name):
        return
    attr: Usd.Attribute
    type_name = get_sdf_type_name(property_type)
    if type_name is None and property_type.name == "RELATIONSHIP":
        attr = prim.CreateRelationship(attr_name, custom=True)  # type: ignore
    else:
        attr = prim.CreateAttribute(
            name=attr_name, typeName=type_name, custom=True, variability=Sdf.VariabilityVarying
        )  # type: ignore
        if property_default and not property_mode == PropertyMode.RO:
            attr.SetCustomDataByKey("default", property_default)
            attr.ClearDefault()
            attr.Set(property_default)  # Even through we reset to default, set is needed for model to receive it
    if property_type.name == "COLOR":
        attr.SetCustomDataByKey("default", (1.0, 1.0, 1.0, 1.0))
        attr.ClearDefault()
        attr.Set((1.0, 1.0, 1.0, 1.0))
    if property_type.name == "ENUM":
        # Default option would be first from the list at the moment
        if isinstance(property_type, StylePropertyType):
            options = get_style_property_enum_options(property_name)
        else:
            options = get_property_enum_options(property_name)
        enum_list = Vt.TokenArray(options)
        attr.SetMetadata("allowedTokens", enum_list)


class PropertyBearingWidgetMeta(type):
    def __init_properties__(cls) -> tuple[dict[str, dict], dict[str, dict]]:
        properties = {cls.__name__: prim_properties.get(cls.__name__, {})}
        style_properties = {cls.__name__: prim_style_properties.get(cls.__name__, {})}
        for typ in cls.mro():
            properties.update({typ.__name__: prim_properties.get(typ.__name__, {})})
            style_properties.update({typ.__name__: prim_style_properties.get(typ.__name__, {})})

        return properties, style_properties


class PropertyBearingWidget(metaclass=PropertyBearingWidgetMeta):
    _prim_type: str
    _properties: dict[str, dict]
    _style_properties: dict[str, dict[str, object]]

    def __init__(self, prim: Usd.Prim):
        self._properties, self._style_properties = type(self).__init_properties__()
        self._prim = prim
        self._prim_type = prim.GetTypeName()  # type: ignore
        self._prim_attrs = []

    def create_properties(self):
        self.properties = {}
        if self._prim_type == f"{PRIM_NS}Style":
            self.create_style_prim_metadata()
        if not self._prim_type.startswith(f"{PRIM_NS}Style"):
            self.create_default_style_binding()
        for cls in type(self).mro():
            for property_name, property_settings in self._properties.get(cls.__name__, {}).items():
                self.create_property(cls.__name__, property_settings, property_name)

    def create_style_prim_metadata(self):
        name_type = {
            "type_name": get_sdf_type_name(PropertyType.ENUM),
            "name": get_sdf_type_name(PropertyType.STRING),
            "state": get_sdf_type_name(PropertyType.ENUM),
        }
        attr: Usd.Attribute
        if self._prim:
            for attrname, type_name in name_type.items():
                attr_fullname = f"{ATTR_NS}:StyleSelector:{attrname}"
                if self._prim.HasAttribute(attr_fullname):
                    continue
                attr = self._prim.CreateAttribute(
                    name=attr_fullname, typeName=type_name, custom=True, variability=Sdf.VariabilityVarying
                )  # type: ignore
                if attrname == "type_name":
                    options = ("",) + tuple(valid_ui_prim_types) + ("Button.Label", "Button.Image")
                    enum_list = Vt.TokenArray(options)
                    attr.SetMetadata("allowedTokens", enum_list)
                elif attrname == "state":
                    options = ("",) + tuple(valid_selector_states)
                    enum_list = Vt.TokenArray(options)
                    attr.SetMetadata("allowedTokens", enum_list)

                attr.SetCustomDataByKey("default", "")
                attr.ClearDefault()
                attr.Set("")
                self._prim_attrs.append(attr)

    def create_default_style_binding(self):
        if self._prim:
            attr = create_property_as_usd_attribute(
                self._prim, f"{ATTR_NS}:Style:binding", "binding", StylePropertyType.RELATIONSHIP, None
            )
            self._prim_attrs.append(attr)

    def create_property(
        self,
        property_source_name: str,
        property_settings: Tuple[PropertyType, PropertyMode, Union[str, float, int, bool]],
        property_name: str,
    ):
        attr_name = f"{ATTR_NS}:{property_source_name}:{property_name}"
        property_type, _, property_default = property_settings

        if self._prim:
            attr = create_property_as_usd_attribute(
                self._prim, attr_name, property_name, property_type, property_default
            )
            self._prim_attrs.append(attr)

    def allows_style_property(self, property_name: str) -> bool:
        if self._prim_type == f"{PRIM_NS}Style" and property_name != "binding":
            return True
        return any(property_name in style_properties for style_properties in self._style_properties.values())

    def backing_property_type(self, property_name: str):
        for cls in type(self).mro():
            if widget_properties := self._properties.get(cls.__name__, {}):
                if widget_property := widget_properties.get(property_name, None):
                    return widget_property[0]
        return None


# Types outside of the `omni.ui` module.
# Only have properties from themselves currently.
property_bearing_widget_classes: dict[str, PropertyBearingWidgetMeta] = {
    "ViewportButton": PropertyBearingWidgetMeta("ViewportButton", (PropertyBearingWidget,), {}),
    "ViewportCircle": PropertyBearingWidgetMeta("ViewportCircle", (PropertyBearingWidget,), {}),
    "StyleContainer": PropertyBearingWidgetMeta("StyleContainer", (PropertyBearingWidget,), {}),
}

# Use actual omni.ui module structure and widget hierarchy to automatically construct the a class hierarchy of widgets
for prim_type in valid_ui_prim_types:
    if prim_type in property_bearing_widget_classes:
        continue
    else:
        _obj = getattr(ui, prim_type)
        classes = [
            _cls.__name__ for _cls in reversed(_obj.__mro__) if _cls.__name__ not in ["pybind11_object", "object"]
        ]
    bases: list[PropertyBearingWidgetMeta] = [PropertyBearingWidget]
    for _cls in classes:
        if _cls not in property_bearing_widget_classes:
            PropertyBearingWidgetClass = PropertyBearingWidgetMeta(_cls, tuple(reversed(bases)), {})
            property_bearing_widget_classes[_cls] = PropertyBearingWidgetClass
            bases.append(PropertyBearingWidgetClass)
        else:
            bases.append(property_bearing_widget_classes[_cls])


def get_property_class(prim_type: str, prim: Usd.Prim) -> PropertyBearingWidget:
    if prim_type not in property_bearing_widget_classes:
        raise Exception(f"No properties for prim_type {prim_type}")
    prim_type_properties = property_bearing_widget_classes[prim_type]
    prim_properties = prim_type_properties(prim)
    return prim_properties


# Called after creation of the prim of the appropriate type
def create_prim_properties(prim_type: str, prim: Usd.Prim):
    prim_properties = get_property_class(prim_type, prim)
    prim_properties.create_properties()


def prim_property_backing_type(prim_type: str, prim: Usd.Prim, property_name: str):
    prim_properties = get_property_class(prim_type, prim)
    return prim_properties.backing_property_type(property_name)

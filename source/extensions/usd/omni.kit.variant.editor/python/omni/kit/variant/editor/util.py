# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb
import omni.ui as ui
from pxr import Sdf, Usd

from .placeholder_attribute import PlaceholderAttribute


class AbstractValueModelDelegate:
    def __init__(self):
        pass

    def get_value_model(self, value, value_type=None):
        if value_type is None:
            value_type = type(value)
        if value_type == str or value_type == "string":
            return ui.SimpleStringModel(value)
        elif value_type == int or value_type == "int":
            return ui.SimpleIntModel(int(value))
        elif value_type == float or value_type == "float":
            return ui.SimpleFloatModel(float(value))
        elif value_type == bool or value_type == "bool":
            return ui.SimpleBoolModel(float(value))
        elif value_type == Sdf.Path or value_type == "Sdf.Path":
            return ui.SimpleStringModel(value.pathString)
        elif value_type == Sdf.ValueTypeName or value_type == "Sdf.ValueTypeName":
            return ui.SimpleStringModel(str(value))
        elif value_type == Usd.Attribute or value_type == "Usd.Attribute":
            return Usd.Attribute
        elif value_type == PlaceholderAttribute or value_type == "PlaceholderAttribute":
            return Usd.Attribute
        elif value_type == Usd.Relationship or value_type == "Usd.Relationship":
            return ui.SimpleStringModel(str(value))
        elif value_type == Sdf.Reference or value_type == "Sdf.Reference":
            return ui.SimpleStringModel(str(value))
        elif value_type == Sdf.Payload or value_type == "Sdf.Payload":
            return ui.SimpleStringModel(str(value))
        elif value_type == Sdf.Layer or value_type == "Sdf.Layer":
            return ui.SimpleStringModel(str(value))
        elif value_type == dict or value_type == "dict":
            return ui.SimpleStringModel(str(value))
        elif value_type == Sdf.RelationshipSpec or value_type == "Sdf.RelationshipSpec":
            return ui.SimpleStringModel(str(value))
        elif value_type == Sdf.AttributeSpec or value_type == "Sdf.AttributeSpec":
            return ui.SimpleStringModel(str(value))
        elif value_type == Usd.Object or value_type == "Usd.Object":
            return ui.SimpleStringModel(str(value))
        elif value_type == Usd.Property or value_type == "Usd.Property":
            return ui.SimpleStringModel(str(value))
        elif value_type == Usd.VariantSet or value_type == "Usd.VariantSet":
            return ui.SimpleStringModel(str(value))
        else:
            carb.log_error(f"Unknown value type {value_type}!")
            carb.log_error(f"Unknown value {value}!")
            return None


def get_ui_style():
    settings = carb.settings.get_settings()
    style = settings.get_as_string("/persistent/app/window/uiStyle")
    if not style:
        style = "NvidiaDark"
    return style


def get_payload_setting():
    settings = carb.settings.get_settings()
    payload_setting = settings.get_as_string("/persistent/app/stage/dragDropImport")
    if payload_setting == "payload":
        return True
    else:
        return False

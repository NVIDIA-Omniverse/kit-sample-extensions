# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import List, Sequence, Union

from pxr import Sdf, Usd

from ..prims import PRIM_NS
from ..properties.prim_properties import ATTR_NS
from ..properties.property_enums import get_style_property_type
from .prim_properties import (
    create_property_as_usd_attribute,
    get_property_class,
    remove_property_as_usd_attribute,
    valid_ui_prim_types,
)


def prim_allows_style_property(prim_type: str, prim: Usd.Prim, property_name: str) -> bool:
    if not prim_type.startswith(PRIM_NS):
        return False
    prim_type = prim_type.split(PRIM_NS)[1]
    if prim_type not in valid_ui_prim_types:
        return False
    prim_properties = get_property_class(prim_type, prim)
    return prim_properties.allows_style_property(property_name)


def prim_add_style_property(prim: Usd.Prim, property_name: str):
    prim_type: str = prim.GetTypeName()  # type: ignore
    if not prim_type.startswith(PRIM_NS):
        return
    prim_type = prim_type.split(PRIM_NS)[1]
    if prim_type not in valid_ui_prim_types:
        return
    attr_name = f"{ATTR_NS}:Style:{property_name}"
    property_name = property_name
    property_type = get_style_property_type(property_name)
    property_default = None  # TODO
    create_property_as_usd_attribute(prim, attr_name, property_name, property_type, property_default)


def prim_remove_style_property(prim: Usd.Prim, property_name: str):
    prim_type: str = prim.GetTypeName()  # type: ignore
    if not prim_type.startswith(PRIM_NS):
        return
    prim_type = prim_type.split(PRIM_NS)[1]
    if prim_type not in valid_ui_prim_types:
        return
    attr_name = f"{ATTR_NS}:Style:{property_name}"
    remove_property_as_usd_attribute(prim, attr_name)


def prims_allows_style_property(
    stage: Usd.Stage | None, prim_list: Sequence[Usd.Prim | Sdf.Path | str], property_name: str
) -> bool:
    for prim_path in prim_list:
        if not isinstance(prim_path, Usd.Prim) and stage is not None:
            prim = stage.GetPrimAtPath(prim_path)
        elif isinstance(prim_path, Usd.Prim):
            prim = prim_path
        else:
            continue
        prim_type: str = prim.GetTypeName()  # type: ignore
        if prim_allows_style_property(prim_type, prim, property_name):
            return True
    return False


def prims_add_style_property(stage: Usd.Stage | None, prim_list: Sequence[Usd.Prim | str], property_name: str):
    for prim_path in prim_list:
        if not isinstance(prim_path, Usd.Prim) and stage is not None:
            prim = stage.GetPrimAtPath(prim_path)
        elif isinstance(prim_path, Usd.Prim):
            prim = prim_path
        else:
            continue
        prim_type: str = prim.GetTypeName()  # type: ignore
        if prim_allows_style_property(prim_type, prim, property_name):
            prim_add_style_property(prim, property_name)


def prims_remove_style_property(stage: Usd.Stage | None, prim_list: Sequence[Usd.Prim | str], property_name: str):
    for prim_path in prim_list:
        if not isinstance(prim_path, Usd.Prim) and stage is not None:
            prim = stage.GetPrimAtPath(prim_path)
        elif isinstance(prim_path, Usd.Prim):
            prim = prim_path
        else:
            continue
        prim_type: str = prim.GetTypeName()  # type: ignore
        if prim_allows_style_property(prim_type, prim, property_name):
            prim_remove_style_property(prim, property_name)

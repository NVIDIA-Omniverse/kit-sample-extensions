# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path


def Singleton(class_):
    """
    A singleton decorator.
    """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@Singleton
class Icons:
    """A singleton that scans the icon folder and returns the icon depending on the type"""

    def __init__(self):
        self._current_path = Path(__file__).parent
        self._icon_path = self._current_path.parent.parent.parent.parent.parent.joinpath("icons")

        # Read all the svg files in the directory
        self._icons = {icon.stem: icon for icon in self._icon_path.glob("*.svg")}
        self._icons.update({icon.stem: icon for icon in self._icon_path.glob("*.png")})

    def get(self, prim_type, default=None):
        """Checks the icon cache and returns the icon if exists"""
        found = self._icons.get(prim_type)
        if not found and default:
            found = self._icons.get(default)
        if found:
            return str(found)
        else:
            return str(self._icons.get("Placeholder_Tooltip"))

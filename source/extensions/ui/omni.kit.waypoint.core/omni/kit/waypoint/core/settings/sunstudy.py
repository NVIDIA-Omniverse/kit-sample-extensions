# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from datetime import datetime
from typing import List, Optional, Tuple

import omni.usd
from pxr import Sdf, Usd

from .abstract_setting import AbstractWaypointSetting

WAYPOINT_ATTR_SUNSTUDY = "sunstudy"

ENVIRONMENT_PRIM_ROOT = "/Environment"


class EnvironmentProperties:
    """
    Date, time, location and ground properties path in environment prim.
    """

    LATITUDE = ENVIRONMENT_PRIM_ROOT + ".location:latitude"
    LONGITUDE = ENVIRONMENT_PRIM_ROOT + ".location:longitude"
    NORTH_ORIENTATION = ENVIRONMENT_PRIM_ROOT + ".location:north_orientation"

    TIME_START = ENVIRONMENT_PRIM_ROOT + ".time:start"
    TIME_END = ENVIRONMENT_PRIM_ROOT + ".time:end"
    TIME_CURRENT = ENVIRONMENT_PRIM_ROOT + ".time:current"

    DATE = ENVIRONMENT_PRIM_ROOT + ".date"

    GROUND_SIZE = ENVIRONMENT_PRIM_ROOT + ".ground:size"
    GROUND_TYPE = ENVIRONMENT_PRIM_ROOT + ".ground:type"
    GROUND_MATERIAL_PATH = ENVIRONMENT_PRIM_ROOT + ".ground:material:path"
    GROUND_MATERIAL_STRENGTH = ENVIRONMENT_PRIM_ROOT + ".ground:material:strength"

    SCENE_TEMPLATE = ENVIRONMENT_PRIM_ROOT + ".sceneTemplate"


class SunstudySetting(AbstractWaypointSetting):
    def __init__(self, edit_context: Usd.EditContext = None):
        super().__init__(edit_context)

    @property
    def info(self) -> Optional[List[List[str]]]:
        if not self.valid:
            return []
        latitude = self._data["location"][0] or ""
        longtitude = self._data["location"][1] or ""
        orientation = self._data["location"][2] or ""
        return [["Location", f"{longtitude}, {latitude}"], ["Orientation", f"{orientation}"]]

    def get_name(self):
        return "Sunstudy Settings"

    def is_dirty(self):
        FLOAT_MAX_DELTA = 0.01
        if not self.valid:
            return False

        date = self._get_sunstudy_date()
        if date != self._data["date"]:
            return True

        time = self._get_sunstudy_time()
        if time is None and self._data["time"] is None:
            return False
        elif time is None and self._data["time"] is not None:
            return True
        elif time is not None and self._data["time"] is None:
            return True
        elif abs(time - self._data["time"]) > FLOAT_MAX_DELTA:
            return True

        location = self._get_sunstudy_location()
        if not self.equal_data(location, self._data["location"]):
            return True

        return False

    def create(self, valid: bool = True):
        super().create(valid)
        if valid:
            # Collect data from sunstudy settings
            self._data["date"] = self._get_sunstudy_date()
            self._data["time"] = self._get_sunstudy_time()
            self._data["location"] = self._get_sunstudy_location()

    def recall(self, prim: Usd.Prim):
        if not self.valid:
            return
        if self._data["date"] is not None:
            self._set_attribute(EnvironmentProperties.DATE, self._data["date"], Sdf.ValueTypeNames.String)
        if self._data["time"] is not None:
            self._set_attribute(EnvironmentProperties.TIME_CURRENT, self._data["time"], Sdf.ValueTypeNames.Float)

        loc = self._data["location"]
        if loc is not None:
            # loc is a turple
            if loc[0] is not None:
                self._set_attribute(EnvironmentProperties.LATITUDE, loc[0], Sdf.ValueTypeNames.Double)
            if loc[1] is not None:
                self._set_attribute(EnvironmentProperties.LONGITUDE, loc[1], Sdf.ValueTypeNames.Double)
            if loc[2] is not None:
                self._set_attribute(EnvironmentProperties.NORTH_ORIENTATION, loc[2], Sdf.ValueTypeNames.Double)

    def save_to_usd(self, prim: Usd.Prim) -> None:
        self._save_data_to_usd(prim, WAYPOINT_ATTR_SUNSTUDY)

    def load_from_usd(self, prim: Usd.Prim) -> bool:
        return self._load_data_from_usd(prim, WAYPOINT_ATTR_SUNSTUDY)

    def _save_data_to_usd(self, prim: Usd.Prim, attr_name: str) -> None:
        super()._save_data_to_usd(prim, attr_name)

    def _load_data_from_usd(self, prim: Usd.Prim, attr_name: str) -> bool:
        result = super()._load_data_from_usd(prim, attr_name)
        return result

    def _get_sunstudy_location(self) -> List[float]:
        return [
            self._get_attribute(EnvironmentProperties.LATITUDE),
            self._get_attribute(EnvironmentProperties.LONGITUDE),
            self._get_attribute(EnvironmentProperties.NORTH_ORIENTATION),
        ]

    def _get_sunstudy_date(self):
        return self._get_attribute(EnvironmentProperties.DATE)

    def _get_sunstudy_time(self):
        return self._get_attribute(EnvironmentProperties.TIME_CURRENT)

    def _get_attribute(self, path: str):
        stage = omni.usd.get_context().get_stage()
        if not stage:  # pragma: no cover
            return None
        else:
            attribute = stage.GetPropertyAtPath(path)
            if attribute:
                return attribute.Get()
            else:
                return None

    def _set_attribute(self, path: str, value, value_type):
        stage: Usd.Stage = omni.usd.get_context().get_stage()
        if not stage:  # pragma: no cover
            return None
        else:
            attribute = stage.GetPropertyAtPath(path)
            if attribute:
                attribute.Set(value)
            else:
                prim_path, attr_name = path.split(".")
                prim: Usd.Prim = stage.GetPrimAtPath(prim_path)
                if not prim:
                    prim = stage.DefinePrim(prim_path)
                if prim:
                    prim.CreateAttribute(attr_name, value_type).Set(value)

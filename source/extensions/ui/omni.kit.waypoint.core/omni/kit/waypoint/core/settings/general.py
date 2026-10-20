# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import getpass
from datetime import datetime
from typing import List, Optional

import omni.client
import omni.usd
from pxr import Sdf, Usd

from .abstract_setting import AbstractWaypointSetting

WAYPOINT_ATTR_CREATE_TIME = "created"
WAYPOINT_ATTR_CREATE_BY = "created_by"
WAYPOINT_ATTR_COMMENT = "comment"
WAYPOINT_ATTR_FRAME = "frame"


class GeneralSetting(AbstractWaypointSetting):
    def __init__(self, edit_context):
        super().__init__(edit_context)
        self.data = {"create_time": None, "created_by": None, "comment": "", "frame": 0.0}
        self._prim: Usd.Prim = None

    @property
    def info(self) -> Optional[List[List[str]]]:
        date = self.data["create_time"].split(" ")[0]
        return [["Author", self.data["created_by"] or ""], ["Date Added", date]]

    def get_name(self):
        return "info"

    def create(self, valid: bool = True) -> None:
        super().create(valid)

        self.data["create_time"] = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.data["created_by"] = self._get_created_by()
        if self.data["created_by"]:
            self.data["created_by"] = self.data["created_by"].split("@")[0]
        self.data["comment"] = ""

    def recall(self, prim: Usd.Prim) -> None:
        pass

    def save_to_usd(self, prim: Usd.Prim) -> None:
        self._save_attribute(prim, WAYPOINT_ATTR_CREATE_TIME, self.data["create_time"], Sdf.ValueTypeNames.String)
        self._save_attribute(prim, WAYPOINT_ATTR_CREATE_BY, self.data["created_by"], Sdf.ValueTypeNames.String)
        self._save_attribute(prim, WAYPOINT_ATTR_COMMENT, self.data["comment"], Sdf.ValueTypeNames.String)
        self._save_attribute(prim, WAYPOINT_ATTR_FRAME, self.data["frame"], Sdf.ValueTypeNames.Float)

    def load_from_usd(self, prim: Usd.Prim) -> bool:
        self.data["create_time"] = prim.GetAttribute(WAYPOINT_ATTR_CREATE_TIME).Get()
        self.data["created_by"] = prim.GetAttribute(WAYPOINT_ATTR_CREATE_BY).Get()
        self.data["comment"] = prim.GetAttribute(WAYPOINT_ATTR_COMMENT).Get()
        self.data["frame"] = prim.GetAttribute(WAYPOINT_ATTR_FRAME).Get()

    def set_comment(self, comment: str) -> None:
        self.data["comment"] = comment
        if self.prim:
            self._save_attribute(self.prim, WAYPOINT_ATTR_COMMENT, self.data["comment"], Sdf.ValueTypeNames.String)

    def set_frame(self, frame: float) -> None:
        self.data["frame"] = frame
        if self.prim:
            self._save_attribute(self.prim, WAYPOINT_ATTR_FRAME, self.data["frame"], Sdf.ValueTypeNames.Float)

    # OM-79712 - Grabbing the user name, either from the current file, or `getpass.getuser()`
    def _get_created_by(self):
        stage: Usd.Stage = omni.usd.get_context().get_stage()
        path = stage.GetEditTarget().GetLayer().identifier
        res, inf = omni.client.get_server_info(path)
        user_name = ""
        if res == omni.client.Result.OK:
            user_name = inf.username
        if not user_name:
            return getpass.getuser()
        return user_name

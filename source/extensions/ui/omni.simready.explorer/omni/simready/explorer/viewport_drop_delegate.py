# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import json
from typing import Tuple

import omni.kit.commands
import omni.usd
from omni.kit.viewport.window.dragdrop.usd_file_drop_delegate import UsdFileDropDelegate
from pxr import Usd

from .actions import configure_prim
from .style import SIMREADY_DRAG_PREFIX


class SimReadyDragDropObject(UsdFileDropDelegate):
    """
    SimReady drop delegate based on UsdFileDropDelegate in omni.kit.viewport.window with variants setting.
    """

    def __init__(self):
        self._usd_prim_droped = None
        super().__init__()

    def drop_should_disable_preview(self):
        return True

    def get_raw_data(self, drop_data: dict) -> dict:
        return json.loads(drop_data.get("mime_data")[len(SIMREADY_DRAG_PREFIX) :])

    def get_url(self, drop_data: dict):
        return self.get_raw_data(drop_data)["url"]

    def add_reference_to_stage(self, usd_context, stage: Usd.Stage, url: str) -> Tuple[str, Usd.EditContext, str]:
        self._usd_prim_droped, edit_context, relative_url = super().add_reference_to_stage(usd_context, stage, url)
        return (self._usd_prim_droped, edit_context, relative_url)

    def accepted(self, drop_data: dict):
        mime_data = drop_data["mime_data"]
        self._usd_prim_droped = None
        return mime_data.startswith(SIMREADY_DRAG_PREFIX)

    def dropped(self, drop_data: dict):
        super().dropped(drop_data)

        # Additionaly, set variants if required
        usd_prim_droped = drop_data.get("usd_prim_droped") or self._usd_prim_droped
        if usd_prim_droped is not None:
            raw_drop_data = self.get_raw_data(drop_data)
            variants = raw_drop_data.get("variants", {})
            if variants:
                context_name = drop_data.get("usd_context_name", "")
                stage = omni.usd.get_context(context_name).get_stage()
                if stage:
                    configure_prim(stage, usd_prim_droped, variants)
        return

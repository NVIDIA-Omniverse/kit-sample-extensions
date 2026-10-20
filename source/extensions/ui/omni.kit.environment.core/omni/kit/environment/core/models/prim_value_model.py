# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Any, Optional

import carb
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni import ui
from pxr import Sdf, Usd


class PrimValueModel(ui.AbstractValueModel):
    """
    Model for simple usd prim states. Readonly.
    True means prim exists. False means prim not exists!
    """

    def __init__(self, prim_path: str, stage: Usd.Stage):
        """
        Args:
            prim_path: Stage prim path string
        """
        ui.AbstractValueModel.__init__(self)
        self.prim_path = prim_path
        self._stage = stage

    def destroy(self):
        pass  # pragma: no cover

    def set_value(self, value: Any) -> None:
        pass  # pragma: no cover

    def get_value_as_string(self) -> str:
        return str(self._has_prim())  # pragma: no cover

    def get_value_as_float(self) -> float:
        return float(self._has_prim())  # pragma: no cover

    def get_value_as_bool(self) -> bool:
        return self._has_prim()

    def get_value_as_int(self) -> int:
        return int(self._has_prim())  # pragma: no cover

    def _has_prim(self) -> bool:
        if not self._stage:
            # carb.log_warn(f"[{self.prim_path}]: no stage!")
            return False

        # TODO: cache the value to donot read property again without changing
        prim = self._stage.GetPrimAtPath(self.prim_path)
        if prim:
            return True
        else:
            return False

    def on_prim_changed(self, stage: Usd.Stage):
        self._stage = stage
        # Only notify model value changed, read property when get model value
        self._value_changed()

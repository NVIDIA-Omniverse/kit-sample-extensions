# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from omni.ui import AbstractValueModel

__all__ = ["ProgressModel"]


class ProgressModel(AbstractValueModel):
    """
    A float model to represent progress.
    """

    def __init__(self):
        super().__init__()
        self._value: float | None = None

    def set_value(self, value: float) -> None:
        """
        Override AbstractValueModel.set_value.
        """
        if self._value is None or int(value * 100) != int(self._value * 100):
            self._value = value
            self._value_changed()

    def get_value_as_float(self) -> float:
        """
        Override AbstractValueModel.get_value_as_float.
        """
        return self._value or 0.0

    def get_value_as_string(self) -> str:
        """
        Override AbstractValueModel.get_value_as_string.
        """
        if self._value is None:
            return "Computing dependencies"
        else:
            return f"{int(self._value * 100)} %"

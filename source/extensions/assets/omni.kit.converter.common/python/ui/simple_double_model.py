# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni import ui


class SimpleDoubleModel(ui.AbstractValueModel):
    """String-backed value model whose floating-point view uses binary64 precision."""

    def __init__(self, default_value: float | str = 0.0):
        super().__init__()
        self._value = self._as_text(default_value)

    @staticmethod
    def _as_text(value: bool | int | float | str) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        return value if isinstance(value, str) else str(value)

    def get_value_as_bool(self) -> bool:
        return bool(self.get_value_as_float())

    def get_value_as_float(self) -> float:
        try:
            # Python float is an IEEE-754 binary64 value. Keeping the source
            # text here avoids SimpleFloatModel's string-to-binary32 path.
            return float(self._value)
        except ValueError:
            return 0.0

    def get_value_as_int(self) -> int:
        try:
            return int(self.get_value_as_float())
        except (OverflowError, ValueError):
            return 0

    def get_value_as_string(self) -> str:
        return self._value

    def set_value(self, value: bool | int | float | str) -> None:
        new_value = self._as_text(value)
        if new_value == self._value:
            return
        self._value = new_value
        self._value_changed()

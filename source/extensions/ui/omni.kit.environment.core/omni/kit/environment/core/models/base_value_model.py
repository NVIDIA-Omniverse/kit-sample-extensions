# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Any, Callable, List

from omni import ui


class BaseValueModel(ui.AbstractValueModel):
    def __init__(self, default_value: Any = None):
        super().__init__()
        self.default = default_value
        self._sub_ids: List[int] = []

    def destroy(self):
        for id in self._sub_ids:
            super().remove_value_changed_fn(id)
        self._sub_ids.clear()

    def add_value_changed_fn(self, value_changed_fn: Callable[[ui.AbstractValueModel], None]) -> int:
        id = super().add_value_changed_fn(value_changed_fn)
        self._sub_ids.append(id)
        return id

    def remove_value_changed_fn(self, id: int) -> None:
        super().remove_value_changed_fn(id)
        if id in self._sub_ids:
            self._sub_ids.remove(id)

    def reset_value(self) -> None:
        if self.default is not None:
            self.set_value(self.default)

    def set_default(self, value: Any, save: bool = False) -> None:
        self.default = value
        if save:
            self.set_value(value)

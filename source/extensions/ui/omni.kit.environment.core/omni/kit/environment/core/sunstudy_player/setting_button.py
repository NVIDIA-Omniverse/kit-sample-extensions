# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import abc

from omni import ui

from ..models import SettingModel


class SettingButton(ui.Button):
    """Abstract button binded with setting."""

    def __init__(self, setting_path, **kwargs):
        super().__init__(**kwargs)

        self.model = SettingModel(setting_path)
        self.model.add_value_changed_fn(self._on_value_changed)
        self.set_clicked_fn(self._on_clicked)

        self._on_value_changed(self.model)

    def destroy(self):
        self.model.destroy()

    @abc.abstractmethod
    def _on_clicked(self):
        pass

    @abc.abstractmethod
    def _on_value_changed(self, model: ui.AbstractValueModel):
        pass

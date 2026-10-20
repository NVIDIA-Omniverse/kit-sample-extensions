# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from omni.ui import SimpleBoolModel

__all__ = ["SettingsModel"]


class SettingsModel:
    def __init__(self):
        self.variants_model = SimpleBoolModel(True)
        self.instance_prototypes_model = SimpleBoolModel(True)
        self.persist_model = SimpleBoolModel(False)
        self.autovalidate_model = SimpleBoolModel(True)

    @property
    def variants(self) -> bool:
        return self.variants_model.as_bool

    @variants.setter
    def variants(self, value: bool) -> None:
        self.variants_model.as_bool = value

    @property
    def instance_prototypes(self) -> bool:
        return self.instance_prototypes_model.as_bool

    @instance_prototypes.setter
    def instance_prototypes(self, value: bool) -> None:
        self.instance_prototypes_model.as_bool = value

    @property
    def persist(self) -> bool:
        return self.persist_model.as_bool

    @persist.setter
    def persist(self, value: bool) -> None:
        self.persist_model.as_bool = value

    @property
    def autovalidate(self) -> bool:
        return self.autovalidate_model.as_bool

    @autovalidate.setter
    def autovalidate(self, value: bool) -> None:
        self.autovalidate_model.as_bool = value

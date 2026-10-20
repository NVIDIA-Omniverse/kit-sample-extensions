# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import carb
from omni.asset_validator.core import (
    Capability,
    Profile,
    ProfileRegistry,
    RequirementsRegistry,
    add_registry_profile_callback,
    add_registry_requirement_callback,
)

from ._options import OptionGroup, OptionModel, OptionsModel

__all__ = ["ProfilesModel"]


def _get_url(path: str) -> str:
    url = carb.settings.get_settings().get("exts/omni.asset_validator.ui/capabilities/url")
    return f"{url}/{path}"


class CapabilityModel(OptionModel):
    def __init__(self, capability: Capability, selected: bool, enabled: bool):
        super().__init__(
            capability,
            capability.id,
            capability.id,
            url=_get_url(capability.path) if capability.path else None,
            selected=selected,
            enabled=enabled,
        )


class ProfileModel(OptionGroup):
    def __init__(self, profile: Profile):
        super().__init__(f"{profile.id}@{profile.version}", _get_url(profile.path) if profile.path else None)


class ProfilesModel(OptionsModel):
    def __init__(self):
        super().__init__()
        self._requirement_subscription = add_registry_requirement_callback(self.initialize)
        self._profile_subscription = add_registry_profile_callback(self.initialize)

    def initialize(self) -> None:
        registry = RequirementsRegistry()
        self.clear()
        for profile in ProfileRegistry().profiles:
            if not profile.capabilities:
                continue
            profile_model = ProfileModel(profile)
            selected: bool = False
            for capability in profile.capabilities:
                enabled: bool = bool(registry.get_validators(capability.requirements))
                profile_model.append(CapabilityModel(capability, selected, enabled))
            self.append(profile_model)

    def reset(self) -> None:
        for profile in self:
            selected: bool = False
            for capability in profile:
                capability.selected = selected

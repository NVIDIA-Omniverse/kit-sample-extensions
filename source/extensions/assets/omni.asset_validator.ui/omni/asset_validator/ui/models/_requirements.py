# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import carb
from omni.asset_validator.core import (
    Requirement,
    RequirementProtocol,
    RequirementRefProtocol,
    RequirementsRegistry,
    SemVer,
)

from ._options import OptionModel


def _get_url(path: str) -> str:
    url = carb.settings.get_settings().get("exts/omni.asset_validator.ui/capabilities/url")
    return f"{url}/{path}"


class RequirementModel(OptionModel):
    def __init__(self, requirement: Requirement | RequirementRefProtocol, selected: bool, enabled: bool):
        requirement = self._resolve(requirement)
        if requirement is None:
            raise ValueError("RequirementModel requires a registered requirement")
        display_name = f"{requirement.display_name or requirement.code}@{requirement.version or SemVer.DEFAULT}"
        super().__init__(
            requirement,
            display_name,
            requirement.message or "",
            url=_get_url(requirement.path) if requirement.path else None,
            selected=selected,
            enabled=enabled,
        )

    def _resolve(self, requirement: Requirement | RequirementRefProtocol) -> Requirement | None:
        if isinstance(requirement, RequirementProtocol):
            return requirement

        if isinstance(requirement, RequirementRefProtocol):
            return RequirementsRegistry().find_requirement(requirement.code, requirement.version)

        return None

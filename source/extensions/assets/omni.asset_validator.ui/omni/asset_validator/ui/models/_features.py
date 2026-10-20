# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import carb
from omni.asset_validator.core import (
    Feature,
    FeatureRegistry,
    RequirementsRegistry,
    add_registry_feature_callback,
    add_registry_requirement_callback,
)

from ._options import OptionGroup, OptionsModel
from ._requirements import RequirementModel

__all__ = ["FeaturesModel"]


def _get_url(path: str) -> str:
    url = carb.settings.get_settings().get("exts/omni.asset_validator.ui/capabilities/url")
    return f"{url}/{path}"


class FeatureModel(OptionGroup):
    def __init__(self, feature: Feature):
        super().__init__(f"{feature.id}@{feature.version}", _get_url(feature.path) if feature.path else None)


class FeaturesModel(OptionsModel):
    def __init__(self):
        super().__init__()
        self._requirement_subscription = add_registry_requirement_callback(self.initialize)
        self._feature_subscription = add_registry_feature_callback(self.initialize)

    def initialize(self) -> None:
        selected: bool = False
        registry = RequirementsRegistry()
        self.clear()
        for feature in FeatureRegistry():
            if not feature.requirements:
                continue
            if all(registry.get_validator(requirement) is None for requirement in feature.requirements):
                continue
            feature_model = FeatureModel(feature)
            for requirement in feature.requirements:
                feature_model.append(
                    RequirementModel(requirement, selected, registry.get_validator(requirement) is not None)
                )
            self.append(feature_model)

    def reset(self) -> None:
        selected: bool = False
        for feature in self:
            for requirement in feature:
                requirement.selected = selected

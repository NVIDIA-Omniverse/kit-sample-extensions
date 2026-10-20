# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps

from omni.asset_validator.core import BaseRuleChecker, Capability, Requirement, RequirementsRegistry

from ..models._capabilities import CapabilitiesModel
from ..models._categories import CategoriesModel
from ..models._features import FeaturesModel
from ..models._options import OptionModel
from ..models._profiles import ProfilesModel

__all__ = ["OptionsDelegate"]


def synchronized(func: Callable[..., None]) -> Callable[..., None]:
    """
    Decorator to synchronize calls to the delegate.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            func(self, *args, **kwargs)
        finally:
            self._syncing = False

    return wrapper


@dataclass
class OptionsDelegate:
    """
    Delegate that coordinates bidirectional selection between rules and requirements.
    """

    categories: CategoriesModel
    capabilities: CapabilitiesModel
    features: FeaturesModel
    profiles: ProfilesModel
    _syncing: bool = field(init=False, default=False)
    _subscriptions: list[int] = field(init=False, default_factory=list)

    def __post_init__(self):
        for category in self.categories:
            for rule_option in category:
                subscription = rule_option.add_value_changed_fn(self._on_rule_changed)
                self._subscriptions.append(subscription)
        for capability in self.capabilities:
            for req_option in capability:
                subscription = req_option.add_value_changed_fn(self._on_capability_changed)
                self._subscriptions.append(subscription)
        for feature in self.features:
            for req_option in feature:
                subscription = req_option.add_value_changed_fn(self._on_feature_changed)
                self._subscriptions.append(subscription)
        for profile in self.profiles:
            for cap_option in profile:
                subscription = cap_option.add_value_changed_fn(self._on_profile_changed)
                self._subscriptions.append(subscription)

    @synchronized
    def _on_rule_changed(self, rule_option: OptionModel) -> None:
        rule: type[BaseRuleChecker] = rule_option.value
        selected: bool = rule_option.selected

        for requirement in RequirementsRegistry().get_requirements(rule):
            if req_option := self.capabilities.get(requirement):
                req_option.selected = selected
            if req_option := self.features.get(requirement):
                req_option.selected = selected

    @synchronized
    def _on_capability_changed(self, req_option: OptionModel) -> None:
        requirement: Requirement = req_option.value
        selected: bool = req_option.selected

        if validator := RequirementsRegistry().get_validator(requirement):
            if rule_option := self.categories.get(validator):
                rule_option.selected = selected

        if req_option := self.features.get(requirement):
            req_option.selected = selected

    @synchronized
    def _on_feature_changed(self, req_option: OptionModel) -> None:
        requirement: Requirement = req_option.value
        selected: bool = req_option.selected

        if validator := RequirementsRegistry().get_validator(requirement):
            if rule_option := self.categories.get(validator):
                rule_option.selected = selected

        if req_option := self.capabilities.get(requirement):
            req_option.selected = selected

    @synchronized
    def _on_profile_changed(self, cap_option: OptionModel) -> None:
        capability: Capability = cap_option.value
        selected: bool = cap_option.selected

        for requirement in capability.requirements:
            if req_option := self.capabilities.get(requirement):
                req_option.selected = selected

            if req_option := self.features.get(requirement):
                req_option.selected = selected

    @synchronized
    def reset(self) -> None:
        self.categories.reset()
        self.capabilities.reset()
        self.features.reset()
        self.profiles.reset()

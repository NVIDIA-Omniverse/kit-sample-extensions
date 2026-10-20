# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from functools import lru_cache
from typing import List

import carb
import omni.asset_validator.core

VALIDATOR_SETTINGS_BASE_PATH = "persistent/configurator_publisher/validator/"


class AssetValidatorUtils:
    __initialized = False

    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_categories() -> List[str]:
        """
        Returns:
            The available categories.
        """

        AssetValidatorUtils.__initialize_validator_settings()
        return omni.asset_validator.core.ValidationRulesRegistry.categories()

    @staticmethod
    @lru_cache(maxsize=10)
    def get_rules_of_category(category: str) -> List[str]:
        AssetValidatorUtils.__initialize_validator_settings()

        rules = []
        for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category):
            rules.append(rule.__name__)

        return rules

    @staticmethod
    @lru_cache(maxsize=100)
    def get_rule_description(r: str) -> str:
        AssetValidatorUtils.__initialize_validator_settings()

        rule = omni.asset_validator.core.ValidationRulesRegistry.rule(r)

        return rule.GetDescription() if rule else ""

    @staticmethod
    def is_rule_enabled(rule: str) -> bool:
        AssetValidatorUtils.__initialize_validator_settings()

        setting_path = AssetValidatorUtils.get_rule_setting_path(rule)
        settings = carb.settings.get_settings()
        return settings.get(setting_path) or False

    @staticmethod
    def set_rule_enabled(rule: str, enabled: bool):
        AssetValidatorUtils.__initialize_validator_settings()

        setting_path = AssetValidatorUtils.get_rule_setting_path(rule)
        settings = carb.settings.get_settings()
        settings.set(setting_path, enabled)

    @staticmethod
    def get_rule_setting_path(rule: str):
        AssetValidatorUtils.__initialize_validator_settings()

        return VALIDATOR_SETTINGS_BASE_PATH + rule

    @staticmethod
    def __initialize_validator_settings():
        if AssetValidatorUtils.__initialized:
            return
        AssetValidatorUtils.__initialized = True

        settings = carb.settings.get_settings()
        for category in omni.asset_validator.core.ValidationRulesRegistry.categories(enabledOnly=True):
            for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category, enabledOnly=True):
                setting_path = AssetValidatorUtils.get_rule_setting_path(rule.__name__)
                settings.set_default(setting_path, True)

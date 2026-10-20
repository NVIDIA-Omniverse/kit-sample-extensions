"""Tests for extension settings and preferences UI and persistence.

This module tests the settings and preferences layer: defaults, normalization, persistence,
paths, compounds, prefix, and settings utils (TestSettingsDefaults, TestSettingsNormalization,
TestSettingsPersistence, TestSettingsPaths, TestSettingsCompounds, TestSettingsPrefix,
TestSettingsUtils, TestSettingsUtilsMore), settings and preferences UI (TestSettingsUi,
TestPreferencesUi), plugin property factory and plugins validation (TestPluginPropertyFactory,
TestSettingsPluginsValidation), and preferences sections and lifecycle (TestPreferencesSections,
TestPreferencesLifecycle). We test these because settings control extension and UI behavior
(paths, context order, compounds, etc.); broken persistence or defaults would reset user
choices or break catalog/context behavior across sessions."""

from .test_plugin_property_factory import TestPluginPropertyFactory  # noqa: F401
from .test_preferences_lifecycle import TestPreferencesLifecycle  # noqa: F401
from .test_preferences_sections import TestPreferencesSections  # noqa: F401
from .test_preferences_ui import TestPreferencesUi  # noqa: F401
from .test_settings_compounds import TestSettingsCompounds  # noqa: F401
from .test_settings_defaults import TestSettingsDefaults  # noqa: F401
from .test_settings_normalization import TestSettingsNormalization  # noqa: F401
from .test_settings_paths import TestSettingsPaths  # noqa: F401
from .test_settings_persistence import TestSettingsPersistence  # noqa: F401
from .test_settings_plugins_validation import TestSettingsPluginsValidation  # noqa: F401
from .test_settings_prefix import TestSettingsPrefix  # noqa: F401
from .test_settings_ui import TestSettingsUi  # noqa: F401
from .test_settings_utils import TestSettingsUtils  # noqa: F401
from .test_settings_utils_more import TestSettingsUtilsMore  # noqa: F401

__all__ = [
    "TestPreferencesUi",
    "TestSettingsDefaults",
    "TestSettingsNormalization",
    "TestSettingsPersistence",
    "TestSettingsPaths",
    "TestSettingsCompounds",
    "TestSettingsUi",
    "TestSettingsUtils",
    "TestSettingsPrefix",
    "TestPluginPropertyFactory",
    "TestSettingsUtilsMore",
    "TestSettingsPluginsValidation",
    "TestPreferencesSections",
    "TestPreferencesLifecycle",
]

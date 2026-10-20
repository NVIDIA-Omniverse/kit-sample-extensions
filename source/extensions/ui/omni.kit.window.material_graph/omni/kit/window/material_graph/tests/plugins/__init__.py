"""Tests for the plugin system, catalog build, and MDL integration.

This module tests plugin behavior for render-context integration and catalog discovery:
catalog build (TestCatalogBuild), MDL paths/settings (TestMdlPaths, TestMdlSettings),
plugin base and manager core (TestPluginBase, TestPluginManagerCore), reload behavior,
and plugin properties (TestPluginBehavior, TestPluginReload, TestPluginProperties)."""

from .test_catalog_build import TestCatalogBuild  # noqa: F401
from .test_mdl_paths import TestMdlPaths  # noqa: F401
from .test_mdl_polymorphic_resolver import TestMdlPolymorphicResolver  # noqa: F401
from .test_mdl_settings import TestMdlSettings  # noqa: F401
from .test_plugin_base import TestPluginBase  # noqa: F401
from .test_plugin_behavior import TestPluginBehavior  # noqa: F401
from .test_plugin_manager_core import TestPluginManagerCore  # noqa: F401
from .test_plugin_properties import TestPluginProperties  # noqa: F401
from .test_plugin_reload import TestPluginReload  # noqa: F401

__all__ = [
    "TestCatalogBuild",
    "TestMdlPaths",
    "TestPluginBehavior",
    "TestPluginReload",
    "TestPluginBase",
    "TestPluginManagerCore",
    "TestMdlSettings",
    "TestMdlPolymorphicResolver",
    "TestPluginProperties",
]

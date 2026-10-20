"""Tests for extension configuration: paths, catalog config, and node config.

This module tests how the extension resolves and uses configuration: path resolution for assets
and nodegraphs (TestPathsResolution), catalog configuration and defaults (TestConfigCatalog), and
node-related config (TestConfigNodes). We test these because config drives where files are loaded
from, what appears in the catalog, and how nodes are created or validated; misconfiguration would
break discovery, export paths, or graph behavior."""

from .test_config_catalog import TestConfigCatalog  # noqa: F401
from .test_config_nodes import TestConfigNodes  # noqa: F401
from .test_discovery import TestDiscoveryContract  # noqa: F401
from .test_graph_style import TestGraphStyle  # noqa: F401
from .test_paths_resolution import TestPathsResolution  # noqa: F401

__all__ = [
    "TestPathsResolution",
    "TestConfigCatalog",
    "TestConfigNodes",
    "TestDiscoveryContract",
    "TestGraphStyle",
]

"""Tests for user preferences used by the material graph extension.

This module tests preference handling that affects user-visible or persistent behavior: path list
preferences (TestPathList) used for catalog search paths, export paths, or similar list-of-paths
settings. We test these because preferences drive where the extension looks for assets and how
it persists user choices; broken path list handling would break catalog discovery or export
locations."""

from .test_path_list import TestPathList  # noqa: F401

__all__ = [
    "TestPathList",
]

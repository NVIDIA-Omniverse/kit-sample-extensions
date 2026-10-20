"""Tests for the context manager and context-related UI controllers.

This module tests the material context layer: loading a material (TestContextManagerLoad),
removing contexts and cleanup (TestContextManagerRemove), the full
context manager API (add/clear/load/get_context/set_current, destroy, root prim replacement;
TestContextManagerApi), low-level helpers (ContextHandle, ContextPluginAccess, Context.destroy;
TestContextHelpers), the controller that syncs widget and catalog when the context changes
(TestContextModelController), and the context switcher UI (tabs/menu from settings;
TestContextSwitcherController). We test these because the extension supports multiple render
contexts (e.g. MDL vs USD); the context manager is the single source of truth for the current
material and its plugin, and broken context switching would show wrong graphs or stale data."""

from .test_context_helpers import TestContextHelpers  # noqa: F401
from .test_context_manager_api import TestContextManagerApi  # noqa: F401
from .test_context_manager_load import TestContextManagerLoad  # noqa: F401
from .test_context_manager_remove import TestContextManagerRemove  # noqa: F401
from .test_context_manager_upgrade import TestContextManagerUpgrade  # noqa: F401
from .test_context_model_controller import TestContextModelController  # noqa: F401
from .test_context_switcher_controller import TestContextSwitcherController  # noqa: F401

__all__ = [
    "TestContextManagerLoad",
    "TestContextManagerRemove",
    "TestContextManagerUpgrade",
    "TestContextManagerApi",
    "TestContextHelpers",
    "TestContextModelController",
    "TestContextSwitcherController",
]

# pylint: disable=relative-beyond-top-level
from unittest.mock import patch

import omni.kit.test

from ...scripts.context_manager import context as context_module
from ...scripts.context_manager.context_handle import ContextHandle
from ...scripts.context_manager.context_plugin_access import ContextPluginAccess


class _DummyModel:
    def __init__(self, *_args, **_kwargs) -> None:
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True


class _DummyManager:
    def __init__(self, plugins=None, destroyed=False) -> None:
        self._plugins = plugins or {}
        self._destroyed = destroyed

    def get_all_plugins(self):
        if self._destroyed:
            return []
        return list(self._plugins.values())

    def get_plugin(self, name):
        if self._destroyed:
            return None
        return self._plugins.get(name)


class TestContextHelpers(omni.kit.test.AsyncTestCase):
    """ContextHandle and ContextPluginAccess adapt the context/plugin layer; Context.destroy releases
    model and plugin. We test handle validity, plugin access pass-through, and destroy clearing refs
    (with MaterialModel patched for the destroy test)."""

    async def test_context_handle_validity(self) -> None:
        """Handle validity reflects error and payload."""
        handle = ContextHandle(None, None, "ctx", error="boom")
        self.assertFalse(handle.is_valid)

        plugin = object()
        context = object()
        handle = ContextHandle(context, plugin, "ctx")
        self.assertTrue(handle.is_valid)

    async def test_context_plugin_access(self) -> None:
        """PluginAccess passes through to manager."""
        plugin_a = object()
        manager = _DummyManager({"a": plugin_a})
        access = ContextPluginAccess(manager)
        self.assertEqual(access.get_plugins(), [plugin_a])
        self.assertIs(access.get_plugin("a"), plugin_a)
        self.assertIsNone(access.get_plugin("missing"))

        destroyed_access = ContextPluginAccess(_DummyManager({"a": plugin_a}, destroyed=True))
        self.assertEqual(destroyed_access.get_plugins(), [])
        self.assertIsNone(destroyed_access.get_plugin("a"))

    async def test_context_destroy_clears_references(self) -> None:
        """Context.destroy releases model and plugin refs."""
        # Patch MaterialModel to use _DummyModel so we can assert model.destroyed and refs cleared.
        with patch.object(context_module, "MaterialModel", _DummyModel):
            plugin = object()
            ctx = context_module.Context(object(), "ctx", object(), plugin, validator=object())
            model = ctx.model
            ctx.destroy()
            self.assertTrue(model.destroyed)
            self.assertIsNone(ctx.model)
            self.assertIsNone(ctx.plugin)

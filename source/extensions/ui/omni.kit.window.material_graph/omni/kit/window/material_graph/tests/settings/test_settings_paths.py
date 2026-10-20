# pylint: disable=relative-beyond-top-level,unused-import
import tempfile
from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.plugins.impl.mdl import settings as mdl_settings
from ...scripts.settings import compounds
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestSettingsPaths(MaterialGraphTestBase):
    """Path sanitization for MDL modules and compound paths."""

    async def test_mdl_module_validation(self) -> None:
        """MDL module path validation should reject invalid inputs."""
        # Patch resolver so this test only exercises validation logic,
        # not environment-dependent resolver behavior.
        with patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=True):
            Settings.set_mdl_catalog_modules(["not_mdl.txt"])
            self.assertEqual(Settings.get_mdl_catalog_modules(), [])

    async def test_mdl_module_resolve(self) -> None:
        """MDL module path should be rejected when resolver fails."""
        # Patch resolver to simulate a resolution failure deterministically.
        with patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=False):
            Settings.set_mdl_catalog_modules(["test.mdl"])
            self.assertEqual(Settings.get_mdl_catalog_modules(), [])

    async def test_mdl_module_accepts_valid(self) -> None:
        """Valid MDL modules should be accepted and stored."""
        # Patch resolver so this test is not dependent on local MDL assets.
        with patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=True):
            Settings.set_mdl_catalog_modules(["test.mdl"])
            self.assertEqual(Settings.get_mdl_catalog_modules(), ["test.mdl"])

    async def test_invalid_plugin_property_key_returns_none(self) -> None:
        """Invalid plugin property keys should return None."""
        self.assertIsNone(Settings.get_plugin_property_key("", "key"))

    async def test_mdl_module_logs_invalid(self) -> None:
        """Invalid MDL module paths should log a warning."""
        with (
            patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=False),
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.mdl.settings.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            Settings.set_mdl_catalog_modules(["bad.mdl"])
            Settings.get_mdl_catalog_modules()
            self.assertTrue(log_warn.called)

    async def test_compound_paths_sanitized(self) -> None:
        """Compound paths should be deduped and validated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            Settings.set_compound_paths([temp_dir, temp_dir])
            self.assertEqual(Settings.get_compound_paths(), [temp_dir])

    async def test_compound_paths_initialized_default(self) -> None:
        """Missing compound paths should initialize to default."""
        self._settings.destroy_item(Settings.COMPOUND_PATHS)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(compounds, "_resolve_token", autospec=True, return_value=temp_dir),
        ):
            Settings.ensure_compound_paths_initialized()
        value = self._settings.get(Settings.COMPOUND_PATHS)
        self.assertEqual(value, [temp_dir])

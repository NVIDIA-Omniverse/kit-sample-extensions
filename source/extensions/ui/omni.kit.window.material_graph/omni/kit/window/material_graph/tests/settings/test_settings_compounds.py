# pylint: disable=relative-beyond-top-level
import tempfile
from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.settings import compounds
from ...scripts.settings.utils import COMPOUND_PATHS, COMPOUND_PATHS_EXPLICIT_EMPTY
from ..base import MaterialGraphTestBase


class TestSettingsCompounds(MaterialGraphTestBase):
    """Direct tests for settings compounds helpers."""

    async def test_token_resolution_failure_logs_warning(self) -> None:
        """Token resolution failures should log warnings and be excluded."""
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.settings.compounds.carb.tokens.get_tokens_interface",
                autospec=True,
            ) as tokens_iface,
            patch(
                f"{Paths.MODULE_ID}.scripts.settings.compounds.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            tokens_iface.return_value.resolve.return_value = ""
            compounds.set_compound_paths(["${bad_token}"])
            self.assertEqual(compounds.get_compound_paths(), [])
            log_warn.assert_called()

    async def test_sanitizes_invalid_and_duplicate_paths(self) -> None:
        """Invalid and duplicate paths should be removed."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch(
                f"{Paths.MODULE_ID}.scripts.settings.compounds.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            compounds.set_compound_paths([temp_dir, temp_dir, "missing"])
            self.assertEqual(compounds.get_compound_paths(), [temp_dir])
            self.assertTrue(log_warn.called)

    async def test_ensure_paths_initialized_sets_default_when_missing(self) -> None:
        """ensure_compound_paths_initialized should seed defaults only when unset."""
        self._settings.destroy_item(COMPOUND_PATHS)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(compounds, "_resolve_token", autospec=True, return_value=temp_dir),
        ):
            compounds.ensure_compound_paths_initialized()
        value = self._settings.get(COMPOUND_PATHS)
        self.assertEqual(value, [temp_dir])

    async def test_explicit_empty_paths_remain_empty(self) -> None:
        """Clearing the last compound path must not silently restore defaults."""
        compounds.clear_compound_paths()
        compounds.ensure_compound_paths_initialized()
        self.assertTrue(self._settings.get_as_bool(COMPOUND_PATHS_EXPLICIT_EMPTY))
        self.assertEqual(compounds._get_raw_compound_paths(), [])
        self.assertEqual(compounds.get_compound_paths(), [])

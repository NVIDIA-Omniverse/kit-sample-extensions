# pylint: disable=relative-beyond-top-level,protected-access
from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.settings import utils
from ..base import MaterialGraphTestBase


class TestSettingsUtils(MaterialGraphTestBase):
    """Tests for settings utils logging behavior."""

    async def test_sanitize_list_logs_invalid(self) -> None:
        """Invalid list entries should emit warnings when enabled."""

        def _reject(_value):
            return False, "invalid"

        with patch(
            f"{Paths.MODULE_ID}.scripts.settings.utils.logger.warning",
            autospec=True,
        ) as log_warn:
            result = utils._sanitize_list(["bad"], _reject, log_invalid=True, warn_prefix="invalid value")
            self.assertEqual(result, [])
            log_warn.assert_called()

    async def test_normalize_texture_format(self) -> None:
        """Texture format tokens should normalize to lowercase extension values."""
        self.assertEqual(utils.normalize_texture_format(".PNG"), "png")
        self.assertEqual(utils.normalize_texture_format("  Jpg "), "jpg")
        self.assertEqual(utils.normalize_texture_format(""), "")
        self.assertEqual(utils.normalize_texture_format("bad-token!"), "")

    async def test_sanitize_texture_formats(self) -> None:
        """Supported texture formats should dedupe/normalize and skip invalid entries."""
        with patch(
            f"{Paths.MODULE_ID}.scripts.settings.utils.logger.warning",
            autospec=True,
        ) as log_warn:
            values = [".PNG", "jpg", "JPG", "bad token", 42]
            self.assertEqual(utils.sanitize_texture_formats(values), ["png", "jpg"])
            log_warn.assert_called()

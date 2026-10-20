import os
import tempfile
from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.registries.texture import info as texture_info

# pylint: disable=protected-access
from ..base import MaterialGraphTestBase


class TestTextureInfo(MaterialGraphTestBase):
    """texture_info wraps texture resolution and icon creation; it caches results by path so we don't
    repeatedly call into bindings. We test cache hit on second call, empty path returning None,
    exception path logging and returning None, and create_texture_icon delegating to bindings.
    tearDown clears the module cache to avoid cross-test leakage."""

    async def tearDown(self) -> None:
        """Reset module cache to avoid cross-test contamination."""
        texture_info._CACHE.clear()
        await super().tearDown()

    async def test_valid_texture_path_cached(self) -> None:
        """Valid texture info cached by path."""
        # Patch get_texture_info to control return value and assert it is only called once for same path.
        texture_info._CACHE.clear()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
        try:
            with patch(
                f"{Paths.MODULE_ID}._textureUtils.get_texture_info",
                autospec=True,
                return_value=(True, 4),
            ) as get_info:
                self.assertEqual(texture_info.get_texture_info(path), (True, 4))
                self.assertEqual(texture_info.get_texture_info(path), (True, 4))
                self.assertEqual(get_info.call_count, 1)
        finally:
            os.remove(path)

    async def test_invalid_texture_path_returns_none(self) -> None:
        """Empty path returns None."""
        self.assertIsNone(texture_info.get_texture_info(""))

    async def test_texture_info_error_logs(self) -> None:
        """Exception from bindings logs and returns None."""
        # Patch get_texture_info to raise; patch logger.warning to assert path is in log.
        texture_info._CACHE.clear()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
        try:
            with (
                patch(
                    f"{Paths.MODULE_ID}._textureUtils.get_texture_info",
                    autospec=True,
                    side_effect=RuntimeError("boom"),
                ),
                patch(
                    f"{Paths.MODULE_ID}.scripts.models.catalog.registries.texture.info.logger.warning",
                    autospec=True,
                ) as log_warn,
            ):
                self.assertIsNone(texture_info.get_texture_info(path))
                self.assertTrue(any(path in call.args for call in log_warn.call_args_list))
        finally:
            os.remove(path)

    async def test_unsupported_texture_extension_skips_binding(self) -> None:
        """Unsupported extensions should short-circuit before binding lookup."""
        texture_info._CACHE.clear()
        with patch(
            f"{Paths.MODULE_ID}._textureUtils.get_texture_info",
            autospec=True,
            return_value=(True, 4),
        ) as get_info:
            self.assertIsNone(texture_info.get_texture_info("file.unsupported"))
            get_info.assert_not_called()

    async def test_create_texture_icon_success(self) -> None:
        """Texture icon creation delegates to bindings."""
        # Patch create_texture_icon to avoid real bindings and assert call.
        with patch(
            f"{Paths.MODULE_ID}._textureUtils.create_texture_icon",
            autospec=True,
            return_value=True,
        ) as create_icon:
            self.assertTrue(texture_info.create_texture_icon("file.png", "out.png", 64))
            create_icon.assert_called_once()

    async def test_create_texture_icon_unsupported_extension(self) -> None:
        """Unsupported extensions should not invoke icon creation binding."""
        with patch(
            f"{Paths.MODULE_ID}._textureUtils.create_texture_icon",
            autospec=True,
            return_value=True,
        ) as create_icon:
            self.assertFalse(texture_info.create_texture_icon("file.unsupported", "out.png", 64))
            create_icon.assert_not_called()

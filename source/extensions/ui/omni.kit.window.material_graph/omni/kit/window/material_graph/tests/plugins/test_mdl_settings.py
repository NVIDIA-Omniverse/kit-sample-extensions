# pylint: disable=relative-beyond-top-level,no-member
from unittest.mock import patch

from pxr import Ar

from ...scripts.config.paths import Paths
from ...scripts.plugins.impl.mdl import settings as mdl_settings
from ..base import MaterialGraphTestBase


class TestMdlSettings(MaterialGraphTestBase):
    """Tests for MDL settings sanitization."""

    async def test_sanitize_mdl_modules(self) -> None:
        """Invalid or unresolved paths should be removed."""
        mdl_path = str(Paths.DATA_PATH / "tests" / "mdl" / "test_int.mdl")
        with (
            patch.object(Ar, "GetResolver") as resolver,
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.mdl.settings.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            resolver.return_value.Resolve.side_effect = lambda path: path if path == mdl_path else ""
            mdl_settings.set_mdl_catalog_modules(["bad.txt", mdl_path, "missing.mdl"])
            result = mdl_settings.get_mdl_catalog_modules()
            self.assertEqual(result, [mdl_path])
            self.assertTrue(log_warn.called)

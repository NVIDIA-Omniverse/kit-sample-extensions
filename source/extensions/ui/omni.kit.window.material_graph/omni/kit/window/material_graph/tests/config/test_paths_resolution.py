# pylint: disable=relative-beyond-top-level
import tempfile
from pathlib import Path

from ...scripts.config.paths import Paths, _find_extension_root
from ..base import MaterialGraphTestBase


class TestPathsResolution(MaterialGraphTestBase):
    """Paths.EXT_PATH and _find_extension_root resolve the extension root so config and assets can
    be loaded. We test that the resolved path contains the manifest and that _find_extension_root
    falls back to the start path when no manifest is found (e.g. in a temp tree)."""

    async def test_extension_root_contains_manifest(self) -> None:
        """EXT_PATH resolves to extension root with manifest."""
        manifest = Path(Paths.EXT_PATH) / "config" / "extension.toml"
        self.assertTrue(manifest.exists())

    async def test_docs_url_uses_public_guide(self) -> None:
        """DOCS_URL resolves to the canonical public Material Graph guide."""
        self.assertEqual(
            Paths.DOCS_URL,
            "https://docs.omniverse.nvidia.com/extensions/latest/ext_material/ext_material-graph.html",
        )

    async def test_find_extension_root_fallbacks_to_start(self) -> None:
        """No manifest: returns start path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            start = Path(temp_dir) / "nested"
            start.mkdir(parents=True, exist_ok=True)
            self.assertEqual(_find_extension_root(start), start)

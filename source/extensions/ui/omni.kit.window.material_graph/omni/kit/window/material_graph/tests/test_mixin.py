import pathlib
from pathlib import Path
from typing import Sequence

import carb.settings
import omni.kit.app
import omni.usd
from omni.kit.test_suite.helpers import open_stage, select_prims, wait_stage_loading
from pxr import Sdf, Usd

from ..scripts.config.paths import Paths
from ..scripts.settings.settings import Settings
from ..scripts.settings.utils import TEST_SETTINGS_PATH


class MaterialGraphTestMixin:
    """Shared setup/teardown helpers for UI and non-UI tests."""

    MODULE_ID = Paths.MODULE_ID

    async def _setup_common(self, create_stage: bool = True) -> None:
        """Initialize shared test state and optionally create a stage."""
        self._app = omni.kit.app.get_app()
        self._ext_path = self._get_extension_path()
        self._test_data_dir = Path(self._ext_path) / "data" / "tests"
        self._usd_dir = self._test_data_dir / "usd"
        self._settings = carb.settings.get_settings()
        self._usd_context = omni.usd.get_context()
        if create_stage and self._usd_context:
            await self._usd_context.new_stage_async()
        self._stage = self._usd_context.get_stage() if self._usd_context else None

    async def _teardown_common(self) -> None:
        """Restore settings and close the stage."""
        self._settings.destroy_item(TEST_SETTINGS_PATH)
        if self._usd_context and self._usd_context.get_stage():
            await self._usd_context.close_stage_async()
        self._settings = None
        self._usd_context = None
        self._app = None
        self._ext_path = None
        self._test_data_dir = None
        self._usd_dir = None
        self._stage = None

    def _get_scene_path(self, file_name: str) -> str:
        """Return the resolved path to a test USD scene."""
        path = str(self._usd_dir / file_name)
        self.assertTrue(Path(path).exists())
        return path

    async def _load_scene(self, file_name: str) -> None:
        """Load a USD scene into the active context."""
        path = self._get_scene_path(file_name)
        await open_stage(path, self._usd_context)
        await wait_stage_loading()
        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

    async def _select_prims(self, prim_paths: Sequence[str]) -> None:
        """Select prim paths in the USD context."""
        await select_prims(prim_paths)
        await wait_stage_loading()

    def _get_prim_at_path(self, path: Sdf.Path) -> Usd.Prim:
        """Return a valid prim at the given path."""
        prim = self._stage.GetPrimAtPath(path)
        self.assertTrue(isinstance(prim, Usd.Prim) and prim.IsValid())
        return prim

    def _get_attribute_at_path(self, path: Sdf.Path) -> Usd.Attribute:
        """Return a valid attribute at the given path."""
        attribute = self._stage.GetAttributeAtPath(path)
        self.assertTrue(isinstance(attribute, Usd.Attribute) and attribute.IsValid())
        return attribute

    def _get_selected_prim_paths(self) -> list[str]:
        """Return currently selected prim paths."""
        return self._usd_context.get_selection().get_selected_prim_paths()

    def _get_extension_path(self) -> pathlib.Path:
        """Resolve the extension path from the extension manager."""
        ext_manager = self._app.get_extension_manager()
        ext_path = ext_manager.get_extension_path_by_module(self.MODULE_ID)
        if not ext_path:
            return pathlib.Path(__file__).resolve().parents[2]
        return pathlib.Path(ext_path)

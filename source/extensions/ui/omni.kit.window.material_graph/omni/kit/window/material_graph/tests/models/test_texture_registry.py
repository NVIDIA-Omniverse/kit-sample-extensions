# pylint: disable=relative-beyond-top-level,protected-access
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from ...scripts.models.catalog.registries.texture import TextureRegistry
from ...scripts.models.catalog.registries.texture import registry as texture_registry
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestTextureRegistry(MaterialGraphTestBase):
    """Texture registry persistence coverage."""

    async def setUp(self) -> None:
        await super().setUp()
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._settings.set_string(Settings.CATALOG_TEXTURES_PATH, self._tmp_dir.name)

    async def tearDown(self) -> None:
        try:
            self._tmp_dir.cleanup()
        finally:
            await super().tearDown()

    async def test_add_texture_writes_metadata(self) -> None:
        """Adding a texture should persist JSON metadata."""
        texture_path = Path(self._tmp_dir.name) / "example.png"
        texture_path.write_text("dummy", encoding="utf-8")
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
            item = registry.add_texture(str(texture_path), name="Example")
            self.assertIsNotNone(item)
            metadata = list(Path(self._tmp_dir.name).glob("*.json"))
            self.assertEqual(len(metadata), 1)
            payload = json.loads(metadata[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "Example")
            self.assertEqual(payload["source"], str(texture_path))
            registry.destroy()

    async def test_refresh_marks_missing_textures_invalid(self) -> None:
        """Missing texture sources should be flagged invalid."""
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
        payload = {
            "id": "deadbeef",
            "name": "Missing",
            "source": str(Path(self._tmp_dir.name) / "missing.png"),
            "icon": "",
        }
        json_path = Path(self._tmp_dir.name) / "deadbeef.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")
        registry.refresh()
        items = registry.get_items()
        self.assertEqual(len(items), 1)
        results = texture_registry._validate_items(items, self._tmp_dir.name)
        self.assertFalse(results[0]["valid"])
        registry.destroy()

    async def test_async_validation_updates_in_place_without_refresh_loop(self) -> None:
        """Invalid textures stay invalid without rescheduling validation forever."""
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
        payload = {
            "name": "Missing",
            "source": str(Path(self._tmp_dir.name) / "missing.png"),
            "icon": "",
        }
        item = texture_registry._load_texture_item(self._tmp_dir.name, payload)
        self.assertIsNotNone(item)
        registry._items = [item]
        reload_callback = MagicMock()
        registry.set_reload_callback(reload_callback)

        with patch.object(registry, "refresh", wraps=registry.refresh) as refresh:
            registry._schedule_validation()
            task = registry._lifecycle._tasks[-1]
            await task
            await self.wait_n_updates(3)

        self.assertFalse(item.is_valid)
        refresh.assert_not_called()
        reload_callback.assert_called_once_with()
        self.assertEqual(registry._lifecycle._tasks, [])
        self.assertEqual(registry._validation_generation, 1)
        registry.destroy()

    async def test_group_persistence_and_rename(self) -> None:
        """Groups should persist and update texture assignments."""
        texture_path = Path(self._tmp_dir.name) / "grouped.png"
        texture_path.write_text("dummy", encoding="utf-8")
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
            registry.create_group("GroupA")
            item = registry.add_texture(str(texture_path), name="Grouped")
            self.assertIsNotNone(item)
            registry.assign_group(item, "GroupA")
            registry.rename_group("GroupA", "GroupB")
            groups_path = Path(self._tmp_dir.name) / "texture_groups.json"
            groups = json.loads(groups_path.read_text(encoding="utf-8"))
            self.assertIn("GroupB", groups)
            json_path = Path(self._tmp_dir.name) / f"{texture_registry._texture_id(str(texture_path))}.json"
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["group"], "GroupB")
            registry.destroy()

    async def test_remove_group_deletes_textures(self) -> None:
        """Removing a group should delete its textures."""
        texture_path = Path(self._tmp_dir.name) / "toremove.png"
        texture_path.write_text("dummy", encoding="utf-8")
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
            registry.create_group("DeleteMe")
            item = registry.add_texture(str(texture_path), name="ToRemove")
            registry.assign_group(item, "DeleteMe")
            registry.remove_group("DeleteMe")
            json_path = Path(self._tmp_dir.name) / f"{texture_registry._texture_id(str(texture_path))}.json"
            self.assertFalse(json_path.exists())
            registry.destroy()

    async def test_invalid_groups_file_ignored(self) -> None:
        """Invalid group metadata should not break refresh."""
        groups_path = Path(self._tmp_dir.name) / "texture_groups.json"
        groups_path.write_text("{", encoding="utf-8")
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
        registry.refresh()
        self.assertEqual(registry.get_groups(), [])
        registry.destroy()

    async def test_lookup_group_items_rename_and_remove_texture(self) -> None:
        """Lookup and group projections should track persisted rename/removal operations."""
        texture_path = Path(self._tmp_dir.name) / "managed.png"
        texture_path.write_text("dummy", encoding="utf-8")
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
            registry.create_group("Managed")
            item = registry.add_texture(str(texture_path), name="Before")
            self.assertIsNotNone(item)
            self.assertTrue(registry.assign_group(item, "Managed"))
            self.assertTrue(registry.has_texture(str(texture_path)))
            self.assertIs(registry.get_item_by_source(str(texture_path)), registry.get_items()[0])
            group = registry.get_group_items()[0]
            self.assertTrue(group.is_texture_group)
            self.assertEqual([child.name for child in group.children], ["Before"])

            item = registry.get_item_by_source(str(texture_path))
            registry.rename_texture(item, "After")
            renamed = registry.get_item_by_source(str(texture_path))
            self.assertEqual(renamed.name, "After")
            registry.remove_texture(renamed)
            self.assertFalse(registry.has_texture(str(texture_path)))
            registry.remove_texture(None)
            registry.destroy()

    async def test_group_rename_rolls_back_partial_item_updates(self) -> None:
        """A failed group rename should restore every item already moved."""
        registry = object.__new__(TextureRegistry)
        first = SimpleNamespace(name="First", group="Old", source_path="first.png")
        second = SimpleNamespace(name="Second", group="Old", source_path="second.png")
        registry._groups = ["Old"]
        registry._items = [first, second]
        registry.refresh = MagicMock()
        registry._write_texture_group = MagicMock(side_effect=[True, False, True])
        with patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name):
            registry.rename_group("Old", "New")
        self.assertEqual(
            registry._write_texture_group.call_args_list,
            [
                call(first, "New", self._tmp_dir.name),
                call(second, "New", self._tmp_dir.name),
                call(first, "Old", self._tmp_dir.name),
            ],
        )
        registry.refresh.assert_called_once_with()
        self.assertEqual(registry._groups, ["Old"])

    async def test_group_manifest_failure_rolls_back_items_and_assignment(self) -> None:
        """Manifest failures should not leave item metadata in an unlisted group."""
        registry = object.__new__(TextureRegistry)
        item = SimpleNamespace(name="Item", group="Old", source_path="item.png")
        registry._groups = ["Old"]
        registry._items = [item]
        registry.refresh = MagicMock()
        registry._write_texture_group = MagicMock(return_value=True)
        with (
            patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name),
            patch.object(texture_registry, "_save_groups", return_value=False),
        ):
            registry.rename_group("Old", "New")
        self.assertEqual(registry._write_texture_group.call_count, 2)
        registry.refresh.assert_called_once_with()

        registry.refresh.reset_mock()
        registry._groups = []
        registry._write_texture_group.reset_mock(return_value=True)
        with (
            patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name),
            patch.object(texture_registry, "_save_groups", return_value=False),
        ):
            self.assertFalse(registry.assign_group(item, "Unpersisted"))
        registry.refresh.assert_called_once_with()

    async def test_scheduled_refresh_and_settings_callback_coalesce_through_lifecycle(self) -> None:
        """Deferred and settings-triggered refresh paths should both invoke registry refresh."""
        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
        registry.refresh = MagicMock()
        registry._schedule_refresh()
        task = registry._lifecycle._tasks[-1]
        await task
        registry.refresh.assert_called_once_with()
        registry.refresh.reset_mock()
        registry._on_settings_changed(None, None, None)
        registry.refresh.assert_called_once_with()
        registry.destroy()

    async def test_local_directory_and_global_registry_lifecycle(self) -> None:
        """Remote roots are rejected and the global registry must be destroyable and replaceable."""
        self.assertFalse(texture_registry._ensure_local_dir("omniverse://server/folder"))
        with patch.object(Path, "mkdir", side_effect=OSError("read only")):
            self.assertFalse(texture_registry._ensure_local_dir(self._tmp_dir.name))

        sentinel = SimpleNamespace(destroy=MagicMock())
        texture_registry._TEXTURE_REGISTRY = sentinel
        self.assertIs(texture_registry.get_texture_registry(), sentinel)
        texture_registry.destroy_texture_registry()
        sentinel.destroy.assert_called_once_with()
        self.assertIsNone(texture_registry._TEXTURE_REGISTRY)

    async def test_texture_persistence_failure_boundaries(self) -> None:
        """Invalid roots and filesystem failures must not leave optimistic registry state."""
        registry = object.__new__(TextureRegistry)
        registry._items = []
        registry._groups = []
        registry._lifecycle = None
        registry._schedule_refresh = MagicMock()
        registry.refresh = MagicMock()

        self.assertIsNone(registry.add_texture(""))
        with patch.object(texture_registry, "_get_icons_root", return_value=""):
            self.assertIsNone(registry.add_texture("source.png"))
            registry.remove_texture(SimpleNamespace(source_path="source.png"))
            registry.rename_texture(SimpleNamespace(source_path="source.png"), "New")
            registry.rename_group("Old", "New")
            self.assertFalse(registry.assign_group(SimpleNamespace(), "Group"))

        with (
            patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name),
            patch.object(texture_registry, "_ensure_local_dir", return_value=False),
        ):
            self.assertIsNone(registry.add_texture("source.png"))

        with (
            patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name),
            patch.object(Path, "write_text", side_effect=OSError("read only")),
        ):
            self.assertIsNone(registry.add_texture("source.png"))

        item = SimpleNamespace(source_path="missing.png", group="", name="Missing")
        self.assertFalse(registry._write_texture_group(item, "Group", self._tmp_dir.name))
        metadata_path = Path(self._tmp_dir.name) / f"{texture_registry._texture_id(item.source_path)}.json"
        metadata_path.write_text("{", encoding="utf-8")
        self.assertFalse(registry._write_texture_group(item, "Group", self._tmp_dir.name))

    async def test_texture_group_guard_and_rollback_boundaries(self) -> None:
        """Group mutations reject invalid requests and preserve manifests on failures."""
        registry = object.__new__(TextureRegistry)
        registry._groups = ["Old", "Existing"]
        registry._items = []
        registry.refresh = MagicMock()
        registry._write_texture_group = MagicMock(return_value=False)

        for old_name, new_name in (("", "New"), ("Old", ""), ("Old", "Old"), ("Missing", "New"), ("Old", "Existing")):
            registry.rename_group(old_name, new_name)
        registry._write_texture_group.assert_not_called()

        registry.create_group("")
        registry.create_group("Old")
        registry.remove_group("")
        registry.remove_group("Missing")
        self.assertEqual(registry._groups, ["Old", "Existing"])

        item = SimpleNamespace(source_path="item.png", group="Old", name="Item")
        registry._items = [item]
        with patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name):
            registry.rename_group("Old", "New")
        registry.refresh.assert_called_once_with()

        registry.refresh.reset_mock()
        with (
            patch.object(texture_registry, "_get_icons_root", return_value=self._tmp_dir.name),
            patch.object(texture_registry, "_save_groups", return_value=False),
        ):
            registry.remove_group("Old")
        registry.refresh.assert_called_once_with()

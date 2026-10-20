# pylint: disable=relative-beyond-top-level
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.items.compound import CompoundItem
from ...scripts.models.catalog.registries.compound.discovery import _compound_key
from ...scripts.models.catalog.registries.compound.registry import CompoundRegistry
from ..base import MaterialGraphTestBase


class TestCompoundRegistry(MaterialGraphTestBase):
    """Compound registry lifecycle coverage."""

    async def test_destroy_cleans_up(self) -> None:
        """Destroy should unsubscribe and leave the registry empty."""
        dummy_sub = MagicMock()

        module_id = Paths.MODULE_ID
        with (
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.Settings.get_compound_paths",
                autospec=True,
                return_value=[],
            ),
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.get_eventdispatcher",
                autospec=True,
            ) as get_dispatcher,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.carb.settings.get_settings",
                autospec=True,
            ) as get_settings,
        ):
            get_dispatcher.return_value.observe_event.return_value = dummy_sub
            get_settings.return_value.subscribe_to_tree_change_events.return_value = dummy_sub
            registry = CompoundRegistry()
            registry.destroy()

        self.assertEqual(registry.get_items(), [])

    async def test_remove_compound_deletes_file(self) -> None:
        """Removing a compound should delete the source file."""
        dummy_sub = MagicMock()
        module_id = Paths.MODULE_ID
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.Settings.get_compound_paths",
                autospec=True,
                return_value=[],
            ),
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.get_eventdispatcher",
                autospec=True,
            ) as get_dispatcher,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.carb.settings.get_settings",
                autospec=True,
            ) as get_settings,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.metadata.utils.COMPOUND_DEFAULT_PATH",
                temp_dir,
            ),
        ):
            get_dispatcher.return_value.observe_event.return_value = dummy_sub
            get_settings.return_value.subscribe_to_tree_change_events.return_value = dummy_sub
            registry = CompoundRegistry()
            compound_path = Path(temp_dir) / "compound.usda"
            compound_path.write_text("#usda 1.0", encoding="utf-8")
            item = CompoundItem(
                name="CompoundA",
                info="info",
                icon="",
                tooltip="tooltip",
                source_asset=str(compound_path),
                identifier="/GraphA",
                context_visibility=["mdl"],
            )
            registry.remove_compound(item)
            self.assertFalse(compound_path.exists())

    async def test_remove_compound_failure_preserves_metadata(self) -> None:
        """Failed local and remote deletion must not orphan the catalog metadata."""
        registry = CompoundRegistry.__new__(CompoundRegistry)
        item = CompoundItem(
            name="CompoundA",
            info="info",
            icon="",
            tooltip="tooltip",
            source_asset="omniverse://missing/compound.usda",
            identifier="/GraphA",
            context_visibility=["mdl"],
        )
        key = _compound_key(item.source_asset, item.identifier)
        registry._metadata = {key: {"group": "KeepMe"}}
        registry._save_metadata_and_refresh = MagicMock(return_value=True)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.catalog.registries.compound.registry.omni.client.delete",
            return_value=MagicMock(),
        ):
            self.assertFalse(registry.remove_compound(item))

        self.assertIn(key, registry._metadata)
        registry._save_metadata_and_refresh.assert_not_called()

    async def test_invalid_group_metadata_falls_back(self) -> None:
        """Invalid group metadata should be ignored."""
        dummy_sub = MagicMock()
        module_id = Paths.MODULE_ID
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.Settings.get_compound_paths",
                autospec=True,
                return_value=[],
            ),
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.get_eventdispatcher",
                autospec=True,
            ) as get_dispatcher,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.registry.carb.settings.get_settings",
                autospec=True,
            ) as get_settings,
            patch(
                f"{module_id}.scripts.models.catalog.registries.compound.metadata.utils.COMPOUND_DEFAULT_PATH",
                temp_dir,
            ),
        ):
            get_dispatcher.return_value.observe_event.return_value = dummy_sub
            get_settings.return_value.subscribe_to_tree_change_events.return_value = dummy_sub
            groups_path = Path(temp_dir) / "compound_groups.json"
            groups_path.write_text("{", encoding="utf-8")
            registry = CompoundRegistry()
            self.assertEqual(registry.get_groups(), [])
            registry.destroy()

    async def test_group_lookup_and_metadata_mutations(self) -> None:
        """Group projections, lookup, and metadata edits should remain mutually consistent."""
        first = CompoundItem("Zulu", "", "", "", "asset.usda", "/First", ["mdl"], "Old")
        second = CompoundItem("Alpha", "", "", "", "asset.usda", "/Second", ["mdl"], "Old")
        registry = CompoundRegistry.__new__(CompoundRegistry)
        registry._items = [first, second]
        registry._groups = ["Old"]
        registry._metadata = {
            _compound_key(first.source_asset, first.identifier): {"group": "Old"},
            _compound_key(second.source_asset, second.identifier): {"group": "Old"},
        }
        registry._save_metadata_and_refresh = MagicMock(return_value=True)

        groups = registry.get_group_items()
        self.assertEqual([item.name for item in groups[0].children], ["Alpha", "Zulu"])
        self.assertTrue(groups[0].is_compound_group)
        self.assertIs(registry.get_item_by_identifier("asset.usda", "/First"), first)
        self.assertIsNone(registry.get_item_by_identifier("missing.usda", "/First"))

        registry.rename_group("Old", "New")
        self.assertEqual(registry.get_groups(), ["New"])
        self.assertTrue(all(entry["group"] == "New" for entry in registry._metadata.values()))
        registry.assign_group(first, "Extra")
        self.assertIn("Extra", registry.get_groups())
        registry.rename_compound(first, "Renamed")
        key = _compound_key(first.source_asset, first.identifier)
        self.assertEqual(registry._metadata[key]["name"], "Renamed")
        registry.remove_group("New")
        self.assertNotIn("New", registry.get_groups())
        self.assertEqual(registry._metadata[_compound_key(second.source_asset, second.identifier)]["group"], "")
        self.assertEqual(registry._save_metadata_and_refresh.call_count, 4)

    async def test_group_mutation_invalid_inputs_are_noops(self) -> None:
        """Invalid group and compound edits must not persist partial metadata."""
        item = CompoundItem("Compound", "", "", "", "asset.usda", "/Graph", [], "Group")
        registry = CompoundRegistry.__new__(CompoundRegistry)
        registry._items = [item]
        registry._groups = ["Group", "Existing"]
        registry._metadata = {}
        registry._save_metadata_and_refresh = MagicMock(return_value=True)

        for name in ("", "  ", "Group"):
            registry.create_group(name)
        registry.rename_group("", "New")
        registry.rename_group("Missing", "New")
        registry.rename_group("Group", "Existing")
        registry.remove_group("")
        registry.remove_group("Missing")
        self.assertFalse(registry.assign_group(None, "Group"))
        registry.rename_compound(None, "New")
        registry.rename_compound(item, " ")
        self.assertFalse(registry.remove_compound(None))

        registry._save_metadata_and_refresh.assert_not_called()

    async def test_file_save_listener_filters_and_contains_malformed_events(self) -> None:
        """Only saved compound files within configured roots should trigger a refresh."""
        registry = CompoundRegistry.__new__(CompoundRegistry)
        registry.refresh = MagicMock()

        registry._on_file_saved({})
        registry._on_file_saved(None)
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.models.catalog.registries.compound.registry._is_compound_file",
                side_effect=lambda url: str(url).endswith(".usda"),
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.models.catalog.registries.compound.registry._is_in_compound_paths",
                return_value=True,
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.models.catalog.registries.compound.registry.Settings.get_compound_paths",
                return_value=["/compounds"],
            ),
        ):
            registry._on_file_saved({"url": ""})
            registry._on_file_saved({"url": "/compounds/readme.txt"})
            registry._on_file_saved({"url": "/compounds/node.usda"})

        registry.refresh.assert_called_once_with()

# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""What the scan progress popup reports: the found and resolved counters."""

import tempfile
from pathlib import Path

import carb.settings
import omni.kit.test

from ..models import FileSystemFile, FileSystemFolder, TreeFolderBrowserModel
from ..models.traverse_context import TraverseContext, TraverseState

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/progress_root"


class TestTraverseProgress(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        # Three files the browser wants, two it does not - the shape that matters, because a real
        # scan walks far more files than it will ever show.
        for name in ("a.usd", "b.usd", "readme.txt", "lib.dll"):
            (root / name).write_text("x", encoding="utf-8")
        sub = root / "sub"
        sub.mkdir()
        (sub / "c.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    async def test_a_finished_collection_stops_spinning(self):
        """
        A collection that finishes having found something must repaint its row.

        The delegate builds its rotating spinner in build_widget and stops it only when the row is
        rebuilt, so clearing the loading flag achieves nothing on its own. folder_changed used to
        repaint a non-hidden root only when the traverse found *no* updates, which meant a
        collection that scanned a whole drive kept spinning after it had finished.
        """
        import omni.kit.app

        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        # Build the category items so the collection has a row that can spin.
        for collection in model.get_item_children(None):
            model.get_item_children(collection)

        folder = model.get_root_folder(self._root)
        model.start_traverse(folder)

        changed = []
        sub = model.subscribe_item_changed_fn(lambda _m, i: changed.append(i))  # noqa: F841

        for _ in range(600):
            await omni.kit.app.get_app().next_update_async()
            if folder.prepared and not model.active_folders:
                break
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

        item = model._folder_cache.get(folder, None)
        self.assertIsNotNone(item, "the collection lost its category item")
        self.assertTrue(folder.has_update, "this tree has materials, so the traverse found updates")
        self.assertFalse(item.loading, "the loading flag was left set")
        self.assertIn(item, changed, "nothing repainted the row, so the spinner keeps turning")

        del sub
        model.destroy()

    async def _traverse(self):
        """Traverse the temp root with a context attached, exactly as the model wires one up."""
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        folder = model.get_root_folder(self._root)
        model._register_active_folder(folder)
        return model, folder

    async def test_counts_only_files_the_browser_wants(self):
        """readme.txt and lib.dll are walked but must not be reported as progress."""
        model, folder = await self._traverse()
        await folder.start_traverse()

        ctx = folder.traverse_ctx
        self.assertEqual(ctx.files_found, 3, "expected the three .usd files, not every entry")
        self.assertEqual(ctx.files_resolved, 3, "resolved must reach found, not overrun it")
        # One browsable item per file here: plain FileSystemFile carries no sub items.
        self.assertEqual(ctx.items_resolved, 3)

        model.destroy()

    async def test_items_counted_per_item_not_per_file(self):
        """A file worth several browsable items - a .usd holding many materials - counts as many."""
        model, folder = await self._traverse()

        original = folder.create_file_object

        def multi(url):
            file = original(url)
            if file is not None and url.endswith("a.usd"):
                # Stand in for a material file holding four material prims.
                file.__class__ = _MultiItemFile
            return file

        folder.create_file_object = multi
        await folder.start_traverse()

        ctx = folder.traverse_ctx
        self.assertEqual(ctx.files_resolved, 3, "still three files")
        self.assertEqual(ctx.items_resolved, 6, "a.usd is worth four items, the other two one each")

        model.destroy()

    async def test_found_leads_resolved(self):
        """
        Found is published per listing, so it runs ahead of resolved.

        Incrementing the two a line apart pinned them together and showed the same number in both
        columns; this asserts the lead directly, at the moment the first file is resolved.
        """
        model, folder = await self._traverse()

        seen = []
        original = folder._on_file_found_async

        async def record(url):
            ctx = folder.traverse_ctx
            seen.append((ctx.files_found, ctx.files_resolved))
            return await original(url)

        folder._on_file_found_async = record
        await folder.start_traverse()

        self.assertTrue(seen, "no files were resolved")
        found_at_first, resolved_at_first = seen[0]
        self.assertEqual(resolved_at_first, 0)
        self.assertEqual(found_at_first, 2, "both .usd files in the root are found before either resolves")

        model.destroy()

    async def test_bulk_counter_ignores_empty_folders(self):
        """A folder with nothing wanted must not notify, or the popup flickers on every .dll dir."""
        ticks = []
        ctx = TraverseContext(_FakeFolder(), on_progress_fn=lambda c: ticks.append(c.files_found))
        ctx.note_files_found(0)
        self.assertEqual(ctx.files_found, 0)
        self.assertEqual(ticks, [])

        ctx.note_files_found(5)
        self.assertEqual(ctx.files_found, 5)
        self.assertEqual(ticks, [5])
        self.assertIs(ctx.state, TraverseState.QUEUED)

        ctx.note_items_resolved(0)
        self.assertEqual(ctx.items_resolved, 0)
        ctx.note_items_resolved(3)
        self.assertEqual(ctx.items_resolved, 3)


class _FakeFolder:
    name = "fake"
    url = "omniverse://server/fake"


class _MultiItemFile(FileSystemFile):
    """A file that shows up as more than one entry, the way a multi material .usd does."""

    @property
    def _item_count(self) -> int:
        return 4


class TestDroppedFiles(omni.kit.test.AsyncTestCase):
    """
    Files counted and then refused by the browser.

    A browser that hides files without a thumbnail rejects them after they have been walked and
    counted, so the counters have to give them back - otherwise the window promises items that
    never appear.
    """

    async def test_dropping_files_reports_the_new_totals(self):
        folder = FileSystemFolder("root", "C:/root")
        ctx = TraverseContext(folder)
        ctx.note_files_found(10)
        for _ in range(10):
            ctx.note_file_resolved()
        ctx.note_items_resolved(20)

        # Ran into an attribute that does not exist, so this never worked at all.
        ctx.note_files_dropped(4, 8)

        self.assertEqual(ctx.files_found, 6)
        self.assertEqual(ctx.files_resolved, 6)
        self.assertEqual(ctx.items_resolved, 12)

    async def test_dropping_more_than_was_counted_does_not_go_negative(self):
        folder = FileSystemFolder("root", "C:/root")
        ctx = TraverseContext(folder)
        ctx.note_files_found(1)
        ctx.note_files_dropped(5, 5)
        self.assertEqual(ctx.files_found, 0)
        self.assertEqual(ctx.items_resolved, 0)


class TestScanProgressWindowTeardown(omni.kit.test.AsyncTestCase):
    """The window is destroyed by whichever of the widget and the app gets there first - or both."""

    async def test_destroy_twice(self):
        from ..widgets.scan_progress_window import ScanProgressWindow

        settings = carb.settings.get_settings()
        settings.set(SETTING_ROOT, [])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        window = ScanProgressWindow(model)
        try:
            window.destroy()
            window.destroy()  # the model is gone by now, and this used to raise AttributeError
            self.assertFalse(window.visible, "the window is still showing after being destroyed")
        finally:
            model.destroy()

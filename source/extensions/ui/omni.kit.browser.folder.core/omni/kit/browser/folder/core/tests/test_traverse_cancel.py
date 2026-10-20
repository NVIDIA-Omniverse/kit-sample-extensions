# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""Cancelling a scan."""

import tempfile
import time
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel
from ..models.traverse_context import TraverseState

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/cancel_root"
FOLDERS = 60
FILES_PER_FOLDER = 10


class TestTraverseCancel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        # Big enough that a cancel lands mid-scan rather than after it.
        for d in range(FOLDERS):
            sub = root / f"folder_{d:02d}"
            sub.mkdir()
            for f in range(FILES_PER_FOLDER):
                (sub / f"mat_{f}.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()

    async def tearDown(self):
        self._tmp.cleanup()

    def _model(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root])
        return TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])

    async def _until(self, predicate, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            await omni.kit.app.get_app().next_update_async()
            if predicate():
                return True
        return False

    async def test_cancel_stops_a_running_scan(self):
        model = self._model()
        folder = await self._wait_for_root(model)

        started = await self._until(
            lambda: folder.traverse_ctx is not None
            and folder.traverse_ctx.state in (TraverseState.SCANNING, TraverseState.REFRESHING)
        )
        self.assertTrue(started, "the scan never started")

        self.assertTrue(model._cancel_traverse(self._root), "_cancel_traverse did not take effect")
        ctx = folder.traverse_ctx
        self.assertIs(ctx.state, TraverseState.CANCELLED)
        self.assertTrue(ctx.cancelled)
        self.assertIsNone(ctx.result, "a cancelled traverse reached no result")

        # The row goes immediately; the task unwinds on its own afterwards.
        self.assertNotIn(folder, model.active_folders)
        self.assertTrue(
            await self._until(lambda: ctx.task is None or ctx.task.done()), "the traverse task never unwound"
        )

        model.destroy()

    async def test_cancel_is_first_wins(self):
        """A second cancel, or one racing a completion, must not clean up twice."""
        model = self._model()
        folder = await self._wait_for_root(model)

        first = model._cancel_traverse(self._root)
        second = model._cancel_traverse(self._root)
        self.assertTrue(first)
        self.assertFalse(second, "the second cancel must be a no-op")

        model.destroy()

    async def test_cancel_leaves_the_worker_alive(self):
        """Cancelling one collection must not stop the queue: CancelledError is a BaseException."""
        model = self._model()
        folder = await self._wait_for_root(model)
        model._cancel_traverse(self._root)

        # Queue the same collection again; a dead worker would never pick it up.
        await self._until(lambda: folder.traverse_ctx.task is None or folder.traverse_ctx.task.done())
        model.start_traverse(folder, force=True)
        restarted = await self._until(
            lambda: folder.traverse_ctx is not None and not folder.traverse_ctx.is_terminal, timeout=30
        )
        self.assertTrue(restarted, "the worker did not survive the cancel")

        model.destroy()

    async def test_cancel_does_not_cache_a_partial_scan(self):
        """A cancelled scan must not be written to the cache as if it were the whole collection."""
        model = self._model()
        folder = await self._wait_for_root(model)

        saved = []
        model._save_data_to_json = lambda f: saved.append(f)
        model._cancel_traverse(self._root)
        self.assertEqual(saved, [], "a cancelled traverse wrote a cache entry")

        model.destroy()

    async def test_removing_a_collection_cancels_it(self):
        model = self._model()
        folder = await self._wait_for_root(model)
        ctx = folder.traverse_ctx

        self.assertTrue(model.remove_root_folder(self._root))
        self.assertIs(ctx.state, TraverseState.CANCELLED, "removal left the scan running")
        self.assertNotIn(folder, model.active_folders)

        model.destroy()

    async def test_cancel_stops_the_category_spinner(self):
        """
        Clearing `loading` is not enough.

        The category delegate builds its rotating spinner in build_widget and only stops it when
        the row is rebuilt, so a cancel that clears the flag without asking for a repaint leaves
        the collection spinning forever.
        """
        model = self._model()
        folder = await self._wait_for_root(model)
        # Build the category items, so the collection has a row that can spin.
        for collection in model.get_item_children(None):
            model.get_item_children(collection)
        item = model._folder_cache.get(folder, None)
        self.assertIsNotNone(item, "the collection has no category item")
        self.assertTrue(await self._until(lambda: item.loading), "the row never showed as loading")

        changed = []
        sub = model.subscribe_item_changed_fn(lambda _m, i: changed.append(i))  # noqa: F841

        model._cancel_traverse(self._root)

        self.assertFalse(item.loading, "the loading flag was left set")
        self.assertIn(item, changed, "nothing asked the tree to repaint, so the spinner keeps turning")

        del sub
        model.destroy()

    async def test_cancel_does_not_restart_the_scan(self):
        """
        A cancelled collection must stay cancelled.

        `prepared` is what the browser reads to decide whether a collection still needs scanning,
        and a cancelled traverse never reaches the code that sets it. So the flag stayed False, the
        next category rebuild re-queued the collection, and cancelling a drive scan turned into
        Pending followed by a fresh scan of the whole tree - the opposite of what was asked for.
        """
        model = self._model()
        folder = await self._wait_for_root(model)
        await self._until(lambda: folder.traverse_ctx.state in (TraverseState.SCANNING, TraverseState.REFRESHING))
        self.assertTrue(model._cancel_traverse(self._root))
        self.assertIs(folder.traverse_ctx.state, TraverseState.CANCELLED)

        # Everything the browser does that asks "does this need scanning?".
        for collection in model.get_item_children(None):
            model.get_item_children(collection)
        for _ in range(30):
            await omni.kit.app.get_app().next_update_async()

        self.assertTrue(folder.prepared, "a cancelled collection still looks unscanned")
        self.assertEqual(model.active_folders, [], "the collection was queued again after a cancel")
        self.assertIs(
            folder.traverse_ctx.state,
            TraverseState.CANCELLED,
            "the cancelled traverse was replaced by a new one",
        )

        model.destroy()

    async def test_a_cancelled_collection_reads_cancelled(self):
        """
        The row must not show a count after a cancel.

        A number claims the collection holds that many items; after a cancel it holds whatever had
        been found when the user stopped it, which reads as a finished scan. TIMEOUT already takes
        this line for the same reason.
        """
        from ..widgets.folder_category_delegate import FolderCategoryDelegate

        model = self._model()
        folder = await self._wait_for_root(model)
        for collection in model.get_item_children(None):
            model.get_item_children(collection)
        item = model._folder_cache.get(folder, None)
        self.assertIsNotNone(item, "the collection has no row")

        delegate = FolderCategoryDelegate()
        before = delegate.get_count(item)
        self.assertNotEqual(before, "Cancelled", "it should not read Cancelled before it is cancelled")

        self.assertTrue(model._cancel_traverse(self._root))
        self.assertEqual(delegate.get_count(item), "Cancelled")

        # A fresh traverse builds a fresh context, so the number comes back.
        model.start_traverse(folder, force=True)
        self.assertNotEqual(delegate.get_count(item), "Cancelled", "re-scanning must clear the word")

        model.destroy()

    async def test_cancel_stops_child_spinners_too(self):
        """
        Every row under a cancelled collection stops spinning, not just the collection's own.

        A sub folder part way through never receives its COMPLETED - the traverse was interrupted -
        so nothing clears its loading flag and its row spins on after the collection has stopped.
        """
        model = self._model()
        folder = await self._wait_for_root(model)
        for collection in model.get_item_children(None):
            model.get_item_children(collection)

        ctx = folder.traverse_ctx
        # Wait for the traverse to discover a sub folder, then give it the row it would have once
        # the category tree caught up. Building it here rather than waiting for the tree keeps the
        # test about the sweep instead of about how fast rows appear.
        from ..models.folder_browser_item import FolderCategoryItem

        found = await self._until(lambda: bool(folder.sub_folders), timeout=60)
        self.assertTrue(found, "the traverse never discovered a sub folder")
        child_folder = folder.sub_folders[0]
        child_folder.traverse_ctx = ctx
        child_item = FolderCategoryItem(child_folder.name, 0, child_folder)
        child_item.loading = True
        model._folder_cache[child_folder] = child_item

        self.assertTrue(model._cancel_traverse(self._root))

        self.assertFalse(child_item.loading, "a child row kept spinning after the collection stopped")
        self.assertFalse(model._folder_cache[folder].loading, "the collection's own row kept spinning")

        model.destroy()

    async def test_children_report_their_own_state_after_a_cancel(self):
        """
        Each row says what happened to *it*, not what happened to the collection.

        The whole sub tree shares the root's context, so keying the label off that would have made
        every child read Cancelled - including ones that had already finished and ones the traverse
        never reached. Three outcomes, three appearances: a finished child keeps its count, an
        interrupted child says Cancelled, and an untouched child stays blank (a zero count, which
        the delegate hides).
        """
        from ..models.folder_browser_item import FolderCategoryItem
        from ..widgets.folder_category_delegate import FolderCategoryDelegate

        model = self._model()
        folder = await self._wait_for_root(model)
        for collection in model.get_item_children(None):
            model.get_item_children(collection)
        ctx = folder.traverse_ctx

        self.assertTrue(await self._until(lambda: len(folder.sub_folders) >= 3, timeout=60))
        finished, interrupted, untouched = folder.sub_folders[:3]
        rows = {}
        for sub, loading, prepared, count in (
            (finished, False, True, 7),
            (interrupted, True, False, 2),
            (untouched, False, False, 0),
        ):
            sub.traverse_ctx = ctx
            sub.prepared = prepared
            sub.traverse_cancelled = False
            row = FolderCategoryItem(sub.name, count, sub)
            row.loading = loading
            model._folder_cache[sub] = row
            rows[sub] = row

        self.assertTrue(model._cancel_traverse(self._root))

        delegate = FolderCategoryDelegate()
        self.assertEqual(delegate.get_count(rows[finished]), 7, "a finished child lost its count")
        self.assertEqual(delegate.get_count(rows[interrupted]), "Cancelled", "an interrupted child hid it")
        self.assertEqual(delegate.get_count(rows[untouched]), 0, "an untouched child should stay blank")

        model.destroy()

    async def test_a_sub_folder_can_be_scanned_on_its_own(self):
        """
        Selecting an unscanned category traverses that folder - it must not be swallowed.

        The worker skipped anything not in _root_folders, on the assumption that only collections
        are queued. Sub folders are queued too: clicking one after cancelling its collection put it
        in the progress window as Pending, where it sat forever because the worker threw it away on
        dequeue.
        """
        model = self._model()
        folder = await self._wait_for_root(model)
        self.assertTrue(await self._until(lambda: bool(folder.sub_folders), timeout=60))
        child = folder.sub_folders[0]

        self.assertTrue(model._cancel_traverse(self._root))
        await self._until(lambda: folder.traverse_ctx.task is None or folder.traverse_ctx.task.done())

        # The context the cancelled root left on it. Anything that follows has to be a new one, or
        # "it started" is satisfied by the terminal state of the scan that was just stopped.
        cancelled_ctx = child.traverse_ctx

        child.prepared = False
        model.start_traverse(child)
        self.assertIn(child, model.active_folders, "the sub folder was not queued")
        self.assertIsNot(child.traverse_ctx, cancelled_ctx, "the sub folder kept the cancelled context")

        started = await self._until(
            lambda: child.traverse_ctx is not None
            and child.traverse_ctx is not cancelled_ctx
            and child.traverse_ctx.state is not TraverseState.QUEUED,
            timeout=60,
        )
        self.assertTrue(started, "the sub folder stayed Pending and never started")

        finished = await self._until(lambda: child not in model.active_folders, timeout=60)
        self.assertTrue(finished, "the sub folder never finished")

        model.destroy()

    async def test_selecting_inside_a_cancelled_collection_does_not_rescan(self):
        """
        A cancelled collection stays stopped, children included.

        Selecting an unscanned category normally traverses that folder. Inside a collection the user
        has just stopped, that turns a cancel into a scan starting again a moment later - which is
        what it looked like from the outside. The whole sub tree shares the collection's context, so
        one check covers every row under it. Refresh Current Collection is the way back.
        """
        from ..widgets.tree_folder_browser_widget import TreeFolderBrowserWidget

        model = self._model()
        folder = await self._wait_for_root(model)
        self.assertTrue(await self._until(lambda: bool(folder.sub_folders), timeout=60))
        child = folder.sub_folders[0]
        child.traverse_ctx = folder.traverse_ctx
        child.prepared = False

        # Before the cancel, selecting an unscanned child is meant to scan it.
        self.assertFalse(TreeFolderBrowserWidget._is_cancelled(child))

        self.assertTrue(model._cancel_traverse(self._root))

        self.assertTrue(
            TreeFolderBrowserWidget._is_cancelled(child),
            "a child of a cancelled collection should read as cancelled",
        )
        self.assertTrue(
            TreeFolderBrowserWidget._is_cancelled(folder),
            "the collection itself should read as cancelled",
        )

        # Refreshing builds a fresh context, which is what lets scanning start again.
        model.start_traverse(folder, force=True)
        self.assertFalse(TreeFolderBrowserWidget._is_cancelled(folder), "refresh should clear the cancelled state")

        model.destroy()

    async def _wait_for_root(self, model):
        """Get the root collection and queue it. Adding a collection does not scan it by itself."""
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        folder = model.get_root_folder(self._root)
        self.assertIsNotNone(folder, "the root collection was never created")
        model.start_traverse(folder)
        self.assertIsNotNone(folder.traverse_ctx, "start_traverse did not register a context")
        return folder


class TestConnectionFailure(omni.kit.test.AsyncTestCase):
    """
    A collection whose server never answers has to stop looking like it is working.

    Nothing else ends that traverse: the worker handed the folder to a connector and moved on, so
    when the connection fails this is the only place left to terminalize it - and the only place
    left to say so. _finish_traverse clears the loading flag and notifies nothing by design, which
    means a failure here that does not publish leaves the row exactly as it was, spinner turning.
    """

    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # Named, because the failure this drives is reported - and it should be. The folder's name
        # lands in both messages, which lets extension.toml exclude exactly these two lines from
        # the harness's "no [Error] in stdout" rule without excusing a real connection failure.
        self._root = Path(self._tmp.name) / "unreachable_server_probe"
        self._root.mkdir()
        carb.settings.get_settings().set(SETTING_ROOT, [])
        self._model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])

        # Record the report instead of posting it. The real one is a notification toast that
        # outlives the test by several seconds and is drawn over whatever the next test in this
        # process screenshots - which is how a golden image test three files away started failing.
        self._reported = []
        self._real_notify = self._model._notify_scan_failure
        self._model._notify_scan_failure = lambda folder, **kwargs: self._reported.append((folder, kwargs))

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        self._model._notify_scan_failure = self._real_notify
        self._model.destroy()
        self._tmp.cleanup()

    async def test_a_failed_connection_publishes_the_collection(self):
        folder = self._model.append_root_folder(self._root.as_posix(), save=False, sync=False)
        self._model._register_active_folder(folder)
        category_item = self._model.create_category_item(folder)
        category_item.loading = True
        self._model._folder_cache[folder] = category_item

        published = []
        real = self._model.folder_changed
        self._model.folder_changed = lambda item: (published.append(item), real(item))[1]
        try:
            self._model._on_server_connected(folder, False)
        finally:
            self._model.folder_changed = real

        self.assertIn(folder, published, "a failed connection never told the tree")
        self.assertEqual([f for f, _ in self._reported], [folder], "the user was never told the scan failed")
        self.assertFalse(category_item.loading, "the row was left loading")
        self.assertNotIn(folder, self._model.active_folders, "the collection stayed in the active list")

    async def test_publishing_happens_once(self):
        """Terminalizing is first-wins, and the publish follows it rather than the call."""
        folder = self._model.append_root_folder(self._root.as_posix(), save=False, sync=False)
        self._model._register_active_folder(folder)

        published = []
        real = self._model.folder_changed
        self._model.folder_changed = lambda item: (published.append(item), real(item))[1]
        try:
            self._model._on_server_connected(folder, False)
            self._model._on_server_connected(folder, False)
        finally:
            self._model.folder_changed = real

        self.assertEqual(len(published), 1, "a second failure published the collection again")


class TestWorkerTeardownIsQuiet(omni.kit.test.AsyncTestCase):
    """
    An app that never destroys the model must not make noise on its way out.

    Kit's test harness fails an extension on any [Error] in stdout, and a browser loaded through
    something else - as omni.flowusd.ui loads this one - is torn down by the loop cancelling its
    worker, with no destroy() and so no stop event. Reporting that as an error failed other
    extensions' ETM runs at shutdown, for a browser that was simply going away (OMPE-109433).
    """

    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        carb.settings.get_settings().set(SETTING_ROOT, [])
        self._model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        self._model.destroy()
        self._tmp.cleanup()

    async def test_a_cancel_without_destroy_is_not_an_error(self):
        logged = []
        real_error, real_warn = carb.log_error, carb.log_warn
        carb.log_error = lambda msg, *a, **k: logged.append(("error", msg))
        carb.log_warn = lambda msg, *a, **k: logged.append(("warn", msg))
        try:
            # What the loop does to a model nobody destroyed. destroy() is what sets the stop
            # event, so this is the shape with the flag clear.
            self._model._FolderBrowserModel__traverse_future.cancel()
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
        finally:
            carb.log_error, carb.log_warn = real_error, real_warn

        errors = [m for level, m in logged if level == "error"]
        self.assertEqual(errors, [], f"a teardown cancel logged an error: {errors}")
        self.assertTrue(
            any("cancelled" in m for _, m in logged),
            f"the cancel was not reported at all: {logged}",
        )

# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import asyncio
import pathlib

import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.test_suite.helpers import select_prims, wait_stage_loading
from omni.kit.ui_test import Vec2
from omni.ui.tests.test_base import OmniUiTest


class TestVariantPresenterWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        import omni.kit.variant.presenter as vp

        self._w = vp.get_window()
        self._m = vp.get_model()

        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        test_data_path = pathlib.Path(extension_path).joinpath("data").joinpath("tests")

        self.__golden_img_dir = test_data_path.absolute().joinpath("golden_img").absolute()
        self.__usd_path = str(test_data_path.joinpath("variant_test_stage.usda").absolute())

        await self.docked_test_window(window=self._w._window, width=450, height=350, block_devices=False)
        self._usd_context = omni.usd.get_context()
        await self._usd_context.open_stage_async(self.__usd_path)
        await wait_stage_loading()

        self._stage = self._usd_context.get_stage()

    # After running each test
    async def tearDown(self):
        # Cancel any pending Model._debounced_flush task before the framework
        # tears the stage down. If it survives into the next test's stage
        # transition (e.g. new_stage_async), the flush fires mid-replacement and
        # load() -> stage.Traverse() hits expired prims, raising
        # UsdExpiredPrimAccessError. The race lands reliably on linux-aarch64.
        refresh_task = getattr(self._m, "_refresh_task", None)
        if refresh_task is not None and not refresh_task.done():
            refresh_task.cancel()
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
        await super().tearDown()

    # Test(s)
    async def test_variant_presenter_1_prims(self):
        cone_path = "/World/variant_cone_test"

        # Select the prim.
        await select_prims([cone_path])
        await ui_test.human_delay()

        # Test View Selected
        self._w._set_view(1)
        await ui_test.human_delay()
        list_len = len(self._m.prims)
        self.assertTrue(list_len == 1, msg=f"View Selected shows {list_len} prims instead of the expected 1.")

        # Test View All
        self._w._set_view(0)
        await ui_test.human_delay()
        list_len = len(self._m.prims)
        self.assertTrue(list_len == 2, msg=f"View All shows {list_len} prims instead of the expected 2.")

        # Test Search
        try:
            from omni.kit.widget.searchfield import SearchField

            await ui_test.emulate_mouse_move_and_click(Vec2(114, 82))
            await ui_test.emulate_char_press("cone\n")
            await ui_test.human_delay()
            # Wait for debounced refresh to complete (5 frames + buffer)
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
            list_len = len(self._m.prims)
            for prim in self._m.prims:
                list_len += len(prim.variants)
            self.assertTrue(
                list_len == 2, msg=f"Searching for 'cone' yields {list_len} items instead of the expected 2."
            )
            await ui_test.emulate_mouse_move_and_click(Vec2(434, 82))
            await ui_test.human_delay()
        except ImportError:
            pass

        # Test Edit Variant
        try:
            import omni.kit.variant.editor as ve

            await ui_test.emulate_mouse_move_and_click(Vec2(420, 114))
            await ui_test.human_delay()
            await ui_test.emulate_mouse_move_and_click(Vec2(420, 118))
            await ui_test.human_delay()
            variant_editor_window = ve.get_window()
            self.assertTrue(variant_editor_window._window.visible, msg="Variant Editor window is not visible.")
            variant_editor_window.hide()
        except ModuleNotFoundError:
            carb.log_warn("Variant Editor extension not found.")
            pass

        # Test Locate File
        try:
            from omni.kit.window.content_browser import get_content_window

            content_browser = get_content_window()
            if content_browser:
                await ui_test.emulate_mouse_move_and_click(Vec2(420, 176))
                await ui_test.human_delay()
                await ui_test.emulate_mouse_move_and_click(Vec2(420, 186))
                filename = content_browser.get_filename()
                self.assertTrue(filename == "variant_cone_test", msg=f"cbresult: {filename}")
                await ui_test.human_delay()
        except Exception as exc:
            pass

        # Test select prim in stage
        await ui_test.emulate_mouse_move_and_click(Vec2(10, 10))
        await ui_test.human_delay()
        await ui_test.emulate_mouse_move_and_click(Vec2(114, 202), right_click=True)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_move_and_click(Vec2(114, 236))
        await ui_test.human_delay()
        selection = self._usd_context.get_selection().get_selected_prim_paths()
        self.assertTrue(
            selection == [cone_path], msg=f"Selection is currently {selection} instead of '/World/variant_cone_test'"
        )

        # Test change variant
        vset = self._m._prims[0].variants[0]._vset
        newVar = vset.GetVariantNames()[0]
        vset.SetVariantSelection(newVar)

        # Test lock variant
        await ui_test.emulate_mouse_move_and_click(Vec2(20, 200))

        await ui_test.human_delay(30)

        await self.finalize_test(
            golden_img_dir=self.__golden_img_dir, golden_img_name="variant_presenter_prim.png", threshold=25
        )

    async def test_variant_presenter_2_groups(self):
        self._w.toggle_tabs(True)

        # Test Search
        try:
            from omni.kit.widget.searchfield import SearchField

            await ui_test.emulate_mouse_move_and_click(Vec2(114, 82))
            await ui_test.emulate_char_press("cone\n")
            await ui_test.human_delay()
            # Wait for debounced refresh to complete (5 frames + buffer)
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
            list_len = len(self._m.groups)
            for group in self._m.groups:
                list_len += len(group.variants)
            self.assertTrue(
                list_len == 2, msg=f"Searching for 'cone' yields {list_len} items instead of the expected 2."
            )
            await ui_test.emulate_mouse_move_and_click(Vec2(434, 82))
            await ui_test.human_delay(10)
        except ImportError:
            pass

        # Test Create Group
        self._m.add_group()
        await ui_test.human_delay()
        self.assertTrue(
            len(self._m.groups) == 4, msg=f"'Create Group' results in {list_len} groups instead of the expected 4."
        )

        # Test Rename Group
        cone_group = [g for g in self._m.groups if g.group_name == "cone"]
        self._m.rename_group(cone_group[0], "cone_new_name")
        await ui_test.human_delay()
        cone_group = [g for g in self._m.groups if g.group_name == "cone_new_name"]
        self.assertTrue(len(cone_group) > 0, msg=f"'cone' group was not successfully renamed to 'cone_new_name'")

        # Test Remove From Group
        cube_group = [g for g in self._m.groups if g.group_name == "cube"]
        cube_variants = [v for v in cube_group[0].variants]
        for variant in cube_variants:
            self._m.remove_variant_from_group(variant)
            await ui_test.human_delay()
        # Wait for debounced refresh to complete (5 frames + buffer)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        cube_group = [g for g in self._m.groups if g.group_name == "cube"]
        self.assertTrue(
            len(cube_group[0].variants) == 0,
            msg=f"'Remove From Group' results in {list_len} variants in this group instead of the expected 0.",
        )

        # Test Delete Group
        self._m.remove_group(cube_group[0])
        await ui_test.human_delay()
        self.assertTrue(
            len(self._m.groups) == 3, msg=f"'Delete Group' results in {list_len} groups instead of the expected 3."
        )

        # Test change variant
        vset = cone_group[0].variants[0]._vset
        newVar = vset.GetVariantNames()[0]
        vset.SetVariantSelection(newVar)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_move_and_click(Vec2(114, 142))

        # Test hide locked variants
        await ui_test.emulate_mouse_move_and_click(Vec2(307, 52))

        await ui_test.human_delay(30)

        await self.finalize_test(
            golden_img_dir=self.__golden_img_dir, golden_img_name="variant_presenter_group.png", threshold=25
        )

    async def test_variant_presenter_perf_large_scene(self):
        # Local imports to avoid modifying global header
        import time

        import carb
        from pxr import Sdf, Usd

        # Allow overriding via settings if desired
        settings = carb.settings.get_settings()
        num_prims = settings.get_as_int("/exts/omni.kit.variant.presenter/perf/numPrims") or 2000
        variants_per_prim = settings.get_as_int("/exts/omni.kit.variant.presenter/perf/variantsPerPrim") or 5

        # Build a large synthetic stage for perf measurement
        await self._usd_context.new_stage_async()
        stage: Usd.Stage = self._usd_context.get_stage()
        stage.DefinePrim(Sdf.Path("/World"), "Xform")
        for i in range(num_prims):
            prim_path = f"/World/VarPrim_{i}"
            prim = stage.DefinePrim(Sdf.Path(prim_path), "Xform")
            vset = prim.GetVariantSets().AddVariantSet("presenter_test")
            for j in range(variants_per_prim):
                vset.AddVariant(f"v{j}")
            vset.SetVariantSelection("v0")
        await ui_test.human_delay()

        app = omni.kit.app.get_app()

        # Initial load
        t0 = time.perf_counter()
        self._w._load_model()
        await app.next_update_async()
        await app.next_update_async()
        load_ms = (time.perf_counter() - t0) * 1000.0

        # Toggle: View Selected
        t1 = time.perf_counter()
        self._w._set_view(1)
        await app.next_update_async()
        view_selected_ms = (time.perf_counter() - t1) * 1000.0

        # Toggle: View All
        t2 = time.perf_counter()
        self._w._set_view(0)
        await app.next_update_async()
        view_all_ms = (time.perf_counter() - t2) * 1000.0

        # Toggle tabs: GROUPS
        t3 = time.perf_counter()
        self._w.toggle_tabs(True)
        await app.next_update_async()
        groups_tab_ms = (time.perf_counter() - t3) * 1000.0

        # Toggle tabs: PRIMS
        t4 = time.perf_counter()
        self._w.toggle_tabs(False)
        await app.next_update_async()
        prims_tab_ms = (time.perf_counter() - t4) * 1000.0

        carb.log_info(
            f"[VariantPresenter Perf] num_prims={num_prims}, variants_per_prim={variants_per_prim}, "
            f"initial_load_ms={load_ms:.1f}, view_selected_ms={view_selected_ms:.1f}, "
            f"view_all_ms={view_all_ms:.1f}, groups_tab_ms={groups_tab_ms:.1f}, prims_tab_ms={prims_tab_ms:.1f}"
        )
        # Also print to stdout and persist to a JSON file under the test output path
        try:
            import json
            import os
            from datetime import datetime

            # Stdout marker for easy grepping
            print(
                "PERF|VariantPresenter|"
                + json.dumps(
                    {
                        "num_prims": num_prims,
                        "variants_per_prim": variants_per_prim,
                        "initial_load_ms": round(load_ms, 1),
                        "view_selected_ms": round(view_selected_ms, 1),
                        "view_all_ms": round(view_all_ms, 1),
                        "groups_tab_ms": round(groups_tab_ms, 1),
                        "prims_tab_ms": round(prims_tab_ms, 1),
                    }
                ),
                flush=True,
            )
            out_dir = settings.get_as_string("/exts/omni.kit.test/testOutputPath") or ""
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = os.path.join(out_dir, f"variant_presenter_perf_{stamp}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "num_prims": num_prims,
                            "variants_per_prim": variants_per_prim,
                            "initial_load_ms": load_ms,
                            "view_selected_ms": view_selected_ms,
                            "view_all_ms": view_all_ms,
                            "groups_tab_ms": groups_tab_ms,
                            "prims_tab_ms": prims_tab_ms,
                        },
                        f,
                        indent=2,
                    )
        except Exception:
            pass

    async def test_remove_all_window_lazy_instantiation(self):
        # Initially, the Remove All modal should not be instantiated
        self.assertIsNone(
            getattr(self._w, "_remove_all_window", None),
            msg="RemoveAllWindow should not be instantiated on window construction",
        )

        # Trigger Remove All (this should lazily create and show the modal)
        self._w._remove_all()
        await ui_test.human_delay()

        # Now the modal should exist and be visible
        self.assertIsNotNone(self._w._remove_all_window, msg="RemoveAllWindow was not lazily created")
        self.assertTrue(self._w._remove_all_window.visible, msg="RemoveAllWindow should be visible after _remove_all()")

        # Dismiss the dialog to avoid interference
        self._w._remove_all_window._dismiss()

    async def test_variant_presenter_external_variant_change_regression(self):
        # Regression for OMPE-80476 — variant-selection changes made outside the
        # presenter (e.g. from the Stage panel or the Variant Editor) must be
        # reflected in the presenter's cache/state. The bug had four root causes
        # in 107.1.5 and earlier:
        #   1. Window did not register the stage-change listener when opened
        #      while a stage was already loaded (separate test below).
        #   2. StageChangeHelper filter matched property paths named "set()",
        #      which Usd.Notice.ObjectsChanged never emits for variant changes.
        #      USD actually emits a resync on the prim path with
        #      "variantSelection" in notice.GetChangedFields(path).
        #   3. Model.invalidate_vset_cache_for() compared Sdf.Path keys against
        #      string cache keys (hash mismatch) so every invalidation missed.
        #   4. Model._perform_refresh() did not clear _vset_cache.
        # This test drives the notice -> filter -> invalidate -> refresh chain end
        # to end and asserts the model sees the post-change selection.
        cone_path = "/World/variant_cone_test"
        prim = self._stage.GetPrimAtPath(cone_path)
        self.assertTrue(prim.IsValid(), msg=f"Test stage missing prim at {cone_path}.")
        vset_names = prim.GetVariantSets().GetNames()
        self.assertTrue(len(vset_names) > 0, msg=f"Prim {cone_path} has no variant sets.")
        vset_name = vset_names[0]
        vset = prim.GetVariantSet(vset_name)
        variant_names = vset.GetVariantNames()
        self.assertTrue(
            len(variant_names) >= 2,
            msg=f"Test variant set '{vset_name}' needs at least 2 variants for the swap test.",
        )

        # Put the stage in a known state and give the presenter a fresh load so
        # the listener is registered against our stage.
        vset.SetVariantSelection(variant_names[0])
        self._w._load_model()
        await ui_test.human_delay()

        self.assertIsNotNone(
            self._w._stage_change_helper,
            msg="StageChangeHelper should be registered after _load_model().",
        )

        # Prime the cache by reading selections once (mimics the UI asking the
        # model for this prim's variants). This gives us something that
        # invalidate_vset_cache_for() / _perform_refresh() can fail to clear.
        _, initial_selections = self._m._get_vset_info(prim)
        self.assertIn(
            cone_path,
            self._m._vset_cache,
            msg="_get_vset_info should have cached under the prim's pathString.",
        )
        self.assertEqual(
            initial_selections.get(vset_name),
            variant_names[0],
            msg="Cached selection should match the initial variant.",
        )

        # Perform the external change that the original bug failed to detect.
        new_sel = variant_names[1]
        vset.SetVariantSelection(new_sel)

        # Allow the USD notice to fire, StageChangeHelper.async_prim_changed()
        # to schedule, and Model.refresh()'s 5-frame debounce to flush.
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

        # The next read must reflect the new selection. A regression on any of
        # the four root causes (filter misses, cache hash mismatch, _vset_cache
        # not cleared on refresh) would leave the cache pointing at the old
        # variant and this assertion would fail.
        _, selections = self._m._get_vset_info(prim)
        self.assertEqual(
            selections.get(vset_name),
            new_sel,
            msg=(
                f"Model did not pick up external variant change: expected '{new_sel}', "
                f"got '{selections.get(vset_name)}'. Likely the stage-change listener or "
                "its notice filter is no longer firing on variantSelection changes."
            ),
        )

    async def test_variant_presenter_window_opens_after_stage_registers_listener(self):
        # Regression for OMPE-80476 (Scenario B) — when a stage is already loaded
        # and the Variant Presenter window is created afterward, the OPENED
        # stage event has already fired, so _on_stage_opened() never runs.
        # The fix in VariantPresenterWindow.__init__ simulates the opened flow
        # (calls _register_listener() + _load_model()) when a stage is already
        # present at construction time. Without this, the listener would never
        # be registered for that window instance.
        from omni.kit.variant.presenter.window import VariantPresenterWindow

        # The default test stage is already loaded by setUp; confirm.
        self.assertTrue(
            self._stage is not None and self._stage.GetPseudoRoot().IsValid(),
            msg="Test stage should already be loaded before constructing the second window.",
        )

        presenter = VariantPresenterWindow()
        try:
            # Give the init-time listener registration one frame to settle.
            await ui_test.human_delay()
            self.assertIsNotNone(
                presenter._stage_change_helper,
                msg=(
                    "VariantPresenterWindow.__init__ should register the stage-change "
                    "listener when a stage is already loaded at construction time."
                ),
            )
        finally:
            # Destroy the second window so it does not interfere with subsequent tests.
            presenter.destroy()

    async def test_variant_presenter_window_opens_before_stage_registers_listener(self):
        # Regression for NVBUG 6243017 (Scenario A) — the Composer layout opens
        # Variant Presenter before its setup extension creates the initial stage.
        # _load_model() must not leave behind a helper without a USD listener,
        # otherwise OPENED sees the existing helper and never registers the stage.
        from omni.kit.variant.presenter.window import VariantPresenterWindow

        await self._usd_context.close_stage_async()
        await ui_test.human_delay()

        presenter = VariantPresenterWindow()
        try:
            presenter._load_model()
            self.assertIsNone(
                presenter._stage_change_helper,
                msg="A presenter opened without a stage must not keep an unregistered stage-change helper.",
            )

            await self._usd_context.open_stage_async(self.__usd_path)
            await wait_stage_loading()
            await ui_test.human_delay()

            self.assertIsNotNone(
                presenter._stage_change_helper,
                msg="The OPENED event should create the stage-change helper once a stage is available.",
            )

            prim = presenter._stage.GetPrimAtPath("/World/variant_cone_test")
            self.assertTrue(prim.IsValid(), msg="Test stage is missing /World/variant_cone_test.")
            vset_names = prim.GetVariantSets().GetNames()
            self.assertGreater(len(vset_names), 0, msg="Test prim has no variant sets.")
            vset_name = vset_names[0]
            vset = prim.GetVariantSet(vset_name)
            variant_names = vset.GetVariantNames()
            self.assertGreaterEqual(len(variant_names), 2, msg="Test variant set needs at least two variants.")
            current_selection = vset.GetVariantSelection()
            new_selection = variant_names[1] if current_selection == variant_names[0] else variant_names[0]

            # Prime the cache, then make the external change the original bug missed.
            presenter._model._get_vset_info(prim)
            vset.SetVariantSelection(new_selection)
            for _ in range(20):
                await omni.kit.app.get_app().next_update_async()

            _, selections = presenter._model._get_vset_info(prim)
            self.assertEqual(
                selections.get(vset_name),
                new_selection,
                msg="Presenter did not refresh after a variant change on a stage opened after the window.",
            )
        finally:
            presenter.destroy()

    async def test_variant_presenter_lock_variant_regression(self):
        # Regression for OMPE-87827 — set_variant_lock_metadata previously raised
        # "AttributeError: module 'pxr.Vt' has no attribute 'Cat'" when the
        # variant_sets_ui_hints metadata already existed but did not list this
        # vset as locked. The lock -> unlock -> re-lock sequence hits that
        # branch on the third call.
        import types

        cone_path = "/World/variant_cone_test"
        prim = self._stage.GetPrimAtPath(cone_path)
        self.assertTrue(prim.IsValid(), msg=f"Test stage missing prim at {cone_path}.")
        vset_names = prim.GetVariantSets().GetNames()
        self.assertTrue(len(vset_names) > 0, msg=f"Prim {cone_path} has no variant sets.")

        # Build a minimal item stub with the only attributes the Model method reads.
        item = types.SimpleNamespace(_prim_path=cone_path, _vset_name=vset_names[0])

        # Ensure the model has a stage reference (UI-driven load path may not have run).
        if getattr(self._m, "_stage", None) is None:
            self._m._stage = self._stage

        # First lock — creates metadata dict (metadata-absent branch).
        self._m.set_variant_lock_metadata(item)
        self.assertTrue(
            self._m.get_variant_lock_metadata(item),
            msg="First lock did not take effect.",
        )

        # Unlock — removes from list.
        self._m.set_variant_lock_metadata(item)
        self.assertFalse(
            self._m.get_variant_lock_metadata(item),
            msg="Unlock did not take effect.",
        )

        # Re-lock — regression path (metadata exists, vset not currently in list).
        self._m.set_variant_lock_metadata(item)
        self.assertTrue(
            self._m.get_variant_lock_metadata(item),
            msg="Re-lock did not take effect (OMPE-87827 regression path).",
        )


class TestModalPersistence(OmniUiTest):
    # This test simulates the NVBug scenario: an existing modal dialog is visible
    # (e.g. NLS compliance dialog). Creating the Variant Presenter UI should not
    # destroy that existing modal.
    async def setUp(self):
        await super().setUp()

    async def tearDown(self):
        await super().tearDown()

    async def test_existing_modal_persists_on_presenter_creation(self):
        import omni.ui as ui
        from omni.kit.variant.presenter.window import VariantPresenterWindow

        # Create a dummy modal to simulate NLS dialog
        dummy_modal = ui.Window(
            "Dummy Modal",
            dockPreference=ui.DockPreference.DISABLED,
            visible=False,
            flags=ui.WINDOW_FLAGS_MODAL,
            width=100,
            height=0,
        )
        dummy_modal.visible = True

        # Create the presenter window; should NOT destroy existing modal
        presenter = VariantPresenterWindow()
        await ui_test.human_delay()

        self.assertTrue(dummy_modal.visible, msg="Existing modal should remain visible after presenter creation")

        # Dismiss dummy modal
        dummy_modal.visible = False
        # Destroy presenter window to avoid global state pollution across tests
        presenter.destroy()

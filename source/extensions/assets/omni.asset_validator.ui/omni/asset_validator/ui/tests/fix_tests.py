# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest.mock as mock

import omni.kit.test
from omni.asset_validator.core import (
    EditTargetId,
    EditTargetIdList,
    Issue,
    IssueSeverity,
    LayerId,
    PrimId,
    PropertyId,
    StageId,
    Suggestion,
    TypeChecker,
)
from omni.asset_validator.ui import (
    ApplicationModel,
    AssetResultsModel,
    FixAtItem,
    FixAtItemModel,
    FixAtModel,
    FixFn,
    SuggestionModel,
    ValidateFn,
)
from omni.asset_validator.ui.models._results import IssueModel
from pxr import Sdf, Usd


class FixAtModelTest(omni.kit.test.AsyncTestCase):
    def test_set_value(self):
        path = Sdf.Path("/test")
        target_id = EditTargetId(layer_id=None, path=path)
        fix_sites = [target_id]

        model = FixAtModel(fix_sites)
        self.assertEqual(model.get_value_as_int(), 0)

    def test_fix_site(self):
        path = Sdf.Path("/test")
        target_id = EditTargetId(layer_id=None, path=path)
        fix_sites = [target_id]

        model = FixAtModel(fix_sites)
        self.assertEqual(model.fix_site, target_id)

    def test_value_changed_notification(self):
        path1 = Sdf.Path("/test1")
        path2 = Sdf.Path("/test2")
        target_id1 = EditTargetId(layer_id=None, path=path1)
        target_id2 = EditTargetId(layer_id=None, path=path2)
        fix_sites = [target_id1, target_id2]

        model = FixAtModel(fix_sites)

        on_value_changed = mock.Mock()
        _subscription = model.subscribe_value_changed_fn(on_value_changed)
        model.set_value(1)

        self.assertTrue(on_value_changed.called)
        self.assertEqual(model.get_value_as_int(), 1)
        self.assertEqual(model.fix_site, target_id2)

    def test_reset(self):
        path1 = Sdf.Path("/test1")
        path2 = Sdf.Path("/test2")
        path3 = Sdf.Path("/test3")
        target_id1 = EditTargetId(layer_id=None, path=path1)
        target_id2 = EditTargetId(layer_id=None, path=path2)
        target_id3 = EditTargetId(layer_id=None, path=path3)

        model = FixAtModel([target_id1, target_id2])
        model.set_value(1)
        self.assertEqual(model.fix_site, target_id2)

        on_changed = mock.Mock()
        _sub = model.subscribe_value_changed_fn(on_changed)

        # Update fix sites — should reset selection and notify
        model.reset([target_id3])
        self.assertTrue(on_changed.called)
        self.assertEqual(model.get_value_as_int(), 0)
        self.assertEqual(model.fix_site, target_id3)


class FixAtItemTest(omni.kit.test.AsyncTestCase):
    def test_format_layer_id(self):
        layer_id = LayerId(identifier="/test/layer.usd")
        target_id = EditTargetId(layer_id=layer_id, path=Sdf.Path("/test"))
        issue = Issue(message="message", at=layer_id, severity=IssueSeverity.FAILURE)

        item = FixAtItem(issue, target_id)
        self.assertEqual(item.model.get_value_as_string(), "Prim(/test) at Layer(./layer.usd)")

    def test_format_prim_id(self):
        layer_id = LayerId(identifier="/test/layer.usd")
        stage_id = StageId(root_layer=layer_id)
        prim_id = PrimId(
            stage_id=stage_id,
            path=Sdf.Path("/test"),
            spec_ids=EditTargetIdList([EditTargetId(layer_id=layer_id, path=Sdf.Path("/test"))]),
        )
        target_id = EditTargetId(layer_id=layer_id, path=Sdf.Path("/test"))
        issue = Issue(message="message", at=prim_id, severity=IssueSeverity.FAILURE)

        item = FixAtItem(issue, target_id)
        self.assertEqual(item.model.get_value_as_string(), "Prim(/test) at Layer(./layer.usd)")

    def test_format_property_id(self):
        layer_id = LayerId(identifier="/test/layer.usd")
        stage_id = StageId(root_layer=layer_id)
        prim_id = PrimId(
            stage_id=stage_id,
            path=Sdf.Path("/test"),
            spec_ids=EditTargetIdList([EditTargetId(layer_id=layer_id, path=Sdf.Path("/test"))]),
        )
        property_id = PropertyId(prim_id=prim_id, path=Sdf.Path("/test.prop"))
        target_id = EditTargetId(layer_id=layer_id, path=Sdf.Path("/test.prop"))
        issue = Issue(message="message", at=property_id, severity=IssueSeverity.FAILURE)

        item = FixAtItem(issue, target_id)
        self.assertEqual(item.model.get_value_as_string(), "Property(/test.prop) at Layer(./layer.usd)")

    def test_format_relative_path(self):
        layer_id = LayerId(identifier="/test/dir/layer.usd")
        target_id = EditTargetId(layer_id=LayerId(identifier="/test/other/fix.usd"), path=Sdf.Path("/test"))
        issue = Issue(message="message", at=layer_id, severity=IssueSeverity.FAILURE)

        item = FixAtItem(issue, target_id)
        self.assertEqual(item.model.get_value_as_string(), "Prim(/test) at Layer(../other/fix.usd)")


class SuggestionModelTest(omni.kit.test.AsyncTestCase):
    def test_single_suggestion(self):
        s = Suggestion(callable=lambda stage, at: None, message="fix it")
        model = SuggestionModel((s,))
        self.assertEqual(model.get_value_as_int(), 0)
        self.assertIs(model.suggestion, s)

    def test_multiple_suggestions(self):
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        model = SuggestionModel((s1, s2))
        self.assertEqual(model.suggestion, s1)
        model.set_value(1)
        self.assertEqual(model.suggestion, s2)

    def test_empty_suggestions(self):
        model = SuggestionModel(())
        self.assertIsNone(model.suggestion)

    def test_set_value_out_of_bounds(self):
        s = Suggestion(callable=lambda stage, at: None, message="fix it")
        model = SuggestionModel((s,))
        with self.assertRaises(IndexError):
            model.set_value(1)
        with self.assertRaises(IndexError):
            model.set_value(-1)

    def test_value_changed_notification(self):
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        model = SuggestionModel((s1, s2))
        on_changed = mock.Mock()
        _sub = model.subscribe_value_changed_fn(on_changed)
        model.set_value(1)
        self.assertTrue(on_changed.called)


class IssueModelSuggestionTest(omni.kit.test.AsyncTestCase):
    def test_selected_suggestion_single(self):
        s = Suggestion(callable=lambda stage, at: None, message="fix it")
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestion=s)
        model = IssueModel(issue)
        self.assertIs(model.selected_suggestion, s)

    def test_selected_suggestion_multiple(self):
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestions=[s1, s2])
        model = IssueModel(issue)
        self.assertIs(model.selected_suggestion, s1)
        model.as_suggestion.set_value(1)
        self.assertIs(model.selected_suggestion, s2)

    def test_selected_suggestion_none(self):
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE)
        model = IssueModel(issue)
        self.assertIsNone(model.selected_suggestion)

    def test_fix_at_model_identity_preserved_on_suggestion_change(self):
        """Changing suggestion updates fix sites in-place, preserving FixAtModel identity."""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestions=[s1, s2])
        model = IssueModel(issue)

        # Capture the original FixAtModel reference (same one FixAtItemModel would hold)
        original_fix_at = model.as_fix

        # Change suggestion
        model.as_suggestion.set_value(1)

        # The FixAtModel object should be the SAME instance (mutated in-place)
        self.assertIs(model.as_fix, original_fix_at)

    def test_fix_at_subscription_survives_suggestion_change(self):
        """FixAtModel subscription fires when suggestion changes (not broken by replacement)."""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestions=[s1, s2])
        model = IssueModel(issue)

        on_changed = mock.Mock()
        _sub = model.as_fix.subscribe_value_changed_fn(on_changed)

        # Change suggestion — should trigger value_changed on the SAME FixAtModel
        model.as_suggestion.set_value(1)

        self.assertTrue(on_changed.called)

    def test_fix_sites_recomputed_on_suggestion_change(self):
        """Changing suggestion recomputes fix sites via fix_sites_for()."""
        layer_a = LayerId(identifier="/layers/a.usd")
        layer_b = LayerId(identifier="/layers/b.usd")
        target_a = EditTargetId(layer_id=layer_a, path=Sdf.Path("/Prim"))
        target_b = EditTargetId(layer_id=layer_b, path=Sdf.Path("/Prim"))
        stage_id = StageId(root_layer=layer_a)
        prim_id = PrimId(
            stage_id=stage_id,
            path=Sdf.Path("/Prim"),
            spec_ids=EditTargetIdList([target_a, target_b]),
        )
        layer_a_sdf = mock.Mock(spec=Sdf.Layer)
        layer_a_sdf.identifier = "/layers/a.usd"
        s1 = Suggestion(callable=lambda stage, at: None, message="fix in A", at=[layer_a_sdf])
        s2 = Suggestion(callable=lambda stage, at: None, message="fix anywhere")
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, at=prim_id, suggestions=[s1, s2])
        model = IssueModel(issue)

        # Default suggestion (s1) constrains to layer_a → target_a is preferred
        self.assertEqual(model.as_fix.fix_site, target_a)

        # Switch to s2 (unconstrained) — fix sites recomputed, both targets available
        model.as_suggestion.set_value(1)
        fix_sites = model.as_fix.fix_sites
        self.assertIn(target_a, fix_sites)
        self.assertIn(target_b, fix_sites)


class FixAtItemModelTest(omni.kit.test.AsyncTestCase):
    def test_items_rebuilt_on_fix_sites_change(self):
        """FixAtItemModel rebuilds ComboBox items when FixAtModel.reset() is called."""
        layer_a = LayerId(identifier="/layers/a.usd")
        layer_b = LayerId(identifier="/layers/b.usd")
        target_a = EditTargetId(layer_id=layer_a, path=Sdf.Path("/Prim"))
        target_b = EditTargetId(layer_id=layer_b, path=Sdf.Path("/Prim"))
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, at=layer_a)

        model = IssueModel(issue)
        item_model = FixAtItemModel(model)

        original_count = len(item_model.get_item_children(None))

        # Reset with different fix sites
        model.as_fix.reset([target_a, target_b])
        new_count = len(item_model.get_item_children(None))

        self.assertEqual(new_count, 2)
        self.assertGreaterEqual(new_count, original_count)


class FixFnTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = ApplicationModel.create()

        self.test_asset = Usd.Stage.CreateInMemory()
        self.test_asset.DefinePrim("/World", "Xform")
        self.asset_results = AssetResultsModel(self.test_asset)
        self.model.results.add_asset(self.asset_results)

        self.issue = Issue(message="Test issue", severity=IssueSeverity.FAILURE, rule=TypeChecker)
        self.issue_model = IssueModel(self.issue)
        self.asset_results.issues = [self.issue_model]

    async def test_fix_fn_fixes_single_issue(self):
        fix_fn = FixFn(model=self.model, issue=self.issue)
        await fix_fn.apply_async()

        self.assertEqual(len(self.model.results.assets), 1)
        self.assertEqual(len(self.asset_results.groups), 0)

    async def test_fix_fn_fixes_selected_issue(self):
        self.issue_model.selected = True

        fix_fn = FixFn(model=self.model)
        await fix_fn.apply_async()

        self.assertEqual(len(self.model.results.assets), 1)
        self.assertEqual(len(self.asset_results.groups), 0)

    async def test_fix_fn_autovalidate_enabled_clears_groups(self):
        """When autovalidate is enabled (default), fix re-validates and clears old groups."""
        self.model.settings_model.autovalidate = True
        self.issue_model.selected = True

        fix_fn = FixFn(model=self.model)
        await fix_fn.apply_async()

        self.assertEqual(len(self.asset_results.groups), 0)
        self.assertFalse(self.asset_results.outdated)

    async def test_fix_fn_autovalidate_disabled_marks_outdated(self):
        """When autovalidate is disabled, fix marks results as outdated and preserves groups."""
        self.model.settings_model.autovalidate = False
        self.issue_model.selected = True
        groups_before = len(self.asset_results.groups)

        fix_fn = FixFn(model=self.model)
        await fix_fn.apply_async()

        self.assertTrue(self.asset_results.outdated)
        self.assertEqual(len(self.asset_results.groups), groups_before)

    async def test_revalidation_clears_outdated(self):
        """After manual re-validation, outdated resets to False."""
        self.model.settings_model.autovalidate = False
        self.issue_model.selected = True

        fix_fn = FixFn(model=self.model)
        await fix_fn.apply_async()
        self.assertTrue(self.asset_results.outdated)

        validate_fn = ValidateFn(model=self.model, asset=self.test_asset)
        await validate_fn.apply_async()

        self.assertFalse(self.asset_results.outdated)

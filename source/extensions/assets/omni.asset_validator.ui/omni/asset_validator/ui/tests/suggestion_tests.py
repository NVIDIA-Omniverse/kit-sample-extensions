# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import omni.kit.test
import omni.ui
from omni.asset_validator.core import Issue, IssueSeverity, Suggestion
from omni.asset_validator.ui import IssueModel, SuggestionLocationWidget
from omni.kit import ui_test
from pxr import Usd

__all__ = ["SuggestionLocationWidgetTest"]


class SuggestionLocationWidgetTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.stage = Usd.Stage.CreateInMemory()
        self.prim = self.stage.DefinePrim("/World/Prim")
        self.s1 = Suggestion(callable=lambda stage, at: None, message="Fix A")
        self.s2 = Suggestion(callable=lambda stage, at: None, message="Fix B")

    async def test_current_label_no_suggestion(self):
        # Given: issue with no suggestions
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE)
        widget = SuggestionLocationWidget(IssueModel(issue))
        # Then
        self.assertEqual(widget.current_label, "")

    async def test_current_label_suggestion_no_fix_site(self):
        # Given: suggestion on an issue with no location → fix_at is None
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestion=self.s1)
        widget = SuggestionLocationWidget(IssueModel(issue))
        # Then: label shows suggestion message only
        self.assertEqual(widget.current_label, "Fix A")

    async def test_current_label_suggestion_with_fix_site(self):
        # Given: issue at a real prim → fix_sites_for returns at least one site
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, at=self.prim, suggestion=self.s1)
        widget = SuggestionLocationWidget(IssueModel(issue))
        # Then: label includes " at <location>"
        label = widget.current_label
        self.assertTrue(label.startswith("Fix A at "), msg=f"Unexpected label: {label!r}")

    async def test_current_label_updates_on_suggestion_change(self):
        # Given
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestions=[self.s1, self.s2])
        model = IssueModel(issue)
        widget = SuggestionLocationWidget(model)
        self.assertEqual(widget.current_label, "Fix A")
        # When
        model.as_suggestion.set_value(1)
        # Then
        self.assertEqual(widget.current_label, "Fix B")

    async def test_label_widget_reflects_suggestion_change(self):
        # Given: widget built in a window
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestions=[self.s1, self.s2])
        model = IssueModel(issue)

        window = omni.ui.Window("TestSuggestion")
        with window.frame:
            with omni.ui.HStack():
                widget = SuggestionLocationWidget(model)
        await ui_test.human_delay()

        # When
        model.as_suggestion.set_value(1)
        await ui_test.human_delay()

        # Then: the omni.ui label text updated reactively
        self.assertEqual(widget._label.text, "Fix B")

    async def test_build_ui_info_severity_no_label(self):
        # Given: INFO issue with no suggestions → nothing rendered
        issue = Issue(message="msg", severity=IssueSeverity.INFO)
        window = omni.ui.Window("TestSuggestionInfo")
        with window.frame:
            with omni.ui.HStack():
                widget = SuggestionLocationWidget(IssueModel(issue))
        await ui_test.human_delay()
        # Then: label not created
        self.assertIsNone(widget._label)

    async def test_build_ui_failure_no_suggestions_no_label(self):
        # Given: FAILURE issue with no suggestions → "Fix Manually" rendered, no dropdown label
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE)
        window = omni.ui.Window("TestSuggestionFailure")
        with window.frame:
            with omni.ui.HStack():
                widget = SuggestionLocationWidget(IssueModel(issue))
        await ui_test.human_delay()
        # Then
        self.assertIsNone(widget._label)

    async def test_select_updates_model(self):
        # Given
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE, suggestions=[self.s1, self.s2])
        model = IssueModel(issue)
        widget = SuggestionLocationWidget(model)
        # When
        widget._select(1, 0)
        # Then
        self.assertIs(model.selected_suggestion, self.s2)

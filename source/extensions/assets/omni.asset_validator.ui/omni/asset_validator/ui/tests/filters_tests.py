# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import omni.kit.test
from omni.asset_validator.core import IssuePredicates
from omni.asset_validator.ui import FiltersModel


class FiltersModelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.model = FiltersModel()

    def test_root_only_property(self):
        self.assertEqual(self.model.root_only, False)

        self.model.root_only = True
        self.assertEqual(self.model.root_only, True)

        self.assertEqual(self.model.root_only_model.as_bool, True)

    def test_fixes_property(self):
        self.assertEqual(self.model.fixes, False)

        self.model.fixes = True
        self.assertEqual(self.model.fixes, True)

        self.assertEqual(self.model.fixes_model.as_bool, True)

    def test_errors_property(self):
        self.assertEqual(self.model.errors, True)

        self.model.errors = False
        self.assertEqual(self.model.errors, False)

        self.assertEqual(self.model.errors_model.as_bool, False)

    def test_failures_property(self):
        self.assertEqual(self.model.failures, True)

        self.model.failures = False
        self.assertEqual(self.model.failures, False)

        self.assertEqual(self.model.failures_model.as_bool, False)

    def test_warnings_property(self):
        self.assertEqual(self.model.warnings, True)

        self.model.warnings = False
        self.assertEqual(self.model.warnings, False)

        self.assertEqual(self.model.warnings_model.as_bool, False)

    def test_info_property(self):
        self.assertEqual(self.model.info, True)

        self.model.info = False
        self.assertEqual(self.model.info, False)

        self.assertEqual(self.model.info_model.as_bool, False)

    def test_tokens_property(self):
        self.assertEqual(self.model.tokens, [])

        self.model.tokens = ["token1", "token2"]
        self.assertEqual(self.model.tokens, ["token1", "token2"])

        self.assertEqual(self.model.tokens_model.tokens, ["token1", "token2"])

    def test_other_tags_property(self):
        self.assertEqual(self.model.other_tags, True)

        self.model.other_tags = False
        self.assertEqual(self.model.other_tags, False)

        self.assertEqual(self.model.other_tags_model.as_bool, False)

    def test_essential_property(self):
        self.assertEqual(self.model.essential, True)

        self.model.essential = False
        self.assertEqual(self.model.essential, False)

        self.assertEqual(self.model.essential_model.as_bool, False)

    def test_correctness_property(self):
        self.assertEqual(self.model.correctness, True)

        self.model.correctness = False
        self.assertEqual(self.model.correctness, False)

        self.assertEqual(self.model.correctness_model.as_bool, False)

    def test_limitations_property(self):
        self.assertEqual(self.model.limitations, True)

        self.model.limitations = False
        self.assertEqual(self.model.limitations, False)

        self.assertEqual(self.model.limitations_model.as_bool, False)

    def test_performance_property(self):
        self.assertEqual(self.model.performance, True)

        self.model.performance = False
        self.assertEqual(self.model.performance, False)

        self.assertEqual(self.model.performance_model.as_bool, False)

    def test_clear_method(self):
        self.model.root_only = True
        self.model.fixes = True
        self.model.clear()
        self.assertEqual(self.model.root_only, False)
        self.assertEqual(self.model.fixes, False)
        self.assertEqual(self.model.errors, True)
        self.assertEqual(self.model.failures, True)
        self.assertEqual(self.model.warnings, True)
        self.assertEqual(self.model.info, True)
        self.assertEqual(self.model.other_tags, True)
        self.assertEqual(self.model.essential, True)
        self.assertEqual(self.model.correctness, True)
        self.assertEqual(self.model.limitations, True)
        self.assertEqual(self.model.performance, True)
        self.assertEqual(self.model.tokens, [])

    def test_predicate_property(self):
        # No predicates
        self.model.root_only = False
        self.model.fixes = False
        self.model.errors = False
        self.model.failures = False
        self.model.warnings = False
        self.model.info = False
        self.model.other_tags = False
        self.model.essential = False
        self.model.correctness = False
        self.model.limitations = False
        self.model.performance = False
        self.model.tokens = []
        self.assertIs(self.model.predicate, IssuePredicates.Any())

        # Single predicates
        self.model.root_only = True
        self.assertIs(self.model.predicate, IssuePredicates.HasRootLayer())
        self.model.root_only = False

        self.model.fixes = True
        self.assertIs(self.model.predicate, IssuePredicates.HasFix())
        self.model.fixes = False

        self.model.errors = True
        self.assertIs(self.model.predicate, IssuePredicates.IsError())
        self.model.errors = False

        self.model.failures = True
        self.assertIs(self.model.predicate, IssuePredicates.IsFailure())
        self.model.failures = False

        self.model.warnings = True
        self.assertIs(self.model.predicate, IssuePredicates.IsWarning())
        self.model.warnings = False

        self.model.info = True
        self.assertIs(self.model.predicate, IssuePredicates.IsInfo())
        self.model.info = False

        self.model.all_tags = True
        self.assertIs(self.model.predicate, IssuePredicates.Any())
        self.model.all_tags = False

        self.model.essential = True
        self.assertIs(self.model.predicate, IssuePredicates.HasTag("essential"))
        self.model.essential = False

        self.model.correctness = True
        self.assertIs(self.model.predicate, IssuePredicates.HasTag("correctness"))
        self.model.correctness = False

        self.model.limitations = True
        self.assertIs(self.model.predicate, IssuePredicates.HasTag("limitation"))
        self.model.limitations = False

        self.model.performance = True
        self.assertIs(self.model.predicate, IssuePredicates.HasTag("performance"))
        self.model.performance = False

        self.model.other_tags = True
        self.assertEqual(
            repr(self.model.predicate),
            repr(
                IssuePredicates.Not(
                    IssuePredicates.Or(
                        IssuePredicates.HasTag("essential"),
                        IssuePredicates.HasTag("correctness"),
                        IssuePredicates.HasTag("limitation"),
                        IssuePredicates.HasTag("performance"),
                    )
                )
            ),
        )
        self.model.other_tags = False

        self.model.tokens = ["token1", "token2"]
        self.assertEqual(
            repr(self.model.predicate),
            repr(IssuePredicates.Or(IssuePredicates.MatchesToken("token1"), IssuePredicates.MatchesToken("token2"))),
        )
        self.model.tokens = []

        # Multiple predicates
        self.model.root_only = True
        self.model.fixes = True
        self.model.errors = True
        self.assertEqual(
            repr(self.model.predicate),
            repr(
                IssuePredicates.And(IssuePredicates.HasRootLayer(), IssuePredicates.HasFix(), IssuePredicates.IsError())
            ),
        )
        self.model.root_only = False
        self.model.fixes = False
        self.model.errors = False

        # Multiple predicate with tokens
        self.model.tokens = ["token1", "token2"]
        self.model.fixes = True
        self.model.errors = True
        self.assertEqual(
            repr(self.model.predicate),
            repr(
                IssuePredicates.And(
                    IssuePredicates.HasFix(),
                    IssuePredicates.IsError(),
                    IssuePredicates.Or(IssuePredicates.MatchesToken("token1"), IssuePredicates.MatchesToken("token2")),
                )
            ),
        )
        self.model.tokens = []
        self.model.fixes = False
        self.model.errors = False

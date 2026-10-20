# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import pathlib

import omni.asset_validator.core
import omni.kit.test
from omni.asset_validator.core import IssuePredicates, OmniDefaultPrimChecker, StageMetadataChecker
from pxr import Usd

from .registry_tests import MyRuleChecker


def getUrl(relativePath: str | pathlib.Path | None = ""):
    return str(pathlib.Path(__file__).parent.joinpath("data").joinpath(relativePath))


class InitErrorRule(omni.asset_validator.core.BaseRuleChecker):
    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool) -> None:
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        raise ValueError("Unexpected error __init__.")


class EmptyRule(omni.asset_validator.core.BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim):
        pass


class CheckPrimErrorRule(omni.asset_validator.core.BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim):
        raise ValueError("Uncaught error CheckPrim.")


class ValidationEngineTest(omni.kit.test.AsyncTestCase):
    maxDiff = None

    async def testEnableCustomRule(self):
        test_file = getUrl("curves.usda")
        engine = omni.asset_validator.core.ValidationEngine()
        engine.enable_rule(MyRuleChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertFalse(result.issues(IssuePredicates.IsError()))
        self.assertFalse(result.issues(IssuePredicates.IsWarning()))
        self.assertEqual(len(result.issues(IssuePredicates.IsFailure())), 3)
        self.assertTrue(
            result.issues(
                IssuePredicates.And(IssuePredicates.IsFailure(), IssuePredicates.IsRule("StageMetadataChecker"))
            )
        )
        self.assertTrue(
            result.issues(
                IssuePredicates.And(IssuePredicates.IsFailure(), IssuePredicates.IsRule("OmniDefaultPrimChecker"))
            )
        )
        self.assertTrue(
            result.issues(IssuePredicates.And(IssuePredicates.IsFailure(), IssuePredicates.IsRule("MyRuleChecker")))
        )

    async def testEnableBuiltinRule(self):
        test_file = getUrl("curves.usda")
        engine = omni.asset_validator.core.ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertFalse(result.issues(IssuePredicates.IsError()))
        self.assertFalse(result.issues(IssuePredicates.IsWarning()))
        self.assertEqual(len(result.issues(IssuePredicates.IsFailure())), 1)
        self.assertTrue(
            result.issues(
                IssuePredicates.And(IssuePredicates.IsFailure(), IssuePredicates.IsRule("StageMetadataChecker"))
            )
        )

    async def testDisableCustomRule(self):
        test_file = getUrl("curves.usda")
        engine = omni.asset_validator.core.ValidationEngine()
        engine.enable_rule(MyRuleChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 3)

        # Disable rules that cause failures and validate again
        engine.disable_rule(StageMetadataChecker)
        engine.disable_rule(OmniDefaultPrimChecker)
        engine.disable_rule(MyRuleChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 0)

        # We are able to enable and disable the rules again
        engine.enable_rule(MyRuleChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 1)
        engine.disable_rule(MyRuleChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 0)

    async def testDisableBuiltinRule(self):
        test_file = getUrl("curves.usda")
        engine = omni.asset_validator.core.ValidationEngine(init_rules=False)
        engine.enable_rule(EmptyRule)
        engine.enable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 1)

        # Disable rules that cause failures and validate again
        engine.disable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(len(result.issues()), 0)

        # We are able to enable and disable the rules again
        engine.enable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 1)
        engine.disable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 0)

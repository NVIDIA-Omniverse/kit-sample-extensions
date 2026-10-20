# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import pathlib
from pathlib import Path
from tempfile import TemporaryDirectory

import omni.asset_validator.core
import omni.asset_validator.ui
import omni.kit.test
import omni.usd
from omni.asset_validator.ui import IssueModel
from pxr import Sdf, Usd


def getUrl(relativePath: str = ""):
    return (
        str(pathlib.Path(__file__).parent.joinpath("data").joinpath(relativePath))
        .replace(".ui", ".core")
        .replace(f"{os.sep}ui{os.sep}", f"{os.sep}core{os.sep}")
    )


class AssetValidatorUiTest(omni.kit.test.AsyncTestCase):

    maxDiff = None

    async def setUp(self):
        super().setUp()
        await omni.usd.get_context().new_stage_async()
        ui = omni.asset_validator.ui.get_instance()
        ui.reset(resetAssets=True, resetRules=True)
        ui.setAssetMode(omni.asset_validator.ui.AssetMode.Uri)

    async def tearDown(self):
        super().tearDown()
        await omni.usd.get_context().close_stage_async()

    async def testVisibility(self):
        ui = omni.asset_validator.ui.get_instance()
        ui.show()
        self.assertTrue(ui.visible())
        ui.hide()
        self.assertFalse(ui.visible())

    async def testRules(self):
        ui = omni.asset_validator.ui.get_instance()
        rule = omni.asset_validator.core.ValidationRulesRegistry.rule("UsdMaterialBindingApi")
        other_rule = omni.asset_validator.core.ValidationRulesRegistry.rule("UsdLuxSchemaChecker")
        self.assertTrue(ui.enabled(rule))
        self.assertTrue(ui.enabled(other_rule))
        ui.disableRule(rule)
        self.assertFalse(ui.enabled(rule))
        self.assertTrue(ui.enabled(other_rule))
        ui.enableRule(rule)
        self.assertTrue(ui.enabled(rule))
        self.assertTrue(ui.enabled(other_rule))

    async def testReset(self):
        ui = omni.asset_validator.ui.get_instance()
        self.assertEqual(ui.getAssetUri(), "")
        uri = getUrl("helloworld.usda")
        ui.setAssetUri(uri)

        self.assertEqual(ui.getAssetUri(), uri)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

        ui.reset(resetAssets=False)
        self.assertEqual(ui.getAssetUri(), uri)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

        rule = omni.asset_validator.core.ValidationRulesRegistry.rule("UsdMaterialBindingApi")
        ui.disableRule(rule)
        self.assertFalse(ui.enabled(rule))
        ui.reset(resetAssets=False, resetRules=True)
        self.assertEqual(ui.getAssetUri(), uri)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())
        self.assertTrue(ui.enabled(rule))

        ui.disableRule(rule)
        ui.reset(resetAssets=True, resetRules=False)
        self.assertEqual(ui.getAssetUri(), "")
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())
        self.assertFalse(ui.enabled(rule))

    async def test_variants(self):
        ui = omni.asset_validator.ui.get_instance()
        self.assertTrue(ui.variants)
        ui.variants = False
        self.assertFalse(ui.variants)
        ui.variants = True
        self.assertTrue(ui.variants)

    async def test_instance_prototypes(self):
        ui = omni.asset_validator.ui.get_instance()
        self.assertTrue(ui.instance_prototypes)
        ui.instance_prototypes = False
        self.assertFalse(ui.instance_prototypes)
        ui.instance_prototypes = True
        self.assertTrue(ui.instance_prototypes)

    async def testAssetUri(self):
        ui = omni.asset_validator.ui.get_instance()
        self.assertEqual(ui.getAssetUri(), "")
        uri = getUrl("helloworld.usda")
        ui.setAssetUri(uri)
        self.assertEqual(ui.getAssetUri(), uri)

    async def testStage(self):
        ui = omni.asset_validator.ui.get_instance()
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

        uri = getUrl("helloworld.usda")
        stage = Usd.Stage.Open(uri)
        ui.setStage(stage)
        self.assertEqual(ui.getStage(), stage)

        # force resets to the current stage
        ui.setStage(None)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

    async def testAssetMode(self):
        ui = omni.asset_validator.ui.get_instance()
        self.assertEqual(ui.getAssetUri(), "")
        uri = getUrl("helloworld.usda")
        ui.setAssetUri(uri)

        ui.setAssetMode(omni.asset_validator.ui.AssetMode.Uri)
        self.assertEqual(ui.getAssetMode(), omni.asset_validator.ui.AssetMode.Uri)
        self.assertEqual(ui.getAssetUri(), uri)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

        ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
        self.assertEqual(ui.getAssetMode(), omni.asset_validator.ui.AssetMode.Stage)
        self.assertEqual(ui.getAssetUri(), uri)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

        ui.setAssetMode(omni.asset_validator.ui.AssetMode.Prims)
        self.assertEqual(ui.getAssetMode(), omni.asset_validator.ui.AssetMode.Prims)
        self.assertEqual(ui.getAssetUri(), uri)
        self.assertEqual(ui.getStage(), omni.usd.get_context().get_stage())

    async def testValidate(self):
        ui = omni.asset_validator.ui.get_instance()
        uri = getUrl()
        ui.setAssetUri(uri)
        ui_results = await ui.validate_async()
        core_results = await omni.asset_validator.core.ValidationEngine().validate_async(uri)
        self.assertEqual(len(ui_results), len(core_results))
        # we can't guarantee ordering because the UI uses `engine.validate_with_callbacks``
        self.assertEqual(set([x.asset for x in ui_results]), set([x.asset for x in core_results]))

    async def test_fix_uri_do_not_save(self) -> None:
        previous_content: str = Path(getUrl("usdMaterialBindingApiFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            ui = omni.asset_validator.ui.get_instance()
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Uri)
            ui.setAssetUri(str(destination))

            # When
            results = await ui.validate_async()
            for issue in results.issues().filter_by(
                lambda obj: obj.rule is omni.asset_validator.core.UsdMaterialBindingApi
            ):
                self.assertTrue(ui.selectIssue(issue))
            await ui.fix()

            # Then
            current_content: str = Path(str(destination)).read_text()
            self.assertEqual(previous_content, current_content)

    async def test_fix_uri_do_save(self) -> None:
        previous_content: str = Path(getUrl("usdMaterialBindingApiFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            ui = omni.asset_validator.ui.get_instance()
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Uri)
            ui.setAssetUri(str(destination))

            # When
            results = await ui.validate_async()
            for issue in results.issues().filter_by(
                lambda obj: obj.rule is omni.asset_validator.core.UsdMaterialBindingApi
            ):
                self.assertTrue(ui.selectIssue(issue))
            await ui.fixAndSave()

            # Then
            current_content: str = Path(str(destination)).read_text()
            self.assertNotEqual(previous_content, current_content)

    async def test_fix_stage_do_not_save(self) -> None:
        previous_content: str = Path(getUrl("usdMaterialBindingApiFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            ui = omni.asset_validator.ui.get_instance()
            stage: Usd.Stage = Usd.Stage.Open(str(destination))
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.setStage(stage)

            # When
            results = await ui.validate_async()
            for issue in results.issues().filter_by(
                lambda obj: obj.rule is omni.asset_validator.core.UsdMaterialBindingApi
            ):
                self.assertTrue(ui.selectIssue(issue))
            await ui.fix()

            # Then
            current_content: str = Path(str(destination)).read_text()
            self.assertEqual(previous_content, current_content)

    async def test_fix_stage_do_save(self) -> None:
        previous_content: str = Path(getUrl("usdMaterialBindingApiFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            ui = omni.asset_validator.ui.get_instance()
            stage: Usd.Stage = Usd.Stage.Open(str(destination))
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.setStage(stage)

            # When
            results = await ui.validate_async()
            for issue in results.issues().filter_by(
                lambda obj: obj.rule is omni.asset_validator.core.UsdMaterialBindingApi
            ):
                self.assertTrue(ui.selectIssue(issue))
            await ui.fixAndSave()

            # Then
            current_content: str = Path(str(destination)).read_text()
            self.assertNotEqual(previous_content, current_content)

    async def test_fix_issue_do_not_save(self) -> None:
        previous_content: str = Path(getUrl("usdMaterialBindingApiFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            ui = omni.asset_validator.ui.get_instance()
            stage: Usd.Stage = Usd.Stage.Open(str(destination))
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.setStage(stage)

            # When
            results = await ui.validate_async()
            for issue in results.issues().filter_by(
                lambda obj: obj.rule is omni.asset_validator.core.UsdMaterialBindingApi
            ):
                await ui.fixIssue(issue)

            # Then
            current_content: str = Path(str(destination)).read_text()
            self.assertEqual(previous_content, current_content)

    async def test_fix_issue_do_save(self) -> None:
        previous_content: str = Path(getUrl("usdMaterialBindingApiFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            ui = omni.asset_validator.ui.get_instance()
            stage: Usd.Stage = Usd.Stage.Open(str(destination))
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.setStage(stage)

            # When
            results = await ui.validate_async()
            for issue in results.issues().filter_by(
                lambda obj: obj.rule is omni.asset_validator.core.UsdMaterialBindingApi
            ):
                await ui.fixAndSaveIssue(issue)

            # Then
            current_content: str = Path(str(destination)).read_text()
            self.assertNotEqual(previous_content, current_content)

    async def test_select_issue_property_prim(self) -> None:
        previous_content: str = Path(getUrl("omniGeometryFail.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            omni.usd.get_context().open_stage(str(destination))
            ui = omni.asset_validator.ui.get_instance()
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.enableRule(omni.asset_validator.core.ValidationRulesRegistry.rule("WeldChecker"))
            selection = omni.usd.get_context().get_selection()
            selection.clear_selected_prim_paths()

            # When
            results = await ui.validate_async()
            issue_item = omni.asset_validator.ui.IssueItem(IssueModel(results.issues()[0]))
            issue_item._select_prim()

            # Then
            self.assertEqual(selection.get_selected_prim_paths(), ["/root/Cube_001/Cube_001"])

    async def test_select_issue_pseudo_root_prim(self) -> None:
        with TemporaryDirectory() as directory:
            stage = Usd.Stage.CreateNew(os.path.join(directory, "test.usda"))
            stage.DefinePrim("/World", "Xform")
            stage.Save()

            # Given
            omni.usd.get_context().open_stage(os.path.join(directory, "test.usda"))
            ui = omni.asset_validator.ui.get_instance()
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.enableRule(omni.asset_validator.core.ValidationRulesRegistry.rule("OmniDefaultPrimChecker"))
            selection = omni.usd.get_context().get_selection()
            selection.clear_selected_prim_paths()

            # When
            results = await ui.validate_async()
            stage = omni.usd.get_context().get_stage()
            issue_item = omni.asset_validator.ui.IssueItem(IssueModel(results.issues()[0]))
            issue_item._select_prim()

            # Then
            self.assertEqual(selection.get_selected_prim_paths(), [Sdf.Path.absoluteRootPath.pathString])

        # Clear and test simple case when asset is a stage
        selection.clear_selected_prim_paths()
        issue = omni.asset_validator.core.Issue(
            message="Test select pseudo root prim when issue asset is a stage ",
            severity=omni.asset_validator.core.IssueSeverity.ERROR,
            at=stage,
        )
        issue_item = omni.asset_validator.ui.IssueItem(IssueModel(issue))
        issue_item._select_prim()
        # Then
        self.assertEqual(selection.get_selected_prim_paths(), [Sdf.Path.absoluteRootPath.pathString])

    async def test_selected_issues(self) -> None:
        previous_content: str = Path(getUrl("complianceCheckerRoot.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            omni.usd.get_context().open_stage(str(destination))
            ui = omni.asset_validator.ui.get_instance()
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.enableRule(omni.asset_validator.core.ValidationRulesRegistry.rule("StageMetadataChecker"))

            # When
            results = await ui.validate_async()
            issues = results.issues()

            self.assertEqual(len(ui.selectedIssues), 0)

            # Then
            # Select one
            ui.selectIssue(issues[0])
            self.assertEqual(len(ui.selectedIssues), 1)

            # Select all
            for issue in issues:
                ui.selectIssue(issue)
            self.assertEqual(len(issues), len(ui.selectedIssues))

    async def test_issues_on_root_only(self) -> None:
        previous_content: str = Path(getUrl("complianceCheckerRoot.usda")).read_text()
        with TemporaryDirectory() as directory:
            destination = Path(directory).joinpath("test.usda")
            destination.write_text(previous_content)  # NOSONAR

            # Given
            omni.usd.get_context().open_stage(str(destination))
            ui = omni.asset_validator.ui.get_instance()
            ui.setAssetMode(omni.asset_validator.ui.AssetMode.Stage)
            ui.enableRule(omni.asset_validator.core.ValidationRulesRegistry.rule("StageMetadataChecker"))

            issue_on_root_only = ui.issueOnRootOnly

            # When
            ui.issueOnRootOnly = False
            results = await ui.validate_async()
            issues = results.issues()

            # Select all
            for issue in issues:
                ui.selectIssue(issue)

            self.assertEqual(len(issues), len(ui.selectedIssues))
            for issue in issues:
                self.assertTrue(issue in ui.selectedIssues)

            # Then
            ui.issueOnRootOnly = True

            # Select all
            for issue in issues:
                ui.selectIssue(issue)

            self.assertEqual(len(ui.selectedIssues), 0)  # No Issue on root layer
            # Restore
            ui.issueOnRootOnly = issue_on_root_only

    async def test_register_rule(self):
        # Given
        ui = omni.asset_validator.ui.get_instance()

        @omni.asset_validator.core.registerRule("TestCategory")
        class TestRule(omni.asset_validator.core.BaseRuleChecker):
            def CheckStage(self, stage: Usd.Stage):
                self._AddFailedCheck(message="Test complete", at=stage)

        # Then
        ui.enableRule(TestRule)
        self.assertTrue(ui.enabled(TestRule))

        uri = getUrl("helloworld.usda")
        ui.setAssetUri(uri)
        results = await ui.validate_async()
        issues = results.issues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].message, "Test complete")

        # Cleanup
        ui.disableRule(TestRule)
        omni.asset_validator.core.ValidationRulesRegistry.deregisterRule(TestRule)

        # Rule is no longer present in the UI
        ui.enableRule(TestRule)
        self.assertFalse(ui.enabled(TestRule))

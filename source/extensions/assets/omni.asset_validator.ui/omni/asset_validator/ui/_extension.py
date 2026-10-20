# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import omni.ext
from pxr import Usd

from .models._asset import AssetMode
from .models._model import ApplicationModel
from .views._commands import FixFn, ValidateFn
from .views._ui import AssetValidatorUI

g_singleton = None


class PublicExtension(omni.ext.IExt):
    """The public interface for the Asset Validator UI.

    Attributes:
        AssetMode (int): Mode of validation in the Asset Validator Window.
            Either `AssetMode.Uri`,`AssetMode.Stage` or `AssetMode.Prims` are accepted.

    Example:
        Initialize the UI and configure it for the user

        .. code-block:: python

            import omni.asset_validator.core
            import omni.asset_validator.ui

            ui = omni.asset_validator.ui.get_instance()

            # opt out of some rules
            ui.disableRule(omni.asset_validator.core.ValidationRulesRegistry.rule('TextureChecker'))
            ui.disableRule(omni.asset_validator.core.ValidationRulesRegistry.rule('KindChecker'))

            # make the window visible (though it could remain behind other windows)
            ui.show()

            # switch to the current stage
            ui.setAssetMode(ui.AssetMode.Stage)

            # run the validator
            import asyncio
            asyncio.ensure_future(ui.validate_async())

            # go back but retain your settings
            ui.reset()

            # switch to a bespoke stage and validate it in-memory, including any unsaved edits
            from pxr import Usd, Kind
            stage = Usd.Stage.Open('omniverse://localhost/NVIDIA/Samples/Astronaut/Astronaut.usd')
            prim = stage.DefinePrim(f'{stage.GetDefaultPrim().GetPath()}/MyCube', 'cube')
            Usd.ModelAPI(prim).SetKind(Kind.Tokens.component)
            ui.setStage(stage)
            asyncio.ensure_future(ui.validate_async())
    """

    def on_startup(self, ext_id):
        global g_singleton
        g_singleton = self
        self._model = ApplicationModel.get()  # Start up singletons
        self._ui = AssetValidatorUI(self._model)

    def on_shutdown(self):
        self._ui.shutdown()
        self._ui = None
        ApplicationModel.get.cache_clear()  # Clean up singletons
        self._model = None
        global g_singleton
        g_singleton = None

    def show(self) -> None:
        """Show the Asset Validator Window."""
        self._ui.visible = True

    def hide(self) -> None:
        """Hide the Asset Validator Window."""
        self._ui.visible = False

    def visible(self) -> bool:
        """Determine if the Asset Validator Window is currently visible.

        Note it may still be under another window.

        Returns:
            Bool indicating whether it is visible.
        """
        return self._ui.visible

    @property
    def variants(self) -> bool:
        """Determine if Asset Validator process all variants."""
        return self._model.settings_model.variants

    @variants.setter
    def variants(self, flag: bool) -> None:
        """
        Determine if Asset Validator process all variants.

        Args:
            flag (bool): Whether to process or not variants.
        """
        self._model.settings_model.variants = flag

    @property
    def instance_prototypes(self) -> bool:
        """Determine if Asset Validator processes instance prototypes."""
        return self._model.settings_model.instance_prototypes

    @instance_prototypes.setter
    def instance_prototypes(self, flag: bool) -> None:
        """
        Determine if Asset Validator processes instance prototypes.

        Args:
            flag (bool): Whether to process instance prototypes.
        """
        self._model.settings_model.instance_prototypes = flag

    @property
    def autovalidate(self) -> bool:
        """Determine if Asset Validator re-validates after fix."""
        return self._model.settings_model.autovalidate

    @autovalidate.setter
    def autovalidate(self, flag: bool) -> None:
        """
        Determine if Asset Validator re-validates after fix.

        Args:
            flag (bool): Whether to re-validate after applying fixes.
        """
        self._model.settings_model.autovalidate = flag

    @property
    def issueOnRootOnly(self) -> bool:
        """Determine if only listing issues on root layer."""
        return self._model.filters_model.root_only

    @issueOnRootOnly.setter
    def issueOnRootOnly(self, flag: bool) -> None:
        """
        Determine if only listing issues on root layer.

        Args:
            flag (bool): Whether to only list issues on root layer.
        """
        self._model.filters_model.root_only = flag
        self._model.results_model.filter_by = self._model.filters_model.predicate

    @property
    def selectedIssues(self) -> list[omni.asset_validator.core.Issue]:
        """List of issues that are selected in UI"""
        return [issue.issue for issue in self._model.results.selected_issues]

    def enableRule(self, Rule: omni.asset_validator.core.BaseRuleChecker) -> None:
        """
        Enable a given rule in the Asset Validator Window.

        This gives control to client code to enable rules one by one. Rules must be `BaseRuleChecker` derived classes,
        and **must be registered** with the `ValidationRulesRegistry` before they are enabled in the UI.

        Args:
            Rule: A `BaseRuleChecker` derived class to be enabled.
        """
        if model := self._model.categories_model.get(Rule):
            model.selected = True

    def disableRule(self, Rule: omni.asset_validator.core.BaseRuleChecker) -> None:
        """
        Disable a given rule in the Asset Validator Window.

        This gives control to client code to disable rules one by one. Rules must be `BaseRuleChecker` derived classes,
        and should be registered with the `ValidationRulesRegistry` before they are disabled in the UI.

        Args:
            Rule: A `BaseRuleChecker` derived class to be enabled
        """
        if model := self._model.categories_model.get(Rule):
            model.selected = False

    def enabled(self, Rule: omni.asset_validator.core.BaseRuleChecker) -> bool:
        """
        Check if the given rule is enabled in the Asset Validator Window.

        Args:
            Rule: A `BaseRuleChecker` derived class to be enabled.

        Returns:
            Bool indicating whether the given Rule is enabled. Note it does not guarantee the Rule exists.
        """
        if model := self._model.categories_model.get(Rule):
            return model.selected
        return False

    def reset(self, resetAssets: bool = False, resetRules: bool = False) -> None:
        """Reset the Asset Validator Window to its default state.

        If no arguments are provided the window will return to the selection page, but will remain in
        the same mode, with the same asset selected, and same rules enabled. This is equivalent of
        clicking the "Back to Rules Selection" button.

        Args:
            resetAssets: Flag to reset the configured Assets (both Uri and Stage).
            resetRules: Flag to reset the user selected Rules (all categories).
        """
        if resetAssets:
            self._model.reset_asset()
        if resetRules:
            self._model.reset_selection()

    def getAssetMode(self) -> AssetMode:
        """Get the current mode of validation that the Asset Validator Window will use.

        Returns:
            The current mode of validation that the Asset Validator Window will use.
        """
        return self._model.mode

    def setAssetMode(self, mode: AssetMode) -> None:
        """Set the current mode of validation that the Asset Validator Window will use.

        Args:
            mode: Either `AssetMode.Uri`,`AssetMode.Stage` or `AssetMode.Prims` are accepted.
        """
        self._model.mode = mode

    def getAssetUri(self) -> str:
        """Get the Asset URI that will be validated if the Asset Validator Window is in `Uri` mode.

        Returns:
            A single Omniverse Asset. Note this can be a file URI or folder/container URI.
        """
        return self._model.uri

    def setAssetUri(self, asset: str) -> None:
        """Set the Asset URI that will be validated if the Asset Validator Window is in `Uri` mode.

        Args:
            asset: A single Omniverse Asset. Note this can be a file URI or folder/container URI.
        """
        self._model.uri = asset

    def getStage(self) -> Usd.Stage:
        """Get the `Usd.Stage` that will be validated if the Asset Validator Window is in `Stage` mode.

        Returns:
            A live `Usd.Stage`.
        """
        return self._model.stage

    def setStage(self, stage: Usd.Stage) -> None:
        """Set the `Usd.Stage` that will be validated if the Asset Validator Window is in `Stage` mode.

        Args:
            stage: A live `Usd.Stage`.
        """
        self._model.stage = stage

    async def validate_async(self) -> list[omni.asset_validator.core.Results]:
        """Run the validation with the currently selected Asset in the current mode.

        This is equivalent to clicking the "Run Asset Validation" button. The Asset Validator Window will
        display results as normal, and they will be returned here for convenience once all assets have
        been validated.

        Returns:
            All issues reported by the enabled rules, index aligned with their respective asset.
            Note order of validation is not guaranteed. Re-validation of the same folder URI may
            return results in a different order.
        """
        validate = ValidateFn(self._model)
        await validate.apply_async()
        return self._model.results.as_results

    def selectIssue(self, issue: omni.asset_validator.core.Issue) -> bool:
        """
        Selects a given issue in the Asset Validator Window.

        This gives control to client code to select issues one by one.

        Args:
            issue: The issue to select in the UI.
        Returns:
            True if the issue was selected, False otherwise.
        """
        if model := self._model.results.find_issue(issue):
            model.selected = True
            return True
        return False

    async def fix(self) -> None:
        """
        Run the fix command with the currently selected Asset in the current mode.

        This is equivalent to clicking the "Fix" button, and unchecking "Save fixes".
        """
        self._model.settings_model.persist = False
        fix = FixFn(self._model)
        await fix.apply_async()

    async def fixAndSave(self) -> None:
        """
        Run the fix and save command with the currently selected Asset in the current mode.

        This is equivalent to clicking the "Fix" button, and checking "Save fixes".
        """
        self._model.settings_model.persist = True
        fix = FixFn(self._model)
        await fix.apply_async()

    async def fixIssue(self, issue: omni.asset_validator.core.Issue) -> None:
        """
        This is equivalent to clicking `Fix` on a specific Issue, and unchecking "Save fixes".
        """
        self._model.settings_model.persist = False
        fix = FixFn(self._model, issue)
        await fix.apply_async()

    async def fixAndSaveIssue(self, issue: omni.asset_validator.core.Issue) -> None:
        """
        This is equivalent to clicking `Fix` on a specific Issue, and checking "Save fixes".
        """
        self._model.settings_model.persist = True
        fix = FixFn(self._model, issue)
        await fix.apply_async()


def get_instance() -> PublicExtension:
    """Get the global instance of the Asset Validator UI Extension."""
    global g_singleton
    return g_singleton

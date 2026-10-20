# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass
from functools import singledispatchmethod

import omni.kit.app
from omni.asset_validator.core import AssetType, FixStatus, Issue, IssueFixer
from pxr import Sdf, Usd

from ..models._results import IssueModel, ResultsModel
from ._base import CommandFn
from ._validate import ValidateFn

__all__ = ["FixFn"]


@dataclass
class FixFn(CommandFn):
    issue: Issue | None = None

    @singledispatchmethod
    @classmethod
    def _open_stage(cls, asset: AssetType) -> Usd.Stage:
        raise NotImplementedError(f"Unknown type {type(asset)}")

    @_open_stage.register
    @classmethod
    def _(cls, asset: Usd.Stage) -> Usd.Stage:
        return asset

    @_open_stage.register
    @classmethod
    def _(cls, asset: str) -> Usd.Stage:
        return Usd.Stage.Open(Sdf.Layer.FindOrOpen(asset))

    async def _fix_async(self, asset: AssetType, issues: list[IssueModel]) -> None:
        stage: Usd.Stage = self._open_stage(asset)

        fixer = IssueFixer(stage)
        for issue in issues:
            result = fixer.apply(issue.issue, issue.fix_at, suggestion=issue.selected_suggestion)
            if result.status is FixStatus.SUCCESS:
                issue.fix_status = "Fixed"
            elif result.exception:
                issue.fix_status = f"Failed: {result.exception}"
            else:
                issue.fix_status = "Failed"
            await omni.kit.app.get_app().next_update_async()

        if self.model.settings_model.persist:
            try:
                fixer.save()
            except OSError as error:
                stage.Reload()
                for issue in issues:
                    issue.fix_status = f"Exception: {error}"
                    await omni.kit.app.get_app().next_update_async()

        if self.model.settings_model.autovalidate:
            func = ValidateFn(self.model, asset)
            await func.apply_async()
        elif asset_result := self.model.results.get_asset(asset):
            asset_result.outdated = True

    async def apply_async(self) -> None:
        results: ResultsModel = self.model.results
        for asset_result in results.assets:
            if self.issue:
                if model := asset_result.find_issue(self.issue):
                    await self._fix_async(asset_result.asset, [model])
            else:
                models: list[IssueModel] = asset_result.selected_issues
                if models:
                    await self._fix_async(asset_result.asset, models)

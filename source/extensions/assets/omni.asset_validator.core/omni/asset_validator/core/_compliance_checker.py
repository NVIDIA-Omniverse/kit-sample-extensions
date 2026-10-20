# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import singledispatchmethod

import omni.core
import omni.log
from omni.asset_validator import (
    AssetType,
    AsyncComplianceCheckerRunner,
    BaseRuleChecker,
    ComplianceChecker,
    ValidationStats,
)
from pxr import Sdf, Usd

__all__ = [
    "OmniComplianceChecker",
    "is_omni_path",
]

_OMNI_PRIM_PATHS: set[Sdf.Path] = {
    Sdf.Path("/OmniverseKit_Persp"),
    Sdf.Path("/OmniverseKit_Front"),
    Sdf.Path("/OmniverseKit_Top"),
    Sdf.Path("/OmniverseKit_Right"),
    Sdf.Path("/OmniKit_Viewport_LightRig"),
}
"""Set: Exact paths created by Kit which should be ignored by Rules."""

_OMNI_PRIM_NAMES: set[str] = {
    "OmniverseKitViewportCameraMesh",
}
"""Set: Exact names of prims created by Kit which should be ignored by Rules."""


def is_omni_path(path: Sdf.Path) -> bool:
    """
    Args:
        path: An Sdf Path object.

    Returns:
        True if this is used internally by Omniverse.
    """
    return path in _OMNI_PRIM_PATHS or path.name in _OMNI_PRIM_NAMES


@dataclass
class _PrimRangeWrapper:
    """
    A prim range wrapper that ignores kit prims.
    """

    it: Usd.PrimRange

    def __getattr__(self, name):
        return getattr(self.it, name)

    def __iter__(self) -> Iterator[Usd.Prim]:
        for prim in self.it:
            if is_omni_path(prim.GetPath()):
                self.it.PruneChildren()
            else:
                yield prim


class _SupressLogs:
    """While validating we can hit again multiple composition errors. Since this can be huge, we supress them."""

    def __init__(self):
        log = omni.log.get_log()
        self.log_result, self.log_level, self.log_behavior = log.get_channel_level("omni.usd")

    def __enter__(self) -> _SupressLogs:
        if self.log_result != omni.core.Result.NOT_FOUND:
            log = omni.log.get_log()
            log.set_channel_level("omni.usd", omni.log.Level.ERROR, omni.log.SettingBehavior.OVERRIDE)
        return self

    def __exit__(self, *_) -> None:
        if self.log_result != omni.core.Result.NOT_FOUND:
            log = omni.log.get_log()
            log.set_channel_level("omni.usd", self.log_level, self.log_behavior)


@dataclass
class _AsyncComplianceCheckerRunner(AsyncComplianceCheckerRunner):

    _supress_logs: _SupressLogs = field(init=False, default_factory=_SupressLogs)

    async def flush(self) -> None:
        # The async runner drains all pending work through flush(), including context exit and FLUSH events.
        with self._supress_logs:
            await super().flush()


class OmniComplianceChecker(ComplianceChecker):
    """
    A specific implementation of compliance checker for Kit.
    """

    @singledispatchmethod
    @classmethod
    def _create_stage(cls, asset: AssetType) -> Usd.Stage:
        return super()._create_stage(asset)

    @_create_stage.register
    @classmethod
    def _(cls, asset: str) -> Usd.Stage:
        with _SupressLogs():
            return super()._create_stage(asset)

    @_create_stage.register
    @classmethod
    def _(cls, asset: Usd.Stage) -> Usd.Stage:
        with _SupressLogs():
            return super()._create_stage(asset)

    @classmethod
    def _create_async_runner(
        cls,
        rules: list[BaseRuleChecker],
        stats: ValidationStats,
        *,
        processes: int = 0,
    ) -> AsyncComplianceCheckerRunner:
        return _AsyncComplianceCheckerRunner(rules=rules, stats=stats, processes=processes)

    def _create_prims_it(self, root: Usd.Stage | Usd.Prim):
        return _PrimRangeWrapper(super()._create_prims_it(root))

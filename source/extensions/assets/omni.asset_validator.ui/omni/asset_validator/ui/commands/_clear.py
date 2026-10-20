# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass

from ..models._results import ResultsModel
from ._base import CommandFn

__all__ = ["ClearFn"]


@dataclass
class ClearFn(CommandFn):

    async def apply_async(self) -> None:
        results: ResultsModel = self.model.results
        results.clear()

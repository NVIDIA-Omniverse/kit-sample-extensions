# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import asyncio
from dataclasses import dataclass, field

from ..models._model import ApplicationModel

__all__ = ["CommandFn"]


@dataclass
class CommandFn:
    model: ApplicationModel = field(default_factory=ApplicationModel.get)

    async def apply_async(self) -> None:
        raise NotImplementedError(f"Unknown command type {type(self)}")

    def apply(self) -> asyncio.Task:
        task: asyncio.Task = asyncio.ensure_future(self.apply_async())
        self.model.add_task(task)
        return task

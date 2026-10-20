# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable

from omni.kit.viewport.window.dragdrop import DragDropDelegate


class MaterialDragDropObject(DragDropDelegate):
    """
    Material drop delegate based on _LegacyDragDropObject in omni.kit.viewport.window but support Model Selection.
    """

    def __init__(self, add_outline: bool, test_accepted_fn: Callable, drop_fn: Callable, pick_complete: Callable):
        super().__init__()
        self.__add_outline = add_outline
        self.__test_accepted_fn = test_accepted_fn
        self.__dropped = drop_fn
        self.__pick_complete = pick_complete

    @property
    def add_outline(self):
        return self.__add_outline

    @property
    def honor_picking_mode(self):  # pragma: no cover - not ever called
        return True

    def accepted(self, drop_data: dict):
        url = drop_data["mime_data"]
        return self.__test_accepted_fn(url) if self.__test_accepted_fn else False

    def dropped(self, drop_data: dict):
        url = drop_data["mime_data"]
        if (self.__dropped is not None) and url and self.accepted(drop_data):
            prim_path = drop_data.get("prim_path")
            prim_path = prim_path.pathString if prim_path else None
            model_path = drop_data.get("model_path")
            model_path = model_path.pathString if model_path else None

            usd_context_name = drop_data.get("usd_context_name", "")
            payload = self.__dropped(url, prim_path, model_path, "", usd_context_name)
            if payload and self.__pick_complete:
                self.__pick_complete(payload, prim_path, usd_context_name)

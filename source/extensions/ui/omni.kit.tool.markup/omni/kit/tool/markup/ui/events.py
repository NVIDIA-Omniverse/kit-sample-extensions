# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from types import MethodType
from typing import Callable
from weakref import WeakMethod, ref


class MarkupEvent:
    def __init__(self, **data) -> None:
        self._handlers = set()
        self._data = data

    def add_handler(self, handler: "Callable[..., object]") -> "MarkupEvent":
        if not callable(handler):
            raise ValueError("Event handler's must be callable.")

        if isinstance(handler, MethodType):
            self._handlers.add(WeakMethod(handler))
        else:
            self._handlers.add(ref(handler))
        return self

    def remove_handler(self, handler: "Callable[..., object]") -> "MarkupEvent":
        if not callable(handler):
            raise ValueError("Event handler's must be callable.")

        if isinstance(handler, MethodType):
            self._handlers.discard(WeakMethod(handler))
        else:
            self._handlers.discard(ref(handler))
        return self

    def run(self, *args, **kwargs) -> None:
        active_handlers = {r() for r in self._handlers if r()}
        self._handlers.clear()
        for handler in active_handlers:
            d = {**self._data, **kwargs}
            handler(*args, **d)
            self.add_handler(handler)

    __iadd__ = add_handler
    __isub__ = remove_handler
    __call__ = run

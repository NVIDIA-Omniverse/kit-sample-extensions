# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import sys
from typing import Callable, Dict, Optional, Type

from carb import settings

from .provider import MeasureSnapProvider


class MeasureSnapProviderRegistry:
    def __singleton_init__(self):
        self._providers: Dict[str, Type[MeasureSnapProvider]] = {}
        self._change_subscribers: Dict[int, Callable] = {}
        self._next_change_subscriber_id: int = 1
        self._settings = settings.get_settings()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.__singleton_init__()
        return cls._instance

    def __del__(self):
        self.destroy()

    def destroy(self):
        MeasureSnapProviderRegistry._instance = None

    @property
    def providers(self) -> Dict[str, Type[MeasureSnapProvider]]:
        """
        Gets all provider classes
        """
        return self._providers

    def get_provider_class_by_name(self, name: str) -> Optional[Type[MeasureSnapProvider]]:
        """
        Get provider class by its name. None if not found
        """
        return self._providers.get(name, None)

    def register(self, provider: Type[MeasureSnapProvider]):
        """
        Registers a provider class to the registry.

        Args:
            provider (Type[MeasureSnapProvider]): The class of the provider to be registered.
        """
        id = provider.get_name()
        if id in self._providers:
            raise ValueError(f"{id} already exists")

        self._providers[id] = provider
        self._notify_registry_changed()

    def unregister(self, provider: Type[MeasureSnapProvider]):
        """
        Unregisters a provider class.

        Args:
            provider (Type[MeasureSnapProvider]): The MeasureSnapProvider class to be unregisterd.
        """
        id = provider.get_name()
        self._providers.pop(id, None)
        self._notify_registry_changed()

    def add_on_registry_changed_fn(self, callback: Callable[[], None]) -> int:
        id = self._next_change_subscriber_id
        self._next_change_subscriber_id += 1
        self._change_subscribers[id] = callback
        self._notify_registry_changed(callback)
        return id

    def remove_on_registry_changed_fn(self, id: int):
        self._change_subscribers.pop(id)

    def _notify_registry_changed(self, callback: Optional[Callable[[], None]] = None):
        if callback:
            callback()
        else:
            for sub in self._change_subscribers.values():
                sub()

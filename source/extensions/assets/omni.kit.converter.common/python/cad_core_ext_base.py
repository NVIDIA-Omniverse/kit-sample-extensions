# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import List, Optional

import carb
import omni.ext
import omni.kit.app

from .common import ConverterFilterData

__all__ = ["ICadCoreExtBase"]


class ICadCoreExtBase(omni.ext.IExt):
    """
    Base Cad Converter Extension Class
    """

    FILTER_DATA = None
    OPTIONS_CLS = None
    SERVICE_TITLE = None

    def _on_startup(self, ext_id):
        """Initializes the Converter and/or registers the service

        *This must be called by any subclass in their on_startup method
        """
        self._converter_id = None
        self._ext_id = ext_id
        self._register_service()

    def _on_shutdown(self):
        """Uninitialize the Converter and/or un-registers the service

        *This must be called by any subclass in their on_shutdown method
        """
        self._unregister_service()

    def _register_service(self):
        converter_registry = self.get_converter_registry()
        if converter_registry is None:
            carb.log_info("ConverterRegistry class does not exist... skipping registration")
            return

        extension_filters = []
        for extension in self.FILTER_DATA:
            extension_filters.extend(extension.filter_regexes)

        self._converter_id = converter_registry.register_converter(
            filters=extension_filters,
            convert_fn=self.create_converter_task,
            options_cls=self.OPTIONS_CLS,
        )

    def _unregister_service(self):
        converter_registry = self.get_converter_registry()
        if converter_registry is None:
            carb.log_info("ConverterRegistry class does not exist... skipping unregistration")
            return

        converter_registry.unregister_converter(self._converter_id)

    def get_converter_registry(self) -> Optional["ConverterRegistry"]:
        """Import and return ConverterRegistry or None if service ext is not loaded"""
        try:
            from omni.services.convert.cad import ConverterRegistry
        except ImportError:
            ConverterRegistry = None

        return ConverterRegistry

    def get_ext_name(self) -> str:
        """Return the extension name, ie: omni.kit.converter.hoops_core

        Returns: `str`
        """
        return omni.ext.get_extension_name(self._ext_id)

    def get_ext_path(self) -> Path:
        """Return the path to the extension

        Returns: `Path`
        """
        manager = omni.kit.app.get_app().get_extension_manager()
        return Path(manager.get_extension_path(self._ext_id))

    def get_ext_version(self) -> str:
        """Return the version of the extension

        Returns: `str`"""
        manager = omni.kit.app.get_app().get_extension_manager()
        return manager.get_extension_dict(self._ext_id)["package"]["version"]

    def get_filters(self) -> List[ConverterFilterData]:
        """Return list of `ConverterFilterData`"""
        extension_filters = []
        for extension in self.FILTER_DATA:
            extension_filters.extend(extension.filter_regexes)

        return extension_filters

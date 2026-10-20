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
from typing import List

import omni.ext
import omni.kit.app

try:
    import omni.kit.tool.asset_importer as ai
except ImportError:
    ai = None

from .common import ConverterFilterData

__all__ = ["ICadExtBase"]


class ICadExtBase(omni.ext.IExt):
    """
    Base Cad Converter Extension Class
    """

    DELEGATE = None
    FILTER_DATA = None

    def __init__(self):
        super().__init__()
        self.converter_delegates = []

    def get_ext_name(self) -> str:
        """Return the extension name, ie: omni.kit.converter.hoops

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

    def _on_startup(self, ext_id):
        """Initializes the Converter and/or registers the service

        *This must be called by any subclass in their on_startup method
        """
        self._ext_id = ext_id
        self._register_importer()

    def _on_shutdown(self):
        """Uninitialize the Converter and/or un-registers the service

        *This must be called by any subclass in their on_shutdown method
        """
        self._unregister_importer()

    def _register_importer(self) -> None:
        """Registers each converter delegate as an Asset Importer"""
        if ai is not None:
            for filter_data in self.FILTER_DATA:
                delegate = self.DELEGATE(
                    filter_data.name, filter_data.filter_regexes, filter_data.filter_descriptions, filter_data.priority
                )
                ai.register_importer(delegate)
                self.converter_delegates.append(delegate)

    def _unregister_importer(self) -> None:
        """Unregisters each converter delegate as an Asset Importer"""
        for delegate in self.converter_delegates:
            if delegate:
                delegate.destroy()
                ai.remove_importer(delegate)
        self.converter_delegates.clear()

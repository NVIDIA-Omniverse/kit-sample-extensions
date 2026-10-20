# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Any, Optional

import omni.ext
import omni.usd
from omni.kit.window.preferences import register_page, unregister_page
from pxr import Sdf

from .actions import deregister_actions, register_actions
from .environment_page import EnvironmentPage
from .ground import GroundHelper
from .models import UsdModelBuilder
from .sky import SkyHelper
from .sunstudy_player import SunstudyPlayer

_extension_instance = None


class EnvironmentCoreExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        try:
            self.__ext_id = omni.ext.get_extension_name(ext_id)
        except AttributeError:  # pragma: no cover

            def get_extension_name(ext_id: str) -> str:
                """Convert 'omni.foo-tag-1.2.3' to 'omni.foo-tag'"""
                a, b, *_ = ext_id.split("-") + [""]
                if b and not b[0:1].isdigit():
                    return f"{a}-{b}"
                return a

            self.__ext_id = get_extension_name(ext_id)
        self._page = EnvironmentPage()
        register_page(self._page)
        register_actions(self.__ext_id)

        self._sky_helper = SkyHelper()
        self._ground_helper = GroundHelper()
        self._sunstudy_player: Optional[SunstudyPlayer] = None
        self._usd_model_builder = UsdModelBuilder()

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        deregister_actions(self.__ext_id)
        self._usd_model_builder.destroy()

        self._page.destroy()
        unregister_page(self._page)
        self._page = None

        if self._sunstudy_player is not None:
            self._sunstudy_player.destroy()
            self._sunstudy_player = None

        self._sky_helper.destroy()
        self._ground_helper.destroy()

        global _extension_instance
        _extension_instance = None

    def get_sunstudy_player(self):
        if self._sunstudy_player is None:
            self._sunstudy_player = SunstudyPlayer()
        return self._sunstudy_player

    def create_property_model(
        self, property_path: str, value_type: Sdf.ValueTypeName = Sdf.ValueTypeNames.String, default: Any = ""
    ):
        return self._usd_model_builder.create_property_value_model(
            property_path, value_type=value_type, default=default
        )


def get_instance() -> Optional[EnvironmentCoreExtension]:
    return _extension_instance


def get_sunstudy_player() -> SunstudyPlayer:
    """Return the current SunstudyPlayer instance for controlling sun study parameters.

    Returns:
        SunstudyPlayer: The SunstudyPlayer instance if the extension is active, else None.
    """
    instance = get_instance()
    if instance:
        return instance.get_sunstudy_player()
    else:
        return None

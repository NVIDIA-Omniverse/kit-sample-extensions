# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import weakref

import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.property.environment import EnvironmentPropertyWidget
from omni.kit.property.usd import PrimSelectionPayload

from .property_style import get_style


class PropertyWidget:
    """
    Kinds of property widgets for environment.
    """

    def __init__(self):
        self._property_widget = EnvironmentPropertyWidget()

        self._stage_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.window.environment.PropertyWidget",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=lambda _: self._on_stage_opened(),
        )

        self._build_ui()

        stage = omni.usd.get_context().get_stage()
        if stage:
            self._on_stage_opened()

    def destroy(self):
        self._stage_sub = None
        self._property_widget.destroy()

    def _build_ui(self):
        self._property_container = ui.VStack(style=get_style())
        with self._property_container:
            with ui.ScrollingFrame(
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            ):
                with ui.VStack():
                    self._property_widget.build()

    @property
    def visible(self) -> bool:
        return self._property_container.visible

    @visible.setter
    def visible(self, value) -> None:
        self._property_container.visible = value

    def _on_stage_opened(self):
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if stage:
            payload = PrimSelectionPayload(weakref.ref(stage), ["/Environment"])
            self._property_widget.on_new_payload(payload)

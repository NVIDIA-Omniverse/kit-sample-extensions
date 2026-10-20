# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import weakref

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui


class SchemaAPIWidgetExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self._add_schemaapi_popup = None
        self._stage_event_sub = None

    def on_startup(self, ext_id):
        from omni.kit.property.usd import PrimPathWidget

        if hasattr(omni.kit.property.usd, "get_registered_schemas"):
            from .add_schema_api_popup import AddSchemaAPIPopup

            self._add_schemaapi_popup = AddSchemaAPIPopup()
            self._schemaapi_widget = PrimPathWidget.add_button_menu_entry(
                "Edit API Schema  ",
                show_fn=None,
                onclick_fn=lambda payload, weak_self=weakref.ref(self): (
                    weak_self()._add_schemaapi_popup.show_window(payload, self.__class__.__name__)
                    if weak_self()
                    else None
                ),
            )
            self._stage_event_sub = (
                omni.usd.get_context()
                .get_stage_event_stream()
                .create_subscription_to_pop(self._on_stage_event, name="omni.kit.widget.schema_api")
            )
        else:  # pragma: no cover
            carb.log_warn("not compatible with this version of omni.kit.property.usd. Version 4.3.0+ is required")
            return

    def on_shutdown(self):  # pragma: no cover
        from omni.kit.property.usd import PrimPathWidget

        PrimPathWidget.remove_button_menu_entry(self._schemaapi_widget)
        if self._stage_event_sub:
            self._stage_event_sub = None

        if self._add_schemaapi_popup:
            self._add_schemaapi_popup.destroy()
            self._add_schemaapi_popup = None
            self._schemaapi_widget = None

    def _on_stage_event(self, event):
        if self._add_schemaapi_popup:
            match omni.usd.StageEventType(event.type):
                case omni.usd.StageEventType.CLOSING | omni.usd.StageEventType.CLOSED:
                    self._add_schemaapi_popup.destroy()

                case omni.usd.StageEventType.SELECTION_CHANGED:
                    if self._add_schemaapi_popup._window and self._add_schemaapi_popup._window.visible:
                        self._add_schemaapi_popup.show_window(
                            omni.kit.window.property.get_window().get_payload(), self.__class__.__name__
                        )

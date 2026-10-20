# * Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
# *
# * NVIDIA CORPORATION and its licensors retain all intellectual property
# * and proprietary rights in and to this software, related documentation
# * and any modifications thereto.  Any use, reproduction, disclosure or
# * distribution of this software and related documentation without an express
# * license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
from typing import Optional

import carb
import carb.eventdispatcher
import omni
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.tool.remove_unused.core import RemoveUnusedCore as core

SETTING_MATERIAL_PANEL_MODE = "/exts/omni.kit.window.material/panel_mode"
MATERIAL_PANEL_MODE_STAGE = "Current Stage"


class RemoveUnusedController:
    def __init__(self, usd_context_name: str = ""):
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._hooks = None
        self.__add_menu_future: Optional[asyncio.Future] = None
        self._panel_mode_sub = None
        self._create_ui()

        self._stage_event_observers = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.tool.remove_unused.controller:RemoveUnusedController",
                event_name=self._usd_context.stage_event_name(event_type),
                on_event=func,
            )
            for event_type, func in (
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSING, lambda _: self._on_stage_closing()),
            )
        ]

        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_opened()

    def _create_ui(self):
        """Create the main UI"""
        import omni.kit.app

        manager = omni.kit.app.get_app().get_extension_manager()
        self._popup = None

        self._hooks = manager.subscribe_to_extension_enable(
            lambda _: self._on_material_window_enabled(),
            lambda _: self._on_material_window_disabled(),
            ext_name="omni.kit.window.material",
            hook_name="omni.kit.tool.remove_unused.controller listener",
        )

    def _on_material_window_enabled(self):
        settings = carb.settings.get_settings()
        panel_mode = settings.get(SETTING_MATERIAL_PANEL_MODE)
        # This panel mode setting becomes available from omni.kit.widnow.material v1.8.0
        if panel_mode is not None:
            if panel_mode == MATERIAL_PANEL_MODE_STAGE:
                self.__add_stage_options_menu()
            else:

                def __on_panel_mode_changed(_, event_type: carb.settings.ChangeEventType):
                    if event_type == carb.settings.ChangeEventType.CHANGED:
                        panel_mode = settings.get(SETTING_MATERIAL_PANEL_MODE)
                        if panel_mode == MATERIAL_PANEL_MODE_STAGE:
                            self.__add_stage_options_menu()
                            self._panel_mode_sub = None

                self._panel_mode_sub = settings.subscribe_to_node_change_events(
                    SETTING_MATERIAL_PANEL_MODE, __on_panel_mode_changed
                )

        else:
            from omni.kit.window.material import get_instance as get_mat_inst

            matbrowser_inst = get_mat_inst()
            material_window: ui.Window = matbrowser_inst._window
            if material_window:
                self.__add_menu()
            else:
                # Wait for window becomes visible
                self.__sub_materials_window = ui.Workspace.set_window_visibility_changed_callback(
                    self._on_window_visible
                )

    def __add_stage_options_menu(self):
        from omni.kit.browser.core import OptionMenuDescription
        from omni.kit.window.material import get_instance as get_mat_inst

        matbrowser_inst = get_mat_inst()
        material_window: ui.Window = matbrowser_inst._window
        menu_desc = OptionMenuDescription(
            "Remove Unused Materials",
            clicked_fn=self._open_popup_dialog,
        )

        # Make sure only append menu item once
        if matbrowser_inst.stage_options_menu and menu_desc not in matbrowser_inst.stage_options_menu._menu_descs:
            matbrowser_inst.stage_options_menu.append_menu_item(menu_desc)

    def __add_menu(self):
        from omni.kit.window.material import get_instance as get_mat_inst

        matbrowser_inst = get_mat_inst()
        material_window: ui.Window = matbrowser_inst._window
        # Material window is always docked after startup
        # And UI is really built until it is selected in dock
        if material_window.docked and material_window.is_selected_in_dock():
            self.__add_stage_options_menu()
        else:

            async def __add_stage_options_menu_async():
                # OM-72443: set callback again does not work, have to make sure menu item only appened once
                material_window.set_selected_in_dock_changed_fn(__on_selected_in_dock_changed)

                # Wait for stage options menu created
                while matbrowser_inst.stage_options_menu is None:
                    await omni.kit.app.get_app().next_update_async()

                self.__add_stage_options_menu()

            def __on_selected_in_dock_changed(selected: bool):
                if selected and self.__add_menu_future is None:
                    self.__add_menu_future = asyncio.ensure_future(__add_stage_options_menu_async())

            material_window.set_selected_in_dock_changed_fn(__on_selected_in_dock_changed)

    def _on_window_visible(self, title: str, visible: bool):
        if title == "Materials":
            ui.Workspace.remove_window_visibility_changed_callback(self.__sub_materials_window)

            async def __add_menu_delay():
                for _ in range(2):
                    await omni.kit.app.get_app().next_update_async()
                self.__add_menu()

            asyncio.ensure_future(__add_menu_delay())

    def _on_material_window_disabled(self):
        self._close_popup_dialog()

    def _open_popup_dialog(self) -> None:
        self._stage = self._usd_context.get_stage()
        if self._popup:
            self._popup.destroy()
            self._popup = None
        matlist = set()
        matlist = core.get_excess_materials(self._stage)
        if matlist:
            message = f"The following {len(matlist)} materials will be deleted:"
        else:
            message = "There are no unbound materials in this stage."
        if not self._popup:
            flags = ui.WINDOW_FLAGS_NO_RESIZE
            flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
            flags |= ui.WINDOW_FLAGS_MODAL
            self._popup = ui.Window("Warning", width=400, height=290, flags=flags)
            with self._popup.frame:
                with ui.VStack(
                    name="root",
                    style={"VStack::root": {"margin": 10}},
                    height=0,
                    spacing=20,
                ):
                    ui.Label(message, alignment=ui.Alignment.CENTER)
                    scroll = ui.ScrollingFrame(
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        height=150,
                    )
                    with scroll:
                        with ui.VStack():
                            for mat in matlist:
                                with ui.HStack(width=100, height=15):
                                    ui.Label(mat, width=80, height=10)
                    with ui.HStack():
                        ui.Spacer()
                        ui.Button(
                            "Ok",
                            width=100,
                            height=25,
                            clicked_fn=self._remove_mats_clicked,
                        )
                        ui.Spacer()
                        ui.Button(
                            "Cancel",
                            width=100,
                            height=25,
                            clicked_fn=self._close_popup_dialog,
                        )
                        ui.Spacer()
        self._popup.visible = True

    def _close_popup_dialog(self) -> None:
        if self._popup:
            self._popup.visible = False

    def _remove_mats_clicked(self):
        core.find_and_delete_mats(self._stage)
        if self._popup:
            self._popup.visible = False

    def _on_stage_opened(self):
        self._stage = self._usd_context.get_stage()

    def _on_stage_closing(self):
        self._stage = None

    def destroy(self):
        self._panel_mode_sub = None
        if self.__add_menu_future and not self.__add_menu_future.done():
            self.__add_menu_future.cancel()
        self.__add_menu_future = None

        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_closing()

        self._stage_event_observers.clear()

        if self._hooks:
            self._hooks = None
        if self._popup:
            self._popup.destroy()
            self._popup = None

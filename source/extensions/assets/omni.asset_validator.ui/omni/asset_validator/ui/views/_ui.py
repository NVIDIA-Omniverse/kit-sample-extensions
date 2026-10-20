# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import contextlib

import omni.kit.menu.utils
import omni.ui
from omni.asset_validator.core import ValidationEngine
from pxr import Sdf, Usd, UsdGeom

from ..models._asset import AssetMode
from ..models._model import ApplicationModel
from ._icons import Icons
from ._main import MainWidget
from ._stage_menu import StageMenu
from ._style import FRAME_STYLE


class AssetValidatorUI:

    # ComboBox requires it to be int
    def __init__(self, model: ApplicationModel) -> None:
        self._model = model
        self._build_window()
        self._connect_main_menu()

        # OMPE-22957: USD Composer Missing Asset Validator When Right-Clicking Stage Panel
        # Optional extensions.
        with contextlib.suppress(Exception):
            self._connect_content_browser()
        with contextlib.suppress(Exception):
            self._stage_menu = StageMenu(model, clicked_fn=self.show)
        with contextlib.suppress(Exception):
            self._connect_layer_window()

    def shutdown(self) -> None:
        self._disconnect_main_menu()
        with contextlib.suppress(Exception):
            self._disconnect_content_browser()
        with contextlib.suppress(Exception):
            self._stage_menu.release()
        with contextlib.suppress(Exception):
            self._disconnect_layer_window()
        self._destroy_window()

    @property
    def visible(self) -> bool:
        return self._window.visible

    @visible.setter
    def visible(self, flag: bool) -> None:
        self._window.visible = flag

    def show(self) -> None:
        self.visible = True

    def _build_frame(self) -> None:
        MainWidget(self._model)

    def _build_window(self) -> None:
        self._window = omni.ui.Window("Asset Validator", width=1200, height=700, visible=False)
        self._window.frame.set_style(FRAME_STYLE)
        self._window.frame.set_build_fn(self._build_frame)

    def _destroy_window(self) -> None:
        self._window.destroy()
        self._window = None

    def _validate_uri_callback(self, uri: str) -> None:
        self._model.mode = AssetMode.Uri
        self._model.uri = uri
        self.visible = True

    def _validate_layer_callback(self, layer: Sdf.Layer, mode: AssetMode) -> None:
        self._model.mode = mode
        if mode is AssetMode.Uri:
            self._model.uri = layer.identifier
        elif mode is AssetMode.Stage:
            anon_stage = Usd.Stage.CreateInMemory(layer.GetDisplayName())
            app_stage = omni.usd.get_context().get_stage()
            anon_stage.SetMetadata(UsdGeom.Tokens.upAxis, app_stage.GetMetadata(UsdGeom.Tokens.upAxis))
            anon_stage.SetMetadata(UsdGeom.Tokens.metersPerUnit, app_stage.GetMetadata(UsdGeom.Tokens.metersPerUnit))
            anon_stage.GetSessionLayer().subLayerPaths.insert(0, layer.identifier)
            if layer.HasDefaultPrim():
                anon_stage.SetDefaultPrim(anon_stage.GetPseudoRoot().GetPrimAtPath(layer.defaultPrim))
            self._model.stage = anon_stage
        self.visible = True

    def _connect_main_menu(self) -> None:
        """Creates the menu `Window / Asset Validator`"""
        self._menu_action = omni.kit.actions.core.Action(
            "omni.asset_validator.ui",
            "toggle",
            self._toggle_window,
        )
        omni.kit.actions.core.get_action_registry().register_action(self._menu_action)

        self._menu_list = [
            omni.kit.menu.utils.MenuItemDescription(
                name=self._window.title,
                ticked=True,
                ticked_fn=lambda: self.visible,
                onclick_action=("omni.asset_validator.ui", "toggle"),
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, "Window")

        self._window.set_visibility_changed_fn(lambda _: omni.kit.menu.utils.refresh_menu_items("Window"))

    def _toggle_window(self) -> None:
        self.visible = not self.visible

    def _disconnect_main_menu(self) -> None:
        """"""
        self._window.set_visibility_changed_fn(None)

        omni.kit.menu.utils.remove_menu_items(self._menu_list, "Window")
        self._menu_list = None

        omni.kit.actions.core.get_action_registry().deregister_all_actions_for_extension("omni.asset_validator.ui")
        self._menu_action = None

    def _connect_content_browser(self):
        import omni.kit.window.content_browser

        content_browser = omni.kit.window.content_browser.get_content_window()
        content_browser.add_context_menu(
            "Validate USD",
            glyph=Icons.CONTEXT_MENU,
            click_fn=lambda _, path: self._validate_uri_callback(path),
            show_fn=lambda path: ValidationEngine.is_asset_supported(path),
        )
        content_browser.add_context_menu(
            "Search for USD files and Validate",
            glyph=Icons.CONTEXT_MENU,
            click_fn=lambda _, path: self._validate_uri_callback(path),
            show_fn=lambda path: content_browser.window.widget.api.context_menu._context["item"].is_folder,
        )

    def _disconnect_content_browser(self):
        import omni.kit.window.content_browser

        content_browser = omni.kit.window.content_browser.get_content_window()
        content_browser.delete_context_menu("Validate USD")
        content_browser.delete_context_menu("Search for USD files and Validate")

    def _connect_layer_window(self):
        import omni.kit.widget.layers

        self._layerContextMenuConnections = []
        self._layerContextMenuConnections.append(
            omni.kit.widget.layers.ContextMenu.add_menu(
                [
                    {"name": ""},
                    {
                        "name": "Validate Layer (w/unsaved changes)",
                        "glyph": Icons.CONTEXT_MENU,
                        "onclick_fn": lambda objects: self._validate_layer_callback(
                            layer=omni.kit.widget.layers.ContextMenu._get_layer_item(objects).layer,
                            mode=AssetMode.Stage,
                        ),
                        "show_fn": [
                            omni.kit.widget.layers.ContextMenu.is_layer_item,
                            omni.kit.widget.layers.ContextMenu.is_not_from_session_layer_tree,
                            omni.kit.widget.layers.ContextMenu.is_layer_dirty,
                        ],
                    },
                    {
                        "name": "Validate Layer (in-memory)",
                        "glyph": Icons.CONTEXT_MENU,
                        "onclick_fn": lambda objects: self._validate_layer_callback(
                            layer=omni.kit.widget.layers.ContextMenu._get_layer_item(objects).layer,
                            mode=AssetMode.Stage,
                        ),
                        "show_fn": [
                            omni.kit.widget.layers.ContextMenu.is_layer_item,
                            omni.kit.widget.layers.ContextMenu.is_not_from_session_layer_tree,
                            lambda objects: not omni.kit.widget.layers.ContextMenu.is_layer_dirty(objects),
                        ],
                    },
                    {
                        "name": "Validate Layer (from file)",
                        "glyph": Icons.CONTEXT_MENU,
                        "onclick_fn": lambda objects: self._validate_layer_callback(
                            layer=omni.kit.widget.layers.ContextMenu._get_layer_item(objects).layer,
                            mode=AssetMode.Uri,
                        ),
                        "show_fn": [
                            omni.kit.widget.layers.ContextMenu.is_layer_item,
                            omni.kit.widget.layers.ContextMenu.is_not_anonymous_layer,
                        ],
                    },
                ]
            )
        )

    def _disconnect_layer_window(self):
        self._layerContextMenuConnections = None

# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
from typing import List, Set

import carb
import omni.ui as ui
import omni.usd
from carb import settings
from pxr import Sdf, Usd

from .browser_model import AssetDetailItem
from .combobox_model import ComboBoxItem
from .style import CONTEXT_MENU_STYLE


class ContextMenu(ui.Menu):
    """
    Context menu for simready asset browser.
    """

    def __init__(self):
        super().__init__("SimReady Asset browser context menu", style=CONTEXT_MENU_STYLE)
        self._settings = settings.get_settings()

    def show_item(self, item: AssetDetailItem) -> None:
        self.clear()

        from .extension import get_instance

        selection: List[AssetDetailItem] = (
            get_instance().browser_widget.selection if get_instance().browser_widget else []
        )
        if not selection and not item:
            return

        assets: List[AssetDetailItem] = selection if selection else [item]
        # Gather all physics variant values from all the selected assets
        possible_physics_values = set()
        for asset in assets:
            physics_items = asset.physics_model.get_item_children(None) if asset.physics_model else []
            possible_physics_values.update(item.value for item in physics_items)

        # Compute common physics variant value all selected assets share
        common_physics_value = assets[0].physics
        for asset in assets:
            if asset.physics != common_physics_value:
                common_physics_value = None
                break

        with self:
            # Behavior menu (only physics for now)
            # Always create new menu items to match asset variant settings
            if len(possible_physics_values) > 1:
                with ui.MenuItemCollection(f"{ui.get_custom_glyph_code('${glyphs}/none.svg')}  Physics"):
                    for physics_value in possible_physics_values:
                        value = physics_value
                        ui.MenuItem(
                            value or "None",
                            checked=(value == common_physics_value),
                            checkable=True,
                            triggered_fn=(lambda assets=assets, v=value: self.__set_item_physics(assets, v)),
                        )
            # Some right-click commands only make sense when only one asset is selected
            if len(assets) == 1:
                ui.Separator()
                has_collect = False
                try:
                    # pylint: disable=redefined-outer-name
                    import omni.kit.tool.collect  # noqa: F401

                    has_collect = True
                    ui.MenuItem(
                        f"{ui.get_custom_glyph_code('${glyphs}/upload.svg')}  Collect",
                        triggered_fn=(lambda asset=assets[0]: self.__collect(asset)),
                    )
                except ImportError:
                    carb.log_warn("Please enable omni.kit.tool.collect first to collect.")
                if has_collect:
                    ui.Separator()
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/show.svg')}  Open",
                    triggered_fn=(lambda asset=assets[0]: self.__open_stage(asset, load_all=True)),
                )
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/show.svg')}  Open with Payloads Disabled",
                    triggered_fn=(lambda asset=assets[0]: self.__open_stage(asset, load_all=False)),
                )
            ui.Separator()
            ui.MenuItem(
                f"{ui.get_custom_glyph_code('${glyphs}/plus.svg')}  Add at Current Selection",
                triggered_fn=(lambda assets=assets: self.__add_using_selection(assets, False)),
            )
            if len(assets) == 1:
                # If enabled for multi-selection, only the first asset would be placed at the position
                # where the selected prims were located, as these prims need to be deleted before any
                # new prims are added. Therefore, disabling this command for multi-selection.
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/plus.svg')}  Replace Current Selection",
                    triggered_fn=(lambda assets=assets: self.__add_using_selection(assets, True)),
                )
            ui.Separator()
            ui.MenuItem(
                f"{ui.get_custom_glyph_code('${glyphs}/share.svg')}  Copy URL Link",
                triggered_fn=(lambda assets=assets: self.__copy_url_link(assets)),
            )
            self.show()

    def __set_item_physics(self, assets: List[AssetDetailItem], physics: str) -> None:
        for asset in assets:
            asset.physics = physics

    def __copy_url_link(self, assets: List[AssetDetailItem]) -> None:
        try:
            import omni.kit.clipboard

            omni.kit.clipboard.copy("\n".join(asset.url for asset in assets))
        except ImportError:
            carb.log_warn("Warning: Could not import 'omni.kit.clipboard'.")

    async def __open_stage_async(self, url: str, load_all: bool):
        try:
            import omni.kit.window.file

            if load_all:
                loadset = omni.usd.UsdContextInitialLoadSet.LOAD_ALL
            else:
                loadset = omni.usd.UsdContextInitialLoadSet.LOAD_NONE
            omni.kit.window.file.open_stage(url, open_loadset=loadset)
        except ImportError:
            carb.log_warn("Warning: Could not import 'omni.kit.window.file'.")
        except Exception as e:
            carb.log_error(str(e))
        else:
            carb.log_info(f"Opened '{url}'.\n")

    def __open_stage(self, item: AssetDetailItem, load_all: bool = True) -> None:
        """
        Open a stage in the current context.
        Args:
            item (AssetDetailItem): The asset to open.
            load_all (bool): Whether to load all payloads.
        """
        asyncio.ensure_future(self.__open_stage_async(item.url, load_all))

    def __add_using_selection(self, assets: List[AssetDetailItem], replace_selection: bool) -> None:
        from .browser_api import add_asset_to_stage_using_prims, get_selected_xformable_prim_paths

        usd_context: omni.usd.UsdContext = omni.usd.get_context()
        stage: Usd.Stage = usd_context.get_stage() if usd_context else None

        prim_paths: List[Sdf.Path] = get_selected_xformable_prim_paths(usd_context, stage)
        for asset in assets:
            add_asset_to_stage_using_prims(
                usd_context,
                stage,
                asset.url,
                variants={
                    "PhysicsVariant": asset.physics if asset.physics != "None" else ""
                },  # Hardcoded to physics variant for now
                replace_prims=replace_selection,
                prim_paths=prim_paths,
            )

    def __collect(self, asset: AssetDetailItem) -> None:
        try:
            # pylint: disable=redefined-outer-name
            import omni.kit.tool.collect

            collect_instance = omni.kit.tool.collect.get_instance()
            collect_instance.collect(asset.url)
            collect_instance = None
        except ImportError:
            carb.log_warn("Failed to import collect module (omni.kit.tool.collect). Please enable it first.")
        except AttributeError:
            carb.log_warn("Require omni.kit.tool.collect v2.0.5 or later!")

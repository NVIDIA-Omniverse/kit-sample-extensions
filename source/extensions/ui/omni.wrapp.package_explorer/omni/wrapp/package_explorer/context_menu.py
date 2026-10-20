# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
from typing import List

import carb
import omni.client as omni_client
import omni.ui as ui
import omni.usd
from carb import settings
from pxr import Sdf, Usd

from .browser_model import WrappAssetDetailItem
from .style import CONTEXT_MENU_STYLE
from .utils import (
    add_asset_to_stage_using_prims,
    call_async,
    get_selected_xformable_prim_paths,
    log_warning_with_notification,
    wrapp_install,
)


class ContextMenu(ui.Menu):
    """
    Context menu for wrapp package browser.
    """

    def __init__(self):
        super().__init__("Wrapp Package Browser context menu", style=CONTEXT_MENU_STYLE)
        self._settings = settings.get_settings()

    def show_item(self, item: WrappAssetDetailItem) -> None:
        self.clear()

        from .extension import get_instance

        selection: List[WrappAssetDetailItem] = (
            get_instance().browser_widget.selection if get_instance().browser_widget else []
        )
        if not selection and not item:
            return

        items: List[WrappAssetDetailItem] = selection if selection else [item]
        with self:
            # Some right-click commands only make sense when only one asset is selected
            ui.Separator()
            if len(items) == 1:
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/show.svg')}  Open",
                    triggered_fn=(lambda asset=items[0]: self._open_stage(asset, load_all=True)),
                )
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/eye_slash.svg')}  Open with Payloads Disabled",
                    triggered_fn=(lambda asset=items[0]: self._open_stage(asset, load_all=False)),
                )
                ui.Separator()

            ui.MenuItem(
                f"{ui.get_custom_glyph_code('${glyphs}/plus.svg')}  Add at Current Selection",
                triggered_fn=(lambda items=items: self._add_using_selection(items, False)),
            )
            if len(items) == 1:
                # If enabled for multi-selection, only the first asset would be placed at the position
                # where the selected prims were located, as these prims need to be deleted before any
                # new prims are added. Therefore, disabling this command for multi-selection.
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/menu_refresh.svg')}  Replace Current Selection",
                    triggered_fn=(lambda items=items: self._add_using_selection(items, True)),
                )
            ui.Separator()
            ui.MenuItem(
                f"{ui.get_custom_glyph_code('${glyphs}/copy.svg')}  Copy URL Link",
                triggered_fn=(lambda items=items: self._copy_url_link(items)),
            )
            ui.MenuItem(
                f"{ui.get_custom_glyph_code('${glyphs}/share.svg')}  Install Latest Version",
                triggered_fn=(lambda items=items: self._update_to_latest_version(items)),
            )
            if any(item.installed for item in items):
                ui.MenuItem(
                    f"{ui.get_custom_glyph_code('${glyphs}/trash.svg')}  Uninstall",
                    triggered_fn=(lambda items=items: self._uninstall(items)),
                )
            self.show()

    def _uninstall(self, items: List[WrappAssetDetailItem]) -> None:
        """Uninstall the given items."""
        from .extension import get_instance

        async def do_uninstall():
            await asyncio.gather(*[item.uninstall() for item in items if item.installed])

        call_async(do_uninstall())

    def _update_to_latest_version(self, items: List[WrappAssetDetailItem]) -> None:
        """Update the given items to the latest version."""
        from .extension import get_instance

        async def do_update():
            for item in items:
                item.version_to_update = item.asset.versions[0]
            # Disable per-item refreshes, we will refresh the whole browser in the end.
            await asyncio.gather(*[item.update(run_on_updated=False) for item in items])

        call_async(do_update())

    def _copy_url_link(self, items: List[WrappAssetDetailItem]) -> None:
        try:
            import omni.kit.clipboard

            omni.kit.clipboard.copy("\n".join(asset.url_to_update for asset in items))
        except ImportError:
            carb.log_warn("Warning: Could not import 'omni.kit.clipboard'.")

    async def _open_stage_async(self, url: str, load_all: bool):
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

    def _open_stage(self, item: WrappAssetDetailItem, load_all: bool = True) -> None:
        """
        Open a stage in the current context.
        Args:
            item (WrappAssetDetailItem): The asset to open.
            load_all (bool): Whether to load all payloads.
        """
        asyncio.ensure_future(self._open_stage_async(item.url, load_all))

    def _add_using_selection(self, items: List[WrappAssetDetailItem], replace_selection: bool) -> None:
        usd_context: omni.usd.UsdContext = omni.usd.get_context()
        stage: Usd.Stage = usd_context.get_stage() if usd_context else None
        if not stage:
            log_warning_with_notification("No stage found, Skip adding WRAPP package to stage.")
            return

        prim_paths: List[Sdf.Path] = get_selected_xformable_prim_paths(usd_context, stage)
        for item in items:
            if stage.GetRootLayer().realPath:
                install_dir = f'{"/".join(omni_client.normalize_url(stage.GetRootLayer().realPath).split("/")[:-1])}/{item.asset.relative_destination}'
                call_async(
                    wrapp_install(
                        item.asset.name,
                        item.version_to_update,
                        install_dir,
                        wrapp_repo_url=item.asset.wrapp_repo_url,
                    ),
                    lambda *args, **kwargs: add_asset_to_stage_using_prims(
                        usd_context,
                        stage,
                        f'{install_dir}/{item.url_to_update.split("/")[-1]}',
                        replace_prims=replace_selection,
                        prim_paths=prim_paths,
                    ),
                )

            else:
                as_payload = self._settings.get("/persistent/app/stage/dragDropImport") == "payload"
                # No working area found, skipping wrapp installation. Reference/payload to the asset source directly.
                log_warning_with_notification(
                    f"No working area found, skipping wrapp installation. "
                    f"Asset {item.url_to_update} added to the current stage as {'payload' if as_payload else 'reference'}"
                )
                add_asset_to_stage_using_prims(
                    usd_context,
                    stage,
                    item.url_to_update,
                    replace_prims=replace_selection,
                    prim_paths=prim_paths,
                )

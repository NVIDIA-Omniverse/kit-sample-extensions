# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import os
from typing import List

import carb
import omni.client
import omni.client.utils as clientutils
import omni.ext
import omni.kit.app
import omni.kit.notification_manager as nm
import omni.kit.window.content_browser as content
import omni.usd
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.window.file_exporter import get_file_exporter

from .export_options_window import ExportOptionsWindow
from .exporter import Exporter


def get_instance():
    global _global_instance
    return _global_instance


class AssetExporterExtension(omni.ext.IExt):
    EXPORT_MENU_NAME = "Export"

    def on_startup(self):
        global _global_instance
        _global_instance = self

        self._context_icon_menu_items = []
        self._app = omni.kit.app.get_app()
        self._exporter = Exporter()
        self._exporter.on_startup()
        self._export_option_window = None
        self._show_file_not_supported_popup = None
        self._new_content_window = None
        self._file_menu_list = []
        self._register_menus()

    def on_shutdown(self):  # pragma: no cover
        global _global_instance
        _global_instance = None

        self._unregister_menus()
        if self._export_option_window:
            self._export_option_window.destroy()
        self._export_option_window = None
        self._exporter.on_shutdown()
        self._exporter = None
        self._show_file_not_supported_popup = None
        self._new_content_window = None

    def _unregister_menus(self):  # pragma: no cover
        # unregister actions
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension("omni.kit.tool.asset_exporter")

        if self._file_menu_list:
            omni.kit.menu.utils.remove_menu_items(self._file_menu_list, "File")
            self._file_menu_list.clear()

    def _register_menus(self):
        def _on_file_export():
            if omni.usd.get_context().get_stage() is None:
                error = "No valid stage is opened."
                carb.log_warn(error)
                nm.post_notification(error, status=nm.NotificationStatus.WARNING)

                return

            async def start_export():
                omni.kit.commands.execute("SelectAll", type="Material")
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()
                omni.kit.undo.undo()
                omni.kit.commands.execute("SelectAll", type="Shader")
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()
                omni.kit.undo.undo()
                await omni.kit.app.get_app().next_update_async()

                usd_context = omni.usd.get_context()
                stage = usd_context.get_stage()
                self._on_file_export_menu_clicked(stage)

            asyncio.ensure_future(start_export())

        # register actions
        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Asset Exporter Actions"

        # actions
        action_registry.register_action(
            "omni.kit.tool.asset_exporter",
            "file_export",
            _on_file_export,
            display_name="File Export",
            description="File Export",
            tag=actions_tag,
        )

        self._file_menu_list = [
            MenuItemDescription(
                name=self.EXPORT_MENU_NAME,
                glyph="none.svg",
                appear_after="Save Flattened As...",
                onclick_action=("omni.kit.tool.asset_exporter", "file_export"),
            )
        ]

        omni.kit.menu.utils.add_menu_items(self._file_menu_list, "File")

    def _get_current_dir_in_content_window(self):
        if not self._new_content_window:
            self._new_content_window = content.get_content_window()
        return self._new_content_window.get_current_directory()

    def _on_file_export_menu_clicked(self, stage):
        filters = [
            (".gltf", "glTF File (*.gltf)"),
            (".glb", "glb File (*.glb)"),
            (".fbx", "FBX File (*.fbx)"),
            (".obj", "OBJ File (*.obj)"),
            (".stl", "STL File (*.stl)"),
            (".usdz", "USDZ File (*.usdz)"),
        ]

        def on_export(filename: str, dirname: str, extension: str = "", selections: List[str] = []):
            path = clientutils.make_absolute_url_if_possible(dirname, filename + extension)
            self._export_file(stage, path)

        if stage.GetRootLayer().anonymous:
            filename_url = None
        else:
            filename_url = stage.GetRootLayer().identifier
            url = omni.client.break_url(filename_url)
            filename_url = omni.client.make_url(
                scheme=url.scheme, host=url.host, port=url.port, user=url.user, path=url.path, query=None
            )
            filename_url, _ = os.path.splitext(filename_url)

        file_picker = get_file_exporter()
        file_picker.show_window(
            title="Select Export Path",
            export_button_label="Export",
            export_handler=on_export,
            file_extension_types=filters,
            filename_url=filename_url,
        )

    def _export_file(self, stage, output_path):
        if not output_path:
            return

        if not self._export_option_window:
            self._export_option_window = ExportOptionsWindow(None)

        self._export_option_window.set_import_fn(
            lambda context: self._exporter.create_usd_export_task(stage, output_path, context)
        )

        usd_path = stage.GetRootLayer().identifier.replace("\\", "/")
        self._export_option_window.set_farm_export_fn(lambda: (usd_path, output_path))

        self._export_option_window.show(output_path)

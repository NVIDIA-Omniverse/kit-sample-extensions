# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import urllib.parse

import omni.log
from omni.kit.window.popup_dialog import MessageDialog

from .. import OmniUrl

__all__ = ["ConfirmDialogHelper"]


class ConfirmDialogHelper:
    """
    Helper class for ai.AbstractImporterDelegate implementations to create overriding file dialog.
    """

    def __init__(self):
        self._override_dialog = None
        self._overwrite_existing = False

    def destroy(self):
        pass

    async def _confirm_overwrite(self, export_url) -> bool:
        # reset to False
        self._overwrite_existing = False

        def _ok_handler(dialog: MessageDialog):
            self._overwrite_existing = True
            dialog.hide()

        if self._override_dialog:
            self._override_dialog.destroy()

        self._override_dialog = MessageDialog(
            title="Overwrite",
            message=f"File {export_url} already exists, do you want to overwrite it?",
            ok_handler=_ok_handler,
        )

        self._override_dialog.show()
        app = omni.kit.app.get_app()
        while self._override_dialog.window.visible:
            await app.next_update_async()

        return self._overwrite_existing

    async def confirm_write_location(
        self,
        file_path: str,
        export_folder: str,
        import_as_reference: bool,
        export_file_name: str,
        export_file_format: str,
    ):
        # handle file paths with "spaces"
        file_path = file_path.replace("%20", " ")
        file_url = OmniUrl(file_path)

        export_folder_url = OmniUrl(export_folder) if export_folder else file_url.parent_url

        if not export_file_format:
            export_file_format = ".usd"

        file_name = export_file_name if export_file_name else file_url.stem
        export_url = export_folder_url / (file_name + export_file_format)

        unquoted = urllib.parse.unquote(str(export_url))

        if export_url.exists and import_as_reference:
            if export_url.writeable:
                await self._confirm_overwrite(unquoted)
                if not self._overwrite_existing:
                    omni.log.info(f"{unquoted} overwrite declined.")
                    return False, None, None
                omni.log.warn(f"{unquoted} will be overwritten.")
            else:
                omni.log.error(f"{unquoted} is not writeable.")
                return False, None, None

        return True, str(unquoted), file_url

# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import json
from typing import Any, Dict, Tuple

import carb.settings
import omni.client as omni_client
from omni.kit.viewport.window.dragdrop.usd_file_drop_delegate import UsdFileDropDelegate
from pxr import Usd

from .consistents import WRAPP_EXPLORER_DRAG_PREFIX
from .utils import call_async, configure_prim, get_stage_dir_and_name, log_warning_with_notification, wrapp_install


class WrappDragDropObject(UsdFileDropDelegate):
    """Handles drag and drop operations for WRAPP assets in the viewport.

    Manages:
    - Asset dropping behavior
    - WRAPP installation on drop
    - Variant configuration
    """

    def __init__(self):
        self._usd_prim_droped = None
        super().__init__()

    def drop_should_disable_preview(self):
        return True

    def get_raw_data(self, drop_data: dict) -> dict:
        return json.loads(drop_data.get("mime_data")[len(WRAPP_EXPLORER_DRAG_PREFIX) :])

    def get_raw_data_string(self, raw_data: dict) -> str:
        """Convert raw data back to mime data format with prefix.

        Args:
            raw_data (dict): The raw data dictionary to be converted

        Returns:
            str: The mime data string with prefix
        """
        return WRAPP_EXPLORER_DRAG_PREFIX + json.dumps(raw_data)

    def get_url(self, drop_data: dict):
        return self.get_raw_data(drop_data)["url"]

    def add_reference_to_stage(self, usd_context, stage: Usd.Stage, url: str) -> Tuple[str, Usd.EditContext, str]:
        self._usd_prim_droped, edit_context, relative_url = super().add_reference_to_stage(usd_context, stage, url)
        return (self._usd_prim_droped, edit_context, relative_url)

    def accepted(self, drop_data: dict):
        mime_data = drop_data["mime_data"]
        self._usd_prim_droped = None
        return mime_data.startswith(WRAPP_EXPLORER_DRAG_PREFIX)

    def dropped(self, drop_data: Dict[str, Any]) -> None:
        """Handle dropping of WRAPP assets into the viewport.

        Args:
            drop_data (Dict[str, Any]): Data associated with the dropped asset
        """
        _, stage = self.get_context_and_stage(drop_data)
        if not stage:
            log_warning_with_notification("No stage found, skipping drag and drop WRAPP package.")
            return

        dropped = super().dropped

        def _on_dropped(drop_data: Dict[str, Any]):
            """Callback function for dropped asset."""
            dropped(drop_data)

            usd_prim_droped = drop_data.get("usd_prim_droped") or self._usd_prim_droped
            if usd_prim_droped:
                # Additionally, set variants if required
                variants = self.get_raw_data(drop_data).get("variants", {})
                if variants:
                    configure_prim(stage, usd_prim_droped, variants)

        source_package_url = omni_client.normalize_url(
            self.get_url(drop_data)
        )  # The full url of the wrapp package - including the usd file
        as_payload = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport") == "payload"

        if stage.GetRootLayer().realPath:
            mime_data = self.get_raw_data(drop_data)
            package_name = mime_data.get("name")
            package_version = mime_data.get("version")
            wrapp_repo_url = mime_data.get(
                "wrapp_repo_url"
            )  # The url of the wrapp repo - the folder contains .packages
            relative_destination = mime_data.get(
                "relative_destination"
            )  # The relative destination of the asset - wrapp_assets/package_name
            target_package = mime_data.get(
                "target_package"
            )  # The path to the destination package wrap file that records the asset dependencies
            install_dir = f"{get_stage_dir_and_name()[0]}/{relative_destination}"

            # Update the mime data to source the asset from the install directory
            mime_data["url"] = f'{install_dir}/{source_package_url.split("/")[-1]}'
            drop_data["mime_data"] = self.get_raw_data_string(mime_data)
            call_async(
                wrapp_install(
                    package_name,
                    package_version,
                    install_dir,
                    target_package,
                    wrapp_repo_url,
                    tags=False,
                ),
                lambda *args, **kwargs: _on_dropped(drop_data),
            )
        else:
            # No working area found, skipping wrapp installation. Reference/payload to the asset source directly.
            log_warning_with_notification(
                f"No working area found, skipping wrapp installation. "
                f"Asset {source_package_url} added to the current stage as {'payload' if as_payload else 'reference'}"
            )
            _on_dropped(drop_data)

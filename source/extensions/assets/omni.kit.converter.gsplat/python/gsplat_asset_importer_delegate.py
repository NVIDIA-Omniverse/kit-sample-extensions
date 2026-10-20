# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""
Asset Importer delegate for 3D Gaussian Splat:
constructor (name, filters, descriptions, priority), destroy(), register_importer per FILTER_DATA row.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import Dict, List, Optional, Union

import carb
import omni.kit.app
import omni.kit.tool.asset_importer as ai
import omni.ui as ui
from usd_convert_gsplat import (
    UP_AXIS_Y,
    UP_AXIS_Z,
    read_ply,
    read_spz,
    resolve_local_path,
    write_gaussian_splat_usd,
)

from .gsplat_importer_ui import MinimalModal, ProgressPopup


class _ConversionCancelled(Exception):
    """Raised from the writer progress callback when the user clicks Cancel."""


def _read_splat_file(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".spz":
        return read_spz(path)
    if ext == ".ply":
        return read_ply(path)
    raise ValueError(f"Unsupported file type '{ext}'. Expected .ply or .spz")


def _validate_file_path(file_path: str) -> Optional[str]:
    """Resolve Kit ``file:`` / percent-encoded paths so ``os.path.isfile`` and readers work."""
    resolved = resolve_local_path(file_path)
    if os.path.isfile(resolved):
        return resolved
    return None


def _export_path_resolved(
    absolute_path: str,
    output_dir: str,
    output_file_name: str,
    output_file_format: str,
) -> str:
    """
    Flat output path: ``<export_folder>/<name>.<ext>``.

    If ``export_folder`` is empty, uses the source file's directory (same folder as the .ply/.spz).
    Does not create an extra subdirectory named after the asset (unlike builtin ``create_subdir``).
    """
    od = output_dir.strip().replace("\\", "/") if output_dir else ""
    if not od:
        od = os.path.dirname(absolute_path.replace("\\", "/"))
        if not od:
            od = "."

    stem = os.path.splitext(os.path.basename(absolute_path))[0]
    ofn = output_file_name.strip() if output_file_name else stem

    fmt = (output_file_format or ".usd").strip()
    if fmt and not fmt.startswith("."):
        fmt = "." + fmt

    file_name_with_ext = ofn + fmt
    return os.path.join(od, file_name_with_ext).replace("\\", "/")


class GaussianSplatAssetImporterDelegate(ai.AbstractImporterDelegate):
    """Creates a delegate for the Gaussian Splat Asset Importer: (name, filters, descriptions, priority) per FILTER_DATA entry."""

    def __init__(self, name: str, filters: List[str], descriptions: List[str], priority: int = 0) -> None:
        super().__init__()
        self._name = name
        self._filters = filters
        self._descriptions = descriptions
        self._priority = priority
        self._rot_x = ui.SimpleFloatModel(0.0)
        self._rot_y = ui.SimpleFloatModel(0.0)
        self._rot_z = ui.SimpleFloatModel(0.0)
        # Item model for ComboBox (same pattern as BuiltinImporterOptionsBuilder + ui.ComboBox(model)).
        self._up_axis_combo_model = MinimalModal(0, ["Y", "Z"])
        self._progress_popup: Optional[ProgressPopup] = None

    def destroy(self) -> None:
        """Destroys the delegate and releases the UI models."""
        if self._progress_popup:
            try:
                self._progress_popup.hide()
                self._progress_popup.destroy()
            except Exception:
                pass
            self._progress_popup = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def filter_regexes(self) -> List[str]:
        return self._filters

    @property
    def filter_descriptions(self) -> List[str]:
        return self._descriptions

    @property
    def priority(self) -> int:
        return self._priority

    def is_supported_format(self, path: str) -> bool:
        if super().is_supported_format(path):
            return True
        cleaned = path.replace("\\", "/").split("?", 1)[0]
        ext = os.path.splitext(os.path.basename(cleaned))[1].lower()
        return ext in (".ply", ".spz")

    def supports_usd_stage_cache(self) -> bool:
        return False

    def show_scene_optimizer_config_frame(self) -> bool:
        return True

    def build_options(self, paths: List[str]) -> None:
        with ui.VStack(height=0, spacing=4):
            ui.Label("3D Gaussian Splat Importer.", height=0)
            with ui.HStack(height=24, spacing=6):
                ui.Label("Rotation (deg X, Y, Z):", width=140)
                ui.FloatField(width=60, model=self._rot_x)
                ui.FloatField(width=60, model=self._rot_y)
                ui.FloatField(width=60, model=self._rot_z)
            with ui.HStack(height=26, spacing=6):
                ui.Label("Up axis:", width=140)
                ui.ComboBox(
                    self._up_axis_combo_model,
                    width=160,
                    height=26,
                    identifier="gsplat_import_up_axis",
                )

    def _selected_up_axis(self) -> str:
        idx = self._up_axis_combo_model.current_index
        return UP_AXIS_Y if idx == 0 else UP_AXIS_Z

    async def convert_assets(self, paths: List[str], **kargs) -> Dict[str, Union[str, None]]:
        try:
            from omni.kit.asset_converter import OmniClientWrapper
        except ImportError:
            carb.log_error("[3DGS] omni.kit.asset_converter is required for import path preparation.")
            return {p: None for p in paths}

        export_folder = kargs["export_folder"] if "export_folder" in kargs else ""
        export_file_name = kargs["export_file_name"] if "export_file_name" in kargs else ""
        export_file_format = kargs["export_file_format"] if "export_file_format" in kargs else ""

        rotation = (
            self._rot_x.get_value_as_float(),
            self._rot_y.get_value_as_float(),
            self._rot_z.get_value_as_float(),
        )

        loop = asyncio.get_running_loop()
        converted: Dict[str, Union[str, None]] = {}

        # Same ProgressPopup as BuiltinImporter (title is static; status lines use ASCII "..." like builtin_importer).
        popup = ProgressPopup(
            "Converting Gaussian Splat",
            cancel_button_text="Cancel",
            status_text="Preparing...",
            modal=True,
        )
        self._progress_popup = popup
        cancel_event = threading.Event()

        def cancel_import() -> None:
            cancel_event.set()
            carb.log_info("[3DGS] Gaussian splat import cancelled by user.")

        try:
            # Let the asset importer "Convert Options" window finish closing before stacking a new modal.
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            for absolute_path in paths:
                file_path = _validate_file_path(absolute_path)
                if not file_path:
                    carb.log_warn(f"[3DGS] Invalid or missing path: {absolute_path}")
                    continue
                if not self.is_supported_format(file_path):
                    continue

                asset_export_path = _export_path_resolved(
                    file_path,
                    export_folder,
                    export_file_name,
                    export_file_format or ".usd",
                )

                parent = os.path.dirname(asset_export_path)
                if parent:
                    await OmniClientWrapper.create_folder(parent)
                if not await OmniClientWrapper.writeable_async(asset_export_path):
                    carb.log_warn(f"[3DGS] Export path is not writable: {asset_export_path}")
                    converted[absolute_path] = None
                    continue

                popup.progress = 0.0
                popup.status_text = "Preparing..."
                popup.set_cancel_fn(cancel_import)
                cancel_event.clear()
                popup.show()
                for _ in range(4):
                    await omni.kit.app.get_app().next_update_async()

                base_name = os.path.basename(file_path)
                popup.status_text = f"Reading {base_name}..."
                popup.progress = 0.05

                try:
                    splat_data = await loop.run_in_executor(None, _read_splat_file, file_path)
                except Exception as e:
                    carb.log_warn(f"[3DGS] Failed to read {file_path}: {e}")
                    converted[absolute_path] = None
                    continue

                popup.status_text = f"Converting {base_name} to USD..."

                def _write():
                    def _prog(f: float, msg: Optional[str] = None) -> None:
                        if cancel_event.is_set():
                            raise _ConversionCancelled()
                        overall = 0.12 + float(f) * 0.83
                        label = msg or "Writing USD..."

                        def _apply() -> None:
                            popup.status_text = label
                            popup.progress = overall

                        loop.call_soon_threadsafe(_apply)

                    return write_gaussian_splat_usd(
                        splat_data,
                        asset_export_path,
                        _prog,
                        file_path,
                        up_axis=self._selected_up_axis(),
                        rotation_degrees=rotation,
                    )

                try:
                    actual = await loop.run_in_executor(None, _write)
                except _ConversionCancelled:
                    converted[absolute_path] = None
                    popup.hide()
                    break
                except Exception as e:
                    carb.log_warn(f"[3DGS] Failed to convert {file_path}: {e}")
                    converted[absolute_path] = None
                    continue

                popup.status_text = f"Done - {os.path.basename(actual)}"
                popup.progress = 1.0
                converted[absolute_path] = actual
                for _ in range(2):
                    await omni.kit.app.get_app().next_update_async()
        finally:
            popup.set_cancel_fn(None)
            popup.hide()
            popup.destroy()
            self._progress_popup = None

        return converted

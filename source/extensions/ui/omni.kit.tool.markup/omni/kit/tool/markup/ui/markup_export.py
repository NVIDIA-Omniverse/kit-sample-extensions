# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# TODO: Have _sf subscribe to pref changes
# TODO: Store UI settings, like format checkbox choices, in settings (?)

import webbrowser
from contextlib import suppress
from functools import partial
from pathlib import Path

import carb
import carb.settings
import carb.tokens
import omni.ui as ui
from omni.kit.async_engine import run_coroutine
from omni.kit.markup.core import FORMAT_EXTS, SETTING_MARKUP_EXPORT_LOCAL_FOLDER, MarkupExport
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.notification_manager import NotificationStatus, post_notification
from omni.kit.window.filepicker import FilePickerDialog

PAGE_ORIENTATIONS = ("Portrait", "Landscape")
PAGE_SIZES = ("Letter", "A4")


def _notify_on_finish():
    with suppress(Exception):
        post_notification("Markup data exported.", status=NotificationStatus.INFO)


class MarkupExportWindow(ui.Window):
    _WINDOW_NAME = "Markup Export"

    def __init__(self) -> None:
        super().__init__(
            self._WINDOW_NAME,
            dockPreference=ui.DockPreference.DISABLED,
            auto_resize=True,
            resizable=True,
            padding_x=10,
            padding_y=10,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR,
        )

        self.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

        self.frame.set_build_fn(self._build_ui)

    def destroy(self) -> None:
        self.visible = False
        super().destroy()

    def _build_ui(self) -> None:
        with self.frame:
            with ui.VStack(spacing=8, height=0):
                self._pn_export = ExportPanel()


class ExportPanel:
    def __init__(self):
        self._markup_usd = get_markup_instance()
        self._export_formats = {ext: False for ext in FORMAT_EXTS}
        self._settings = carb.settings.get_settings()

        export_dir = Path(carb.tokens.get_tokens_interface().resolve("${documents}"))
        self._settings.set_default_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER, str(export_dir.resolve()))

        self._filepicker = FilePickerDialog(
            "Select Markup Export Directory",
            allow_multi_selection=False,
            apply_button_label="Select",
            click_apply_handler=lambda _f, dirname: self._on_output_dir_picked(dirname),
        )
        self._filepicker.hide()

        self._draw()

        # super().__init__("Export")

    def _on_browse_clicked(self) -> None:
        current_path = self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER)
        self._filepicker.show(current_path)

    @staticmethod
    def _is_remote_path(path: str) -> bool:
        return path.lower().startswith("omniverse:")

    def _draw(self) -> ui.Stack:
        _placeholder = "{omni.kit.tool.markup}"
        _stack = ui.VStack(spacing=6)
        with _stack:
            with ui.HStack(spacing=0):
                with ui.VStack(spacing=5):
                    ui.Spacer(height=1)
                    for x, ext in enumerate(FORMAT_EXTS):
                        with ui.HStack():
                            cb = ui.CheckBox(name=ext, identifier="FormatCheck" + ext)
                            cb.model.add_value_changed_fn(partial(self._on_format_checkbox_changed, cb.name))
                            cb.model.set_value(str(self._export_formats.get(ext)))
                            lbl = ui.Label(ext)
                            ui.Spacer(width=ui.Percent(75))
                            if ext == "HTML":
                                cb.visible = False
                                lbl.visible = False
                with ui.VStack():
                    self._lbl_pdf_options = ui.Label("PDF Export Options:")
                    self._page_size = ui.ComboBox(0, *PAGE_SIZES)
                    ui.Spacer(height=ui.Percent(5))
                    self._page_orientation = ui.RadioCollection(name="page_orientation")
                    style = {
                        "": {"background_color": 0x0, "image_url": f"${_placeholder}/data/icons/radio_off.svg"},
                        ":checked": {"image_url": f"${_placeholder}/data/icons/radio_on.svg"},
                    }
                    for orientation in PAGE_ORIENTATIONS:
                        with ui.HStack():
                            ui.RadioButton(radio_collection=self._page_orientation, width=24, height=24, style=style)
                            ui.Label(orientation)
            ui.Spacer(height=ui.Percent(10))
            with ui.HStack(height=24, spacing=4):
                self._sf_export_dir = ui.StringField(read_only=True, height=24, identifier="ExportDirField")
                self._sf_export_dir.model.set_value(self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER))
                style = {"image_url": f"${_placeholder}/data/icons/folder.svg", "margin": 0}
                ui.Button(style=style, width=24, clicked_fn=self._on_browse_clicked, identifier="BrowseButton")
            ui.Spacer(height=ui.Percent(10))
            with ui.HStack(height=24, spacing=4):
                self._btn_view_exported = ui.Button(
                    "View Exported Markups",
                    style={"margin": 0},
                    clicked_fn=self._on_view_exported_clicked,
                    enabled=not self._is_remote_path(self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER)),
                )
                ui.Spacer(width=ui.Percent(9))
                ui.Button("Export", style={"margin": 0}, clicked_fn=self._on_export_clicked, identifier="ExportButton")

        return _stack

    def _on_export_clicked(self) -> None:
        active_tool = self._settings.get_as_string("/exts/omni.kit.markup.core/editing_markup")
        if active_tool:  # pragma: no cover
            carb.log_warn("A markup is active for editing. It will not be exported.")
            post_notification(
                "The markup that is active for editing will not be included in the export.",
                status=NotificationStatus.WARNING,
            )
        if self._markup_usd:
            markup_names = self._markup_usd.get_all_markup_names()
            if not markup_names:  # pragma: no cover
                carb.log_warn("No markup data in the scene.")
                post_notification("No markup data in the scene.", status=NotificationStatus.WARNING)
                return
            if not any(self._export_formats.values()):  # pragma: no cover
                carb.log_warn("No Markup export format selected.")
                post_notification("No Markup export format selected.", status=NotificationStatus.WARNING)
                return

            pdf_page_size = self._page_size.model.get_item_value_model().as_int
            pdf_page_orientation = self._page_orientation.model.get_value_as_bool()
            markup_export = MarkupExport(self._markup_usd, self._export_formats, pdf_page_size, pdf_page_orientation)
            run_coroutine(markup_export.export(_notify_on_finish))

    def _on_format_checkbox_changed(self, *args) -> None:
        self._export_formats[args[0]] = args[1].as_bool

    def _on_output_dir_picked(self, export_directory: str) -> None:
        if export_directory.lower().startswith("bookmarks:"):  # pragma: no cover
            post_notification(
                "Cannot export markup data to the root bookmarks folder.", status=NotificationStatus.WARNING
            )
            return

        is_remote = self._is_remote_path(export_directory)
        # Path() mangles nucleus URLs on Windows (omniverse:// -> omniverse:\), so keep remote URLs raw.
        str_export_dir = export_directory if is_remote else str(Path(export_directory))
        self._settings.set(SETTING_MARKUP_EXPORT_LOCAL_FOLDER, str_export_dir)
        self._sf_export_dir.model.set_value(str_export_dir)
        self._btn_view_exported.enabled = not is_remote
        self._filepicker.hide()

    def _on_view_exported_clicked(self) -> None:  # pragma: no cover
        export_dir = self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER)
        webbrowser.open(export_dir)

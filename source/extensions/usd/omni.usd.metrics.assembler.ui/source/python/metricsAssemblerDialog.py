# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
import carb.settings
import omni.kit.commands
import omni.metrics.assembler.core.bindings._metricsAssembler as metricsAssembler
from omni import ui
from omni.ui import color as cl
from pxr import Sdf, Usd

from .metricsAssemblerManager import MetricsAssemblerManager
from .settings import MetricsAssemblerMode
from .tools import remove_anonymous_layer, resolve_layer_hierarchy, store_resolve_information


class MetricsAssemblerDialog:
    """Dialog window for handling mismatched units in USD files.

    Shows a dialog prompting the user to resolve unit mismatches between USD files,
    with options to automatically resolve in the future.
    """

    WINDOW_WIDTH: int = 500
    LINE_WIDTH: int = WINDOW_WIDTH - 40
    COMBO_WIDTH: int = LINE_WIDTH - 50
    BORDER_WIDTH: int = 10
    LINE_SPACER_HEIGHT: int = 10
    WARNING_COLOR = cl.yellow

    def __init__(
        self,
        ma_manager: MetricsAssemblerManager,
        text: str,
        stage: Usd.Stage,
        stage_id: int,
        url: str,
        check_path: Sdf.Path,
        write_layer_id: str,
        title: str = "Mismatched Units",
    ) -> None:
        """Initialize the metrics assembler dialog.

        Args:
            ma_manager: The metrics assembler manager instance
            text: Warning message to display to user
            stage: The USD stage being operated on
            stage_id: ID of the USD stage
            url: Asset URL being processed
            check_path: Path to check for unit mismatches
            write_layer_id: ID of layer to write changes to
            title: Dialog window title
        """
        self._window = ui.Window(
            title, visible=False, width=self.WINDOW_WIDTH, height=0, dockPreference=ui.DockPreference.DISABLED
        )
        self._window.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_MODAL
        )
        self._current_target = None
        self._layer_ids: list[str] = []
        self._layer_names: list[str] = []
        self._do_not_show_in_future: bool = None
        self._ma_manager = ma_manager

        def on_no() -> None:
            """Handle clicking the Cancel button."""
            self.hide()

        def on_yes() -> None:
            """Handle clicking the Resolve button."""
            if self._do_not_show_in_future is not None:
                carb.settings.get_settings().set_int(
                    metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE,
                    MetricsAssemblerMode.AUTO if self._do_not_show_in_future is True else MetricsAssemblerMode.ASK,
                )

            sdf_layer = Sdf.Layer.Find(url)
            if sdf_layer:
                omni.kit.commands.create("TransformPrimSRTCommand", path=check_path).do()
                write_layer = resolve_layer_hierarchy(stage, stage_id, check_path, write_layer_id, False)
                if write_layer and write_layer.empty:
                    remove_anonymous_layer(stage, write_layer)
                    write_layer = None
                    self._ma_manager.set_resolve_layer(None)
                store_resolve_information(stage, check_path, write_layer)
                self._ma_manager.get_metrics_assembler_change_listener().add_path(check_path, url, write_layer)
                self._current_target = None
            self.hide()

        def do_not_show_changed(model: ui.AbstractValueModel) -> None:
            """Handle changes to the "Do not show" checkbox.

            Args:
                model: The checkbox value model
            """
            self._do_not_show_in_future = model.as_bool

        def build_section(
            build_func: callable,
            spacer_width: None | int = self.BORDER_WIDTH,
            spacer_height: int = self.LINE_SPACER_HEIGHT,
        ) -> None:
            """Build a section of the dialog with consistent spacing.

            Args:
                build_func: Function that builds the section content
                spacer_width: Width of spacing around content
                spacer_height: Height of spacing after content
            """
            with ui.HStack(height=0):
                ui.Spacer(width=spacer_width) if spacer_width is not None else ui.Spacer()
                build_func()
                ui.Spacer(width=spacer_width) if spacer_width is not None else ui.Spacer()
            ui.Spacer(width=0, height=spacer_height)

        def build_warning_line(text: str) -> None:
            """Build the warning message section.

            Args:
                text: Warning message to display
            """
            build_section(
                lambda t=text: ui.Label(t, word_wrap=True, width=self.LINE_WIDTH, style={"color": self.WARNING_COLOR}),
                spacer_height=20,
            )

        def build_separator_line() -> None:
            """Build a horizontal separator line."""
            ui.Spacer(width=0, height=10)
            ui.Line(width=self.LINE_WIDTH)

        def build_do_not_show_checkbox() -> None:
            """Build the "Do not show" checkbox section."""
            tooltip = "Metrics assembler default behavior can be changed in Edit->Preferences->Metrics Assembler."
            with ui.HStack():
                ui.CheckBox(tooltip=tooltip).model.add_value_changed_fn(do_not_show_changed)
                ui.Spacer(width=5)
                ui.Label(
                    "Do not show this window in future and always resolve automatically",
                    tooltip=tooltip,
                    word_wrap=True,
                    width=self.LINE_WIDTH,
                )

        def build_buttons() -> None:
            """Build the dialog action buttons."""
            ui.Button("Resolve", width=80, height=0).set_clicked_fn(on_yes)
            ui.Button("Cancel", width=80, height=0).set_clicked_fn(on_no)

        with self._window.frame:
            with ui.VStack(height=0):
                ui.Spacer(width=0, height=10)
                build_warning_line(text)
                build_section(build_separator_line)
                build_section(build_buttons, None)
                build_section(build_do_not_show_checkbox)

    def show(self) -> None:
        """Show the dialog window."""
        self._window.visible = True

    def hide(self) -> None:
        """Hide the dialog window."""
        self._window.visible = False

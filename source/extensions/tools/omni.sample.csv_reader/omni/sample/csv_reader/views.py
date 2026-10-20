# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio

# Omniverse imports
import omni.ui as ui

# Extension modules
from .models import CSVReaderModel

# Status colors (following Omniverse extension patterns)
# These colors match the standard used across Omniverse extensions
STATUS_COLORS = {
    "ready": 0xFF3794FF,  # Blue - ready to process
    "processing": 0xFFFF9E3D,  # Orange - currently processing
    "success": 0xFF00B976,  # Green - operation completed successfully
    "warning": 0xFFFFAA00,  # Yellow - warning or validation issue
    "error": 0xFFCC0000,  # Red - error occurred
}


class CSVReaderView:
    """
    Main UI window for the CSV Reader extension.
    Provides controls for file selection, shape options, and generation with progress tracking.
    """

    def __init__(self, csvmodel: CSVReaderModel):
        # Create main window with docking preference
        self._window = ui.Window("CSV Reader", width=800, height=600, dockPreference=ui.DockPreference.RIGHT_TOP)
        self._window.visible = True
        self._csvmodel = csvmodel
        csvmodel.csv_field_model = None

        with self._window.frame:
            with ui.VStack(alignment=ui.Alignment.TOP, style={"margin": 5}):

                # File selection and visualization options section
                with ui.VStack():
                    # CSV file path selection row
                    with ui.HStack(height=20):
                        ui.Label("CSV file path:", height=10, width=120)
                        self.csv_field = ui.StringField(height=10)
                        self.csv_field.enabled = False  # Read-only display of selected file
                        self.csv_field.model.set_value(str(csvmodel.csv_file_path))
                        csvmodel.csv_field_model = self.csv_field.model
                        ui.Button("Load", width=40, clicked_fn=lambda: csvmodel.select_file())

                    # Shape selection dropdown (cube or sphere)
                    with ui.HStack(height=20):
                        ui.Label("Shape:", height=0)
                        shape_combo = ui.ComboBox(0, "cube", "sphere")
                        shape_combo.model.add_item_changed_fn(
                            lambda model, combo=shape_combo: csvmodel.shape_changed(
                                model.get_item_value_model().get_value_as_int()
                            )
                        )

                    # Cluster grouping option checkbox
                    with ui.HStack(height=20):
                        ui.Label("Group By Cluster:", height=0)
                        cluster_checkbox = ui.CheckBox(width=20)
                        cluster_checkbox.model.add_value_changed_fn(
                            lambda model: csvmodel.group_by_cluster_changed(model.get_value_as_bool())
                        )

                # Visual separator line
                ui.Line(style={"color": 0xFF00B976}, height=20)

                # Progress tracking and status display section
                with ui.VStack(height=60):
                    self.status_label = ui.Label(
                        "Ready", height=20, style={"font_size": 14, "color": STATUS_COLORS["ready"]}
                    )
                    self.progress_bar = ui.ProgressBar(height=20, style={"color": STATUS_COLORS["processing"]})
                    self.progress_bar.visible = False  # Hidden by default, shown during processing

                # Main action button section
                with ui.HStack(height=50):
                    self.generate_button = ui.Button("Generate", clicked_fn=lambda: self._on_generate())

        # Initialize CSV validation and UI state
        self._csvmodel.set_ui_callbacks(self._validate_csv_file)
        self._validate_csv_file()

    def _validate_csv_file(self):
        """Validate the current CSV file and update UI status accordingly."""
        is_valid, validation_message, row_count = self._csvmodel.validate_current_csv()

        if is_valid:
            self._set_status(f"Ready ({row_count} rows)", "ready")
            self.generate_button.enabled = True
        else:
            self._set_status(f"Warning: {validation_message}", "warning")
            self.generate_button.enabled = False

    def _set_status(self, text: str, status_type: str):
        """
        Update status label with colored text to indicate current state.

        Args:
            text: Message to display to the user
            status_type: One of: ready, processing, success, warning, error
        """
        self.status_label.text = text
        self.status_label.style = {"font_size": 14, "color": STATUS_COLORS[status_type]}

    def _on_generate(self):
        """Handle generate button click with progress tracking and UI state management."""
        # Disable UI during processing to prevent multiple concurrent operations
        self.generate_button.enabled = False
        self.progress_bar.visible = True
        self.progress_bar.model.set_value(0.0)
        self._set_status("Processing CSV...", "processing")

        # Start asynchronous generation process with callback functions
        asyncio.ensure_future(
            self._csvmodel.generate(
                progress_callback=self._on_progress_update, completion_callback=self._on_generation_complete
            )
        )

    def _on_progress_update(self, progress: float):
        """
        Update progress bar during CSV processing.

        Args:
            progress: Completion percentage as float between 0.0 and 1.0
        """
        self.progress_bar.model.set_value(progress)
        processed_percentage = int(progress * 100)
        self._set_status(f"Processing CSV... {processed_percentage}%", "processing")

    def _on_generation_complete(self, success: bool, message: str):
        """
        Handle completion of CSV processing and restore UI state.

        Args:
            success: True if generation completed successfully, False if error occurred
            message: Descriptive message about the result
        """
        # Re-enable UI controls after processing completes
        self.generate_button.enabled = True
        self.progress_bar.visible = False

        # Display appropriate status message with color coding
        if success:
            self._set_status(f"Success: {message}", "success")
        else:
            self._set_status(f"Error: {message}", "error")

    def destroy(self):
        """Clean up UI resources when extension is disabled."""
        if hasattr(self, "_window") and self._window is not None:
            self._window.destroy()
            self._window = None

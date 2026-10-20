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
import csv
import itertools
import os.path
from pathlib import Path

import carb

# Omniverse imports
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni.kit.window.file_importer import get_file_importer

# USD imports
from pxr import Gf, Sdf, UsdGeom, UsdLux

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.joinpath("data")

# Default lighting setup for CSV visualization
LIGHT_ANGLE = 0.53  # Angular size in radians for natural shadows
LIGHT_COLOR = Gf.Vec3f(1.0, 1.0, 0.745)  # Warm white color
LIGHT_INTENSITY = 5000.0  # Adequate intensity for medium scenes

# Progress update frequency - yield to UI every N rows for responsive interface
UI_UPDATE_FREQUENCY = 10

# CSV file structure expectations:
# Column 0: name (string) - identifier for the data point
# Column 1: x (float) - X coordinate in 3D space
# Column 2: y (float) - Y coordinate in 3D space
# Column 3: z (float) - Z coordinate in 3D space
# Column 4: cluster (string/int) - cluster identifier for grouping and coloring

# RGB color values for different cluster categories
# Each cluster gets assigned a color based on cluster_id % max_clusters
CLUSTER_COLORS = {
    0: [(1, 0, 0)],  # Red
    1: [(0, 1, 0)],  # Green
    2: [(0, 0.4, 0)],  # Dark Green
    3: [(0, 0, 1)],  # Blue
    4: [(0.3, 0.5, 1)],  # Light Blue
    5: [(0.5, 0.5, 0.5)],  # Gray
    6: [(0, 0, 0)],  # Black
    7: [(0, 1, 1)],  # Cyan
    8: [(0.8, 0.5, 0.25)],  # Brown
    9: [(1, 0.5, 0)],  # Orange
    10: [(1, 1, 1)],  # White
}

# Available 3D shape files for visualization
SHAPE_FILES = {
    "cube": "BasicCubeAsRef.usda",
    "sphere": "BasicSphereAsRef.usda",
}


class CSVReaderModel:
    def __init__(self):

        # USD scene structure paths
        self.root_path = "/World"  # Main container for all generated objects
        self.cluster_layer_root_path = "/Class_"  # Prefix for cluster group containers

        # UI model reference (set by view after initialization)
        self.csv_field_model = None

        # USD stage unit conversion (currently not used but available for scaling)
        self.stage_unit_per_meter = 1

        # Default CSV file path (sample file deployed with extension)
        self.csv_file_path = DATA_PATH.joinpath("CSVSample.csv")

        # 3D shape configuration
        self.shape_file_name = "BasicCubeAsRef.usda"
        self.shape_file_path = DATA_PATH.joinpath(self.shape_file_name)

        # Scale factor to ensure shapes are well-spaced in 3D scene
        # Multiplies CSV coordinates for better visualization
        self.scale_factor = 100.0

        # Processing limits for performance
        self.max_elements = 5000  # Maximum number of CSV rows to process

        # Visualization options
        self.group_by_cluster = False  # Whether to organize shapes by cluster
        self.max_num_clusters = 10  # Maximum number of different cluster colors

        # UI interaction callback
        self._validation_callback = None

    async def generate(self, progress_callback=None, completion_callback=None):
        """
        Generate 3D shapes from CSV data with progress reporting.
        Preserves existing scene content by adding shapes additively.

        Args:
            progress_callback: Function to call with progress (0.0 to 1.0)
            completion_callback: Function to call when done (success: bool, message: str)
        """
        try:
            # Get current USD stage (additive approach - preserve existing content)
            stage = omni.usd.get_context().get_stage()
            if not stage:
                if completion_callback:
                    completion_callback(False, "No stage available")
                carb.log_warn("No stage available.")
                return

            # Validate CSV file exists before processing
            if not os.path.exists(self.csv_file_path):
                if completion_callback:
                    completion_callback(False, "CSV file not found")
                carb.log_warn(f"CSV file not found: {self.csv_file_path}")
                return

            # ORIGINAL BEHAVIOR: Clear the scene before generation (commented out in v1.1.0)
            # This was the behavior in v1.0.0 - uncomment these lines to restore scene clearing
            # omni.kit.commands.execute('SelectPrims', old_selected_paths=[], new_selected_paths=[self.root_path], expand_in_stage=True)
            # omni.kit.commands.execute('DeletePrims', paths=[self.root_path])

            # Count total rows for accurate progress calculation
            total_rows = self._count_csv_rows()
            if total_rows == 0:
                if completion_callback:
                    completion_callback(False, "CSV file is empty")
                return

            # Initialize progress reporting
            if progress_callback:
                progress_callback(0.0)

            # Allow UI to update before starting heavy processing
            await omni.kit.app.get_app().next_update_async()

            # Ensure the root container prim exists in the USD stage
            root_prim = stage.GetPrimAtPath(self.root_path)
            if not root_prim.IsValid():
                UsdGeom.Xform.Define(stage, self.root_path)
                root_prim = stage.GetPrimAtPath(self.root_path)

            # Add default lighting if it doesn't already exist
            light_prim_path = self.root_path + "/DistantLight"
            if not stage.GetPrimAtPath(light_prim_path).IsValid():
                light_prim = UsdLux.DistantLight.Define(stage, light_prim_path)
                light_prim.CreateAngleAttr(LIGHT_ANGLE)
                light_prim.CreateColorAttr(LIGHT_COLOR)
                light_prim.CreateIntensityAttr(LIGHT_INTENSITY)

            # Find existing CSV-generated objects to avoid naming conflicts
            # Scans for objects with pattern 'prim_N' to determine next available number
            existing_shape_numbers = []
            for prim in stage.Traverse():
                prim_name = prim.GetName()
                if prim_name.startswith("prim_"):
                    try:
                        # Extract number from 'prim_N' pattern
                        shape_number = int(prim_name.split("_")[1])
                        existing_shape_numbers.append(shape_number)
                    except (ValueError, IndexError):
                        continue

            # Start numbering new shapes from the highest existing number + 1
            if existing_shape_numbers:
                shape_counter = max(existing_shape_numbers) + 1
            else:
                shape_counter = 1

            # Track cluster groups created during this generation to avoid duplicates
            created_cluster_paths = set()
            processed_rows = 0
            successful_rows = 0

            # Process CSV file row by row
            with open(self.csv_file_path, newline="") as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=",")

                # Skip header row and limit to max_elements for performance
                for row in itertools.islice(csv_reader, 1, self.max_elements):
                    try:
                        # Extract data from CSV row (expected format: name, x, y, z, cluster)
                        point_name = row[0]
                        x_coord = float(row[1])
                        y_coord = float(row[2])
                        z_coord = float(row[3])
                        cluster_id = row[4]

                        # Build the USD prim path for this shape:
                        # - If not clustering: shapes go directly under /World
                        # - If clustering: shapes go under /World/Class_{cluster_name}
                        cluster_prim_path = self.root_path
                        if self.group_by_cluster:
                            cluster_prim_path += self.cluster_layer_root_path + cluster_id

                        cluster_prim = stage.GetPrimAtPath(cluster_prim_path)

                        # Create cluster group container if needed and clustering is enabled
                        if not cluster_prim.IsValid() and self.group_by_cluster:
                            if cluster_prim_path not in created_cluster_paths:
                                UsdGeom.Xform.Define(stage, cluster_prim_path)
                                created_cluster_paths.add(cluster_prim_path)

                        # Create unique prim path for this shape
                        shape_prim_path = cluster_prim_path + f"/prim_{shape_counter}"
                        shape_counter += 1

                        # Create USD reference to the base shape file
                        shape_reference = stage.OverridePrim(shape_prim_path)
                        shape_reference.GetReferences().AddReference(str(self.shape_file_path), "/MyRef/RefMesh")

                        # Apply 3D transformation and visual properties
                        shape_mesh = UsdGeom.Mesh.Get(stage, shape_prim_path)

                        # Set position using scale factor for better visualization
                        shape_mesh.AddTranslateOp().Set(
                            Gf.Vec3f(
                                self.scale_factor * x_coord, self.scale_factor * y_coord, self.scale_factor * z_coord
                            )
                        )

                        # Assign color based on cluster ID (cycles through available colors)
                        cluster_color_index = int(cluster_id) % self.max_num_clusters
                        shape_mesh.GetDisplayColorAttr().Set(CLUSTER_COLORS[cluster_color_index])

                        successful_rows += 1

                    except (ValueError, IndexError) as e:
                        carb.log_warn(f"Error processing CSV row {processed_rows + 2}: {e}")
                        continue
                    finally:
                        processed_rows += 1

                        # Update progress bar with current completion percentage
                        if progress_callback and total_rows > 0:
                            max_processable_rows = min(total_rows, self.max_elements)
                            progress = min(processed_rows / max_processable_rows, 1.0)
                            progress_callback(progress)

                        # Yield to UI every N rows for responsive interface
                        if processed_rows % UI_UPDATE_FREQUENCY == 0:
                            await omni.kit.app.get_app().next_update_async()

            # Report final results
            message = f"Generated {successful_rows} shapes from CSV file"
            carb.log_info(message)

            if completion_callback:
                completion_callback(True, message)

        except Exception as e:
            error_message = f"Failed to generate shapes: {str(e)}"
            carb.log_error(error_message)
            if completion_callback:
                completion_callback(False, error_message)

    def _count_csv_rows(self) -> int:
        """Count the number of data rows in the CSV file (excluding header)."""
        try:
            with open(self.csv_file_path, newline="") as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=",")
                # Count all rows except header, but respect max_elements limit
                total_rows = sum(1 for _ in csv_reader) - 1
                return min(total_rows, self.max_elements)
        except Exception as e:
            carb.log_warn(f"Failed to count CSV rows: {e}")
            return 0

    def shape_changed(self, choice):
        """Handle UI shape selection change (cube/sphere)."""
        chosen_shape = list(SHAPE_FILES.keys())[choice]
        self.shape_file_name = SHAPE_FILES[chosen_shape]
        self.shape_file_path = DATA_PATH.joinpath(self.shape_file_name)

    def group_by_cluster_changed(self, enable_clustering):
        """Handle UI cluster grouping checkbox change."""
        self.group_by_cluster = enable_clustering

    def select_file(self):
        """Open file dialog to select a new CSV file."""
        self.file_importer = get_file_importer()
        self.file_importer.show_window(
            title="Select a CSV File",
            import_button_label="Select",
            import_handler=self._on_click_open,
            file_extension_types=[(".csv", "CSV Files (*.csv)")],
            file_filter_handler=self._on_filter_item,
            filename_url=str(self.csv_file_path),
        )

    def _on_click_open(self, filename: str, dirname: str, selections):
        """Handle file selection from the file dialog."""

        # Validate filename is not empty
        filename = filename.strip()
        if not filename:
            carb.log_warn("Filename must be provided.")
            return

        # Construct full file path
        if dirname:
            fullpath = f"{dirname}{filename}"
        else:
            fullpath = filename

        # Update model and UI with new file path
        self.csv_file_path = fullpath
        self.csv_field_model.set_value(str(fullpath))

        # Trigger validation callback to update UI status
        if self._validation_callback:
            self._validation_callback()

    def _on_filter_item(self, filename: str, filter_postfix: str, filter_ext: str) -> bool:
        """Filter files in the file dialog to show only CSV files."""
        if not filename:
            return True
        # Show only files matching the CSV extension
        _, file_extension = os.path.splitext(filename)
        return file_extension == filter_ext

    def set_ui_callbacks(self, validation_callback):
        """Set callbacks for UI updates."""
        self._validation_callback = validation_callback

    def validate_current_csv(self):
        """
        Validate the current CSV file for structure and readability.

        Returns:
            tuple: (success: bool, message: str, row_count: int)
        """
        if not os.path.exists(self.csv_file_path):
            return False, "CSV file not found", 0

        try:
            # Read and validate CSV file structure
            with open(self.csv_file_path, newline="") as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=",")
                rows = list(csv_reader)

                # Check for minimum required content (header + at least one data row)
                if len(rows) < 2:
                    return False, "CSV file is empty or has no data rows", 0

                # Validate CSV has required number of columns
                header = rows[0]
                if len(header) < 5:
                    return False, "CSV file must have at least 5 columns", 0

                # Validate sample data rows for correct format
                sample_rows = rows[1 : min(6, len(rows))]  # Check up to 5 sample rows
                for i, row in enumerate(sample_rows):
                    if len(row) < 5:
                        return False, f"Row {i+2} has insufficient columns", 0

                    try:
                        # Validate numeric columns (x, y, z coordinates)
                        float(row[1])  # x coordinate
                        float(row[2])  # y coordinate
                        float(row[3])  # z coordinate
                        str(row[4])  # cluster (can be string or number)
                    except (ValueError, IndexError):
                        return False, f"Row {i+2} has invalid data format", 0

                # Calculate processing information
                total_data_rows = len(rows) - 1
                limited_rows = min(total_data_rows, self.max_elements)

                # Generate appropriate message for user
                if limited_rows < total_data_rows:
                    message = f"Will process {limited_rows} of {total_data_rows} rows (max: {self.max_elements})"
                else:
                    message = f"{limited_rows} rows"

                return True, message, limited_rows

        except Exception as e:
            return False, f"Error reading CSV: {str(e)}", 0

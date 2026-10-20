# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""CSV Reader Extension.

Created by BB.CM.EB - June 2022
Updated to v1.1.0 - January 2025

Purpose: Read CSV files and populate the 3D environment with shapes at
         specified X, Y, Z coordinates with optional cluster grouping

Features:
 - Progress tracking with real-time updates
 - CSV file validation with immediate feedback
 - Asynchronous processing for responsive UI
 - Color-coded status indicators
 - Additive scene generation (preserves existing content)
 - Support for cube and sphere shapes
 - Optional cluster-based grouping and coloring

CSV Format Requirements:
 - Column 0: name (string) - identifier for the data point
 - Column 1: x (float) - X coordinate in 3D space
 - Column 2: y (float) - Y coordinate in 3D space
 - Column 3: z (float) - Z coordinate in 3D space
 - Column 4: cluster (string/int) - cluster identifier for grouping
"""

# Omniverse imports
import carb
import omni.ext

# Extension modules
from .models import CSVReaderModel
from .views import CSVReaderView


class CSVReaderExtension(omni.ext.IExt):
    """
    Main extension class for the CSV Reader.

    This extension provides functionality to read CSV files containing 3D coordinate
    data and generate corresponding 3D shapes in the Omniverse scene. It features
    a modern UI with progress tracking, file validation, and various visualization options.

    The extension follows the standard Omniverse extension pattern with startup and
    shutdown lifecycle methods.
    """

    def on_startup(self, ext_id):
        """
        Called when the extension is enabled.

        Initializes the data model and creates the main UI window.

        Args:
            ext_id: Unique identifier for this extension instance
        """
        carb.log_info(f"[CSV_Reader] CSVReaderExtension startup")

        # Initialize to None to ensure safe shutdown
        self._main_window = None

        # Initialize the data model that handles CSV processing and USD generation
        csv_data_model = CSVReaderModel()

        # Create the main UI window and connect it to the data model
        self._main_window = CSVReaderView(csv_data_model)

    def on_shutdown(self):
        """
        Called when the extension is disabled.

        Cleans up UI resources and ensures proper shutdown.
        """
        carb.log_info(f"[CSV_Reader] CSVReaderExtension shutdown")

        # Properly destroy the UI window and release resources
        if hasattr(self, "_main_window") and self._main_window is not None:
            self._main_window.destroy()
            self._main_window = None

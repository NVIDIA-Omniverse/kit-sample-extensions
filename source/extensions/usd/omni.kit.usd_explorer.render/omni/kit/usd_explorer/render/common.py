"""
Common utilities and constants for the USD Explorer render module.

This module provides common paths and constants used across the USD Explorer render extension.
"""

from pathlib import Path

# Path to the current module's directory
CURRENT_PATH: Path = Path(__file__).parent
# Path to the icons directory
ICON_PATH: Path = CURRENT_PATH.parent.parent.parent.joinpath("icons")

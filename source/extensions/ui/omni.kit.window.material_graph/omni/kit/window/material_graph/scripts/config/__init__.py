"""Static configuration surface for paths and UI constants.

This package provides centralized configuration for the Material Graph extension:
- Paths: module IDs, extension identifiers, and file-system paths used across
  the extension.
- Nodes: UI constants and node-type identifiers for graph rendering and catalog
  organization.

Architectural role: Configuration is a leaf dependency; no domain logic depends
on it. It centralizes magic strings and constants to avoid drift across modules.

Typical consumers: extension bootstrap, plugin registration, path resolution,
and UI layout code that needs stable identifiers and constants.
"""

from .nodes import Nodes
from .paths import Paths

__all__ = ["Nodes", "Paths"]

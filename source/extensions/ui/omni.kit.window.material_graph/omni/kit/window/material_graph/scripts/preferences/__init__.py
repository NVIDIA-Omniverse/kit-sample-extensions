"""Preferences-page package for user-configurable extension behavior.

This package exposes the preferences page implementation that binds UI controls
to persistent settings (catalog visibility, plugin options, path lists, and
related behavior toggles).

It centralizes settings UI so configuration logic stays out of graph widgets and
controllers, while still using shared settings utilities under `scripts.settings`.

Typical consumers: extension startup/shutdown registration and the preferences
window host that mounts the Material Graph settings page.
"""

from .page import MaterialGraphPreferences

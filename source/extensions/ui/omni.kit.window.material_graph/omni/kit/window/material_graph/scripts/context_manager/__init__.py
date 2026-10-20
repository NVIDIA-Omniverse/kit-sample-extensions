"""Render-context orchestration entry point.

The context manager coordinates which material/render context (for example MDL,
MaterialX, or other plugin-backed contexts) is currently active, and keeps graph
and catalog subsystems synchronized to that context.

This layer is necessary because context selection affects plugin behavior, model
visibility, catalog content, and command routing across the entire extension.

Typical consumers: context switcher/model controllers and graph widget startup
flows that bind UI state to the active render/material context.
"""

from .context_manager import ContextManager

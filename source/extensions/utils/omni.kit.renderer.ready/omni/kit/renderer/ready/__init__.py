"""
omni.kit.renderer.ready - Headless "RTX ready" log emission.

Watches for the first rendered frame via StageRenderingEventType.NEW_FRAME
and logs a timestamped "RTX ready" message. No omni.ui dependency.
"""

from .extension import RendererReadyExtension

__all__ = ["RendererReadyExtension"]

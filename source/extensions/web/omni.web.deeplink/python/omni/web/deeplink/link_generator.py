"""Module for generating deep links from the current USD scene state."""

__all__ = ["LinkGenerator"]

import omni.usd
from omni.usd import UsdContext
from pxr import Usd

from .encoder import Base64URLEncoder
from .link_builder import LinkBuilder
from .ui.notification import post_notification


class LinkGenerator:
    """Generates deep links from current scene state.

    Args:
        usd_context (UsdContext): The USD context for the scene.
        stage (Usd.Stage): The USD stage containing scene data.
    """

    def __init__(self, usd_context: UsdContext, stage):
        """Initialize with settings (portal URL, etc.)"""
        self._scene_capturer = LinkBuilder(usd_context, stage)

    def destroy(self):
        """Cleans up resources and destroys the scene capturer."""
        self._scene_capturer.destroy()

    def generate_link(self, include_camera=True, include_time=True) -> str:
        """Generate complete deep link from current scene

        Args:
            include_camera (bool): Whether to include camera state in the link.
            include_time (bool): Whether to include time state in the link.

        Returns:
            str: Complete deep link URL
        """
        return self.build_url(self.get_mandatory_data() | self.get_optional_data(include_camera, include_time))

    def get_mandatory_data(self) -> dict:
        """Capture mandatory data (app version, scene)

        Returns:
            dict: Mandatory fields dictionary
        """
        return self._scene_capturer.get_scene_info()

    def get_optional_data(self, include_camera: bool, include_time: bool) -> dict:
        """Capture optional data based on flags

        Args:
            include_camera (bool): Whether to include camera state data.
            include_time (bool): Whether to include time state data.

        Returns:
            dict: Optional fields dictionary
        """
        optional_dict = {}
        if include_camera:
            optional_dict.update(self._scene_capturer.get_camera_state())
        if include_time:
            optional_dict.update(self._scene_capturer.get_time_state())

        return optional_dict

    def build_url(self, data_dict: dict) -> str:
        """Encode data and build final URL

        Args:
            data_dict (dict): Complete data structure

        Returns:
            str: Formatted deep link URL
        """
        return Base64URLEncoder.encode(data_dict)

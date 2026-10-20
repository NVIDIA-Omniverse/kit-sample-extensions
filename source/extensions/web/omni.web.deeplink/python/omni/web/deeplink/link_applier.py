"""A module for applying deep link data to restore scene state in Omniverse."""

__all__ = ["LinkApplier"]

import asyncio
from typing import List

import carb
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.ui as ui
import omni.usd
from pxr import Gf, Tf, Usd, Vt

from .ui.notification import post_notification
from .utils.scene_utils import StageEventHandler, get_resolved_value


class LinkApplier:
    """Applies deep link data to restore scene state"""

    def __init__(self):
        """Initialize with progress UI reference"""
        self._open_stage_callbacks: List = []
        self._stage_loading_prompt = None

    async def apply_deep_link(self, link_data: dict) -> bool:
        """Main async method to process and apply deep link

        Args:
            link_data (dict): Decoded deep link data structure

        Returns:
            bool: True if deep link applied successfully, False otherwise

        Flow:
            1. Validate data structure
            2. Load scene
            3. Wait for scene load completion
            4. Apply camera settings
            5. Apply time settings
        """

        show_stage_loading_prompt = await self._register_activity_ui_addon()

        try:

            if "stage" not in link_data:
                carb.log_error("Deeplink data missing required 'stage' key")
                return False

            if not await self.load_scene(link_data["stage"], show_stage_loading_prompt):
                return False

            if "camera" in link_data:
                success = self.apply_camera_state(link_data["camera"])
                if not success:
                    return False

            if "time" in link_data:
                success = self.apply_time_state(link_data["time"])
                if not success:
                    return False
        finally:
            # NOTE: finally always gets processed even if an exception is raised or function returns
            self._remove_activity_ui_addon()

        # show notification
        post_notification(f"Deep link applied", info=True)

        return True

    async def load_scene(self, scene_path: str, show_stage_loading_prompt: bool):
        """Load scene file asynchronously

        Args:
            scene_path (str): Path to USD scene file

        Returns:
            bool: True if scene loaded successfully, False otherwise
        """
        import omni.kit.app

        # if stage is unsaved, abort and prompt user to save the stage
        if (
            not carb.settings.get_settings().get_as_bool("/exts/omni.web.deeplink/ignore_dirty_state")
            and omni.usd.get_context().has_pending_edit()
        ):
            post_notification(
                f"Stage is unsaved. Please save the stage before loading a deep link.", info=False, duration=10
            )
            return False

        # show notification
        if not show_stage_loading_prompt:
            post_notification(f"Loading scene: {scene_path}", info=True)
        # pause so the notification is visible
        for i in range(50):
            await omni.kit.app.get_app().next_update_async()

        # load stage and wait for assets to load
        stage_event_handler = StageEventHandler("omni.web.deeplink")
        await stage_event_handler.reset_stage_event(omni.usd.StageEventType.OPENED)
        success, error = await omni.usd.get_context().open_stage_async(scene_path)
        if not success:
            post_notification(f"Failed to load scene: {error}", info=False, duration=10)
            stage_event_handler.destroy()
            await omni.usd.get_context().new_stage_async()
            try:
                import omni.kit.window.file

                omni.kit.window.file.new()
            except ModuleNotFoundError:
                pass
            return False

        # wait for assets to load
        await stage_event_handler.wait_for_stage_event()

        stage_event_handler.destroy()
        stage_event_handler = None
        return True

    def apply_camera_state(self, camera_data: dict):
        """Apply camera transformation and settings

        Args:
            camera_data (dict): Camera configuration data including prim path and attributes

        Returns:
            bool: True if camera state applied successfully, False otherwise
        """
        import omni.usd

        camera_prim = None
        for key, value in camera_data.items():
            stage = omni.usd.get_context().get_stage()
            if key == "camera":
                camera_prim = stage.GetPrimAtPath(value)

                if not camera_prim:
                    carb.log_error(f"Failed to get camera prim at path: {value}")
                    return False

                try:
                    import omni.kit.viewport.utility

                    viewport_window = omni.kit.viewport.utility.get_active_viewport_window()
                    if viewport_window:
                        viewport_api = viewport_window.viewport_api
                        with omni.kit.undo.disabled():
                            omni.kit.commands.execute(
                                "SetViewportCameraCommand", camera_path=value, viewport_api=viewport_api
                            )
                except Exception as e:
                    carb.log_error(f"Failed to switch viewport bound camera to {value}: {e}")
                    continue

        with omni.kit.undo.disabled():
            for key, value in camera_data.items():
                if key == "camera":
                    continue

                if not camera_prim:
                    carb.log_error(f"Camera prim must be set before applying attributes")
                    continue

                resolved_value = get_resolved_value(value)
                if resolved_value is None:
                    carb.log_error(f"get_resolved_value() failed to resolve value: {value} for key: {key}")
                    continue

                try:
                    cam_attr = camera_prim.GetAttribute(key)
                    omni.kit.commands.execute(
                        "ChangeProperty",
                        prop_path=cam_attr.GetPath(),
                        value=resolved_value,
                        prev=cam_attr.Get(),
                    )
                except Tf.ErrorException as e:
                    carb.log_error(f"Failed to set attribute {key} to {resolved_value}: {e}")
                    continue

        return True

    def apply_time_state(self, time_data: dict):
        """Set time sample and FPS

        Args:
            time_data (dict): Time configuration data including current time

        Returns:
            bool: True if time state applied successfully, False otherwise
        """
        try:
            import omni.timeline

            timeline = omni.timeline.get_timeline_interface()
            timeline.set_current_time(float(time_data["current_time"]))
        except ModuleNotFoundError:
            post_notification(f"Failed to apply time state: omni.timeline module not found", info=False, duration=10)
            return False

        return True

    # register omni.activity.ui addon to open stage when the prompt is shown
    async def _register_activity_ui_addon(self) -> bool:
        """Auto-register omni.activity.ui's open stage addon if available.

        Returns:
            bool: True if activity ui addon registered successfully, False otherwise
        """
        # Only register once
        if self._open_stage_callbacks:
            return True

        try:
            import omni.activity.ui
            from omni.kit.widget.prompt import PromptManager

            self._open_stage_callbacks.append(omni.activity.ui.get_open_file_addon_callback())
            carb.log_info("omni.web.deeplink: Auto-registered omni.activity.ui open stage addon")

            # Waits 2 updates to make sure modal dialog is centered. This is issue from omni.ui that
            # shows a modal dialog when the last modal dialog is shown will not be positioned correctly.
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            self._stage_loading_prompt = PromptManager.post_simple_prompt(
                "Please Wait",
                f"Applying deep link...",
                None,
                shortcut_keys=False,
                width=500,
                callback_addons=self._open_stage_callbacks,
            )

            # Waits 2 updates to make sure it's shown.
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            return True
        except (ImportError, AttributeError) as e:
            carb.log_info(f"omni.web.deeplink: Could not register omni.activity.ui addon: {e}")

        return False

    # remove omni.activity.ui addon to open stage when the prompt is shown
    def _remove_activity_ui_addon(self):
        """Remove omni.activity.ui's open stage addon if available."""

        if self._stage_loading_prompt:
            self._stage_loading_prompt.destroy()
            self._stage_loading_prompt = None

        if self._open_stage_callbacks:
            self._open_stage_callbacks = []
            carb.log_info("omni.web.deeplink: Removed omni.activity.ui open stage addon")

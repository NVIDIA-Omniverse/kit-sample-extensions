__all__ = ["CloudOpenExtension", "get_session_status", "open_stage_async", "get_endpoint_performance"]

import asyncio
import os
import time

import carb
import omni.client
import omni.ext
import omni.kit.window.content_browser
import omni.services.core
import omni.usd
from omni.kit.viewport.utility import get_active_viewport_window, post_viewport_message

settings_interface = carb.settings.get_settings()

session_status = {"scene_status": "unknown"}
nucleu_path_to_popup = None


def get_session_status() -> dict:
    """Get the current session status."""
    global session_status
    return session_status


async def get_endpoint_performance():
    """
    Get the current performance of the viewport.
    """

    viewport_window = get_active_viewport_window()
    if not viewport_window:
        return {}

    frame_info = viewport_window.viewport_api.frame_info
    multiplier = frame_info.get("subframe_count", 1)
    fps = viewport_window.viewport_api.fps * multiplier

    result = {
        "scene_name": session_status.get("scene_name", ""),
        "scene_status": session_status.get("scene_status", ""),
        "scene_load_time": session_status.get("scene_load_time", 0),
        "fps": fps,
        "viewport_width": viewport_window.viewport_api.resolution[0],
        "viewport_height": viewport_window.viewport_api.resolution[1],
    }
    return result


async def open_stage_async(path: str):
    """
    Open a USD stage asynchronously.
    """

    def _is_usd_filetype(path):
        return ".usd" in path or ".usda" in path or ".usdc" in path

    def _popup_nucleus_folder(nucleu_path=None):
        global nucleu_path_to_popup
        if nucleu_path:
            nucleu_path_to_popup = nucleu_path
        # vincentz: populate again since the first call might fail
        carb.log_info(f"Popup '{nucleu_path_to_popup}'")
        if nucleu_path_to_popup:
            omni.kit.window.content_browser.get_content_window().navigate_to(nucleu_path_to_popup)

    broken_url = omni.client.break_url(path)
    server_only_path = omni.client.make_url(scheme=broken_url.scheme, host=broken_url.host, port=broken_url.port)

    try:
        result, server_info = await omni.client.get_server_info_async(server_only_path)
        if result == omni.client.Result.OK:
            logged_user_name = server_info.username
            logged_user_id = server_info.connection_id
            if logged_user_name.endswith("@nvidia.com"):
                settings_interface.set_bool("/crashreporter/devOnlyOverridePrivacyAndForceUpload", True)
    except Exception as e:
        pass

    omni.client.add_bookmark(broken_url.host, server_only_path)

    result, _ = await omni.client.stat_async(path)
    if result != omni.client.Result.OK or not _is_usd_filetype(path):
        global session_status
        session_status["scene_status"] = "open_failed"

        carb.log_warn(f"'{path}' is not a valid USD file.")

        # populate nucleus connection even if the USD path is invalid
        _popup_nucleus_folder(server_only_path)
        omni.client.remove_bookmark("localhost")
        return

    try:
        # hide welcome window
        import omni.kit.usd_presenter.window.welcome as welcome

        welcome.get_instance().show_window(False)
    except Exception as e:
        pass

    carb.log_info(f"stat_async: result is OK '{path}'.")

    _popup_nucleus_folder(path)
    omni.client.remove_bookmark("localhost")

    # <open_stage> will hang Kit when clicking OK on Siemens factory scene, while <open_stage_with_callback> won't
    # omni.usd.get_context().open_stage(path)
    omni.usd.get_context().open_stage_with_callback(path, None)


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class CloudOpenExtension(omni.ext.IExt):

    def on_startup(self, ext_id):
        # https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/docs/omni.log/Logging.html#logging-settings-reference

        settings_interface.set("exts/omni.kit.usd_presenter.window.welcome/docsURL", "")
        # settings_interface.set("/app/extensions/excluded/0", "omni.kit.window.status_bar")

        self.on_stage_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop(self._on_stage_event, name="bench event")
        )

        omni.services.core.main.register_endpoint("get", "/perf", get_endpoint_performance)

        USD_PATH = os.environ.get("USD_PATH", "")
        if USD_PATH:
            asyncio.ensure_future(open_stage_async(USD_PATH))

    def on_shutdown(self):
        self.on_stage_sub = None

    def _on_stage_event(self, e: carb.events.IEvent):
        global session_status
        event = omni.usd.StageEventType(e.type)
        payload: dict = e.payload
        carb.log_info(f"Stage Event: {event} {payload}")
        if event == omni.usd.StageEventType.OPENING:
            session_status["usd_opening"] = time.time()
            session_status["scene_status"] = "opening"
            session_status["scene_name"] = payload.get("val", "")
            if not session_status["scene_name"]:
                session_status["scene_status"] = "open_failed"
            omni.client.remove_bookmark("localhost")

        elif event == omni.usd.StageEventType.ASSETS_LOADED:
            if session_status["scene_status"] == "opening":
                session_status["usd_assets_loaded"] = time.time()
                session_status["scene_load_time"] = session_status["usd_assets_loaded"] - session_status["usd_opening"]
                session_status["scene_status"] = "loaded"
                omni.client.remove_bookmark("localhost")
        elif event == omni.usd.StageEventType.OPEN_FAILED:
            session_status["scene_status"] = "open_failed"

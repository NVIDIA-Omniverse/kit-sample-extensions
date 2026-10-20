import asyncio
import os
from datetime import datetime
from typing import Callable

import carb
import carb.settings
from omni.kit.viewport.utility import get_active_viewport

SETTING_PERSISTENT = "/persistent"


def capture_regular(on_capture_done_fn: Callable, check_output: bool = True):
    settings = carb.settings.get_settings()
    # screenshot
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d %H.%M.%S")
    capture_filename = "Screenshot %s.png" % (date_time)
    # Check if the user specified the screenshots folder.
    screenshot_path = settings.get("/persistent/app/captureFrame/path")
    if screenshot_path:
        if not os.path.exists(screenshot_path):
            os.makedirs(screenshot_path)
        if os.path.isdir(screenshot_path):
            capture_filename = os.path.join(screenshot_path, capture_filename)
        else:  # pragma: no cover
            carb.log_error(f"Can't save screenshot to {str(screenshot_path)} because it is not a directory")
            return

    async def capture_frame(capture_filename: str, on_capture_done):
        # wait for next frame so menu has closed
        import omni.kit.app

        await omni.kit.app.get_app().next_update_async()

        capture_viewport = settings.get(SETTING_PERSISTENT + "/app/captureFrame/viewport")
        success = False
        try:
            if not capture_viewport:
                import omni.kit.renderer.capture

                renderer_capture = omni.kit.renderer.capture.acquire_renderer_capture_interface()
                renderer_capture.capture_next_frame_swapchain(capture_filename)
                await omni.kit.app.get_app().next_update_async()
                renderer_capture.wait_async_capture()
                for i in range(4):
                    await omni.kit.app.get_app().next_update_async()
                success = True
            else:
                from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport

                viewport = get_active_viewport()
                if viewport:
                    capture = capture_viewport_to_file(viewport, file_path=capture_filename, is_hdr=False)
                    await omni.kit.app.get_app().next_update_async()
                    success = await capture.wait_for_result()
                    if success:
                        while check_output:
                            result, _ = omni.client.stat(capture_filename)
                            if result == omni.client.Result.OK:
                                break
                            else:
                                await omni.kit.app.get_app().next_update_async()

        except ImportError:  # pragma: no cover
            pass

        if success:
            on_capture_done(capture_filename)
        else:  # pragma: no cover
            carb.log_error("Failed to capture " + ("viewport" if capture_viewport else "") + "screenshot")
            on_capture_done(None)

    # wait for next frame so menu has closed
    asyncio.ensure_future(capture_frame(capture_filename, on_capture_done_fn))

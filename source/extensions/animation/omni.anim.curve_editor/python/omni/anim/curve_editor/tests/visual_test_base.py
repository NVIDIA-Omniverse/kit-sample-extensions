import inspect
import os
import pathlib
import sys
import traceback
from datetime import time
from functools import lru_cache
from pathlib import Path

import carb
import carb.settings
import carb.tokens
import carb.windowing
import omni.appwindow
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.timeline import get_timeline_interface

OUTPUTS_DIR = Path(omni.kit.test.get_test_output_path())

settings = carb.settings.get_settings()


@lru_cache()
def _get_windowing() -> carb.windowing.IWindowing:
    try:
        return carb.windowing.acquire_windowing_interface()
    except RuntimeError:
        # OVC: RuntimeError: Failed to acquire interface: card::windowing::IWindowing
        return None


class CompareError(Exception):
    pass


def compare(
    image1, image2, image_diffmap, threshold, compare_op, crop_x1=None, crop_y1=None, crop_x2=None, crop_y2=None
):
    """
    crop_xx: leave None if you do not want to crop images.
    """
    if not image1.exists():
        raise CompareError(f"File image1 {image1} does not exist")
    if not image2.exists():
        raise CompareError(f"File image2 {image2} does not exist")

    if "PIL" not in sys.modules.keys():
        try:
            from PIL import Image
        except ImportError:
            import omni.kit.pipapi

            omni.kit.pipapi.install("Pillow", module="PIL")

    from PIL import Image, ImageChops, ImageStat

    original = Image.open(str(image1))
    contrast = Image.open(str(image2))

    if original.size != contrast.size:
        raise CompareError(
            f"[omni.ui.test] Can't compare different resolutions\n\n"
            f"{image1} {original.size[0]}x{original.size[1]}\n"
            f"{image2} {contrast.size[0]}x{contrast.size[1]}\n\n"
            f"It's possible that your monitor DPI is not 100%.\n\n"
        )

    if any((crop_x1, crop_x2, crop_y1, crop_y2)):
        # we will crop the images
        w, h = original.size  # original and contrast are of the same size
        if crop_x1 is None:
            crop_x1 = 0
        if crop_x2 is None:
            crop_x2 = w
        if crop_y1 is None:
            crop_y1 = 0
        if crop_y2 is None:
            crop_y2 = h
        # (left, top, right, bottom)
        original = original.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        contrast = contrast.crop((crop_x1, crop_y1, crop_x2, crop_y2))

    difference = ImageChops.difference(original, contrast).convert("RGB")
    stat = ImageStat.Stat(difference)
    diff_ratio = sum(stat.mean) / (len(stat.mean) * 255)

    difference = difference.point(lambda i: min(i * 255, 255))
    difference.save(str(image_diffmap))
    return diff_ratio


async def capture(image_name, publish=True):
    image1 = OUTPUTS_DIR.joinpath(image_name)
    import omni.kit.renderer_capture

    omni.kit.renderer_capture.acquire_renderer_capture_interface().capture_next_frame_swapchain(str(image1))
    await omni.kit.app.get_app().next_update_async()
    omni.kit.renderer_capture.acquire_renderer_capture_interface().wait_async_capture()
    await omni.kit.app.get_app().next_update_async()

    if publish:
        print(f"##teamcity[publishArtifacts '{image1} => results']")
        print(f"##teamcity[testMetadata type='image' value='results/{image_name}']")


"""
    Animation(or simulation) extensions' workflow is usually like
    1. Load USD asset
    2. Advance the time
    3. Do animation/simulation
    4. Render the result to the viewport
    5. Or update the value to the UI window, e.g. Property window

    Animation Authoring extensions' workflow is usually like
    1. Load USD asset
    2. User interface manipulation, e.g. mouse/keyboard
    3. Render the result to the viewport or a separate UI window

    Both needs a way to unit test the correctness of the workflow
    The AnimationVisualTestBase class is designed to solve the problem.
    It now offers APIs simulate most of these workflows(except mouse/keyboard)
    and capture the screenshot and do the image difference
"""


class AnimationVisualTestBase(omni.kit.test.AsyncTestCase):
    """
    Public APIs for other extensions to inherit or use
    """

    """
        Overall unit test startup API. Most important part is to set:
            1. _GOLDEN_IMG_DIR
            2. _MAP_DIR
    """

    async def setUp(self):
        self._app = omni.kit.app.get_app()
        self._context = omni.usd.get_context()
        self._timeline = omni.timeline.acquire_timeline_interface()
        self._GOLDEN_IMG_DIR = None  # Child class should override this dir path
        self._MAP_DIR = None  # Child class should override this dir path

    """
        Overall unit test closing API. Inherit it and add your own stuff
    """

    async def tearDown(self):
        pass

    """
        Restore to the original state before executing the unit test
        1. restore the windows layout
        2. restore the rendering and other settings
        Usually users don't have to call this explicitly, it is invoked in the do_visual_test
    """

    async def restore(self, profile=False):
        await self._restore_windows()
        await self._restore_settings(profile)

    """
        Useful helper function to do the viewport visual test: render your test
        1. Setup a new window to render the scene
        2. Also setup the necessary rendering settings and viewport settings so that rendering result is consistent
        3. Users only have to input windows resolution info or leave the default resolution.
    """

    async def setup_viewport_test(self, width=800, height=600, profile=False):
        await self._setup_base_settings()
        await self._setup_viewport_settings(profile)
        await self._setup_render_settings()
        await self._setup_window(width, height)

    """
        Useful helper function to do the UI window visual test, e.g. property window, customized tool window
        Undock the UI window and set the main window to be the same size as the UI window for window capturing
        @param
            docked_window:  the UI window to test against, e.g. property window
            restore_window: The window for restoring after the test is done
            restore_position:   work together with restore_window for restoring after the test is done
            width:          UI windows width
            height:         UI windows height
        @example
            docked_window:  ui.WorkSpace.get_window("Curve Editor")
            restore_window: ui.WorkSpace.get_window("Content")  Curve Editor docks beside Content window
            restore_position:  ui.DockPosition.SAME   Curve editor docks the same place as the Content window

    """

    async def setup_docked_test(
        self,
        docked_window,
        restore_window,
        restore_position=ui.DockPosition.SAME,
        width=800,
        height=600,
        curve_editor_special_flags=False,
    ):
        # window = ui.Workspace.get_window(window_name)
        # restore_window = ui.Workspace.get_window(window_restore)
        await self._setup_base_settings()
        await self._setup_docked(
            docked_window, restore_window, width, height, restore_position, curve_editor_special_flags
        )

    """
        A utility to load the USD map
        @param
            map_name:   USD map name. Don't offer full path here
        @example
            map_name = test.usd  is a map under the self._MAP_DIR folder

    """

    async def load_stage(self, map_name):
        map_path = os.path.join(self._MAP_DIR, map_name)
        result = None
        (result, err) = await self._context.open_stage_async(map_path, omni.usd.UsdContextInitialLoadSet.LOAD_ALL)
        self.assertTrue(result)
        await wait_stage_loading()
        await self.set_time_in_seconds(0)  # always reset time to 0 upon start
        await omni.kit.app.get_app().next_update_async()
        return result

    """
        A utility to advanced time in frame
        @param
            nun_frame:   number of frames to advance
        @example
            set_time_in_frame(50)  set the time to 50th frame

    """

    async def set_time_in_frame(self, nun_frame: int):
        timeline_iface = get_timeline_interface()
        timeline_iface.play()
        timeline_iface.set_auto_update(False)
        for i in range(nun_frame):
            timeline_iface.forward_one_frame()
        timeline_iface.pause()  # we should return to the default state, stop, instead of play
        await omni.kit.app.get_app().next_update_async()

    """
        A utility to advanced time in seconds
        @param
            seconds:   set the time to seconds
        @example
            set_time_in_seconds(5.0)  set the time to 5.0 seconds

    """

    async def set_time_in_seconds(self, seconds: float):
        timeline_iface = get_timeline_interface()
        timeline_iface.play()
        timeline_iface.set_auto_update(False)
        timeline_iface.set_current_time(seconds)
        timeline_iface.pause()  # we should return to the default state, stop, instead of play
        await omni.kit.app.get_app().next_update_async()

    """
        A utility to get image name on how the screenshot is stored.
        @param
            img_name:   image name
            img_suffix: image suffix
        @example
            if img_name is None, it is test case name, else it is the specified name

    """

    def get_img_name(self, img_name, img_suffix):
        return f"{img_name if img_name is not None else inspect.stack()[2][3]}{img_suffix}.png"

    """
        A must called function to kickoff the visual test and comparison. Also do the restore
        @param
            threshold:   a threshold for comparison
            inverse:     by default comparison is less than. inverse means comparison is greater than
            img_name:    specify the image name
            img_suffix:  suffix in the image name
            golden_img_name: name of the golden image to compare against, when it differs from img_name. Use it when
                         two tests share one golden image, so that each still captures under its own img_name and
                         they don't overwrite each other's capture/diffmap artifacts on failure.
            skip_assert: whether to skip the assertion of not
            restore:     whether to run self.resotre() before returning. Default is True. Could be useful when you want
                         to continously capturing images
            reset_mouse: whether to reset mouse to (0, 0) before capturing. Default is True.
    """

    async def do_visual_test(
        self,
        threshold=1e-4,
        inverse=False,
        img_name=None,
        img_suffix="",
        golden_img_name=None,
        skip_assert=False,
        restore=True,
        reset_mouse=True,
    ):
        def compare_ge(a, b):
            return a >= b

        def compare_le(a, b):
            return a <= b

        compare_op = compare_le if inverse else compare_ge

        if reset_mouse:
            await ui_test.emulate_mouse_move(ui_test.Vec2(0, 0))
            await ui_test.human_delay()

        await self._setup_render_settings()
        image_file_name = self.get_img_name(img_name, img_suffix)
        # keep the None default out of get_img_name(): it falls back to inspect.stack() at a fixed depth.
        golden_file_name = self.get_img_name(golden_img_name, img_suffix) if golden_img_name else image_file_name
        diff = await self.capture_and_compare(image_file_name, threshold, compare_op, golden_file_name)
        op_str = ">" if inverse else "<"
        message = f"result: difference ratio {diff} {op_str} {threshold} threshold"
        carb.log_warn(message) if compare_op(diff, threshold) else print(message)

        if restore:
            await self.restore()

        res = diff is not None and not compare_op(diff, threshold)
        if not skip_assert:
            self.assertTrue(res, f"The image {image_file_name} doesn't match the golden one")
        return res

    async def capture_and_compare_test(
        self, threshold=1e-4, inverse=False, img_name=None, img_suffix="", skip_assert=False
    ):
        def compare_ge(a, b):
            return a >= b

        def compare_le(a, b):
            return a <= b

        compare_op = compare_le if inverse else compare_ge

        diff = await self.capture_and_compare(self.get_img_name(img_name, img_suffix), threshold, compare_op)

        res = diff is not None and not compare_op(diff, threshold)
        if not skip_assert and not res:
            carb.log_error(f"Test Faile: output image {img_name} doesn't match the golden one , max diff = {diff}")
        return res

    """
        Private functions
    """

    def __init__(self, tests=()):
        super().__init__(tests)
        self._saved_width = None
        self._saved_height = None
        self._restore_window = None
        self._restore_position = None
        self._restore_dock_window = None
        self._layout_dump = None

        self._base_settings = [
            ("/app/window/scaleToMonitor", False, True),
            ("/app/window/dpiScaleOverride", 1.0, -1.0),
        ]

        self._viewport_settings = [
            ("/app/window/hideUi", True, False),
            ("/app/viewport/forceHideFps", True, False),
            ("/persistent/app/viewport/displayOptions", 0, 0),
            # ("/app/runLoops/main/rateLimitFrequency", 60, 60),
            # ("/persistent/simulation/minFrameRate", 60, 60),
            ("/app/viewport/grid/enabled", False, True),
            ("/app/docks/disabled", True, False),
            ("/app/asyncRendering", False, True),
            ("/app/hydraEngine/waitIdle", True, False),
            ("/app/renderer/waitIdle", True, False),
            ("/renderer/multiGpu/autoEnable", False, True),
            ("/rtx/materialDb/syncLoads", True, False),
            ("/omni.kit.plugin/syncUsdLoads", True, False),
            ("/rtx/hydra/materialSyncLoads", True, False),
            ("/exts/omni.usd/updatePriority", 1, 0),
        ]

        self._viewport_profile_settings = [
            ("/app/window/hideUi", True, False),
            ("/app/viewport/forceHideFps", False, False),
            ("/persistent/app/viewport/displayOptions", 0, 0),
            # ("/app/runLoops/main/rateLimitFrequency", 60, 60),
            # ("/persistent/simulation/minFrameRate", 60, 60),
            ("/app/viewport/grid/enabled", False, True),
            ("/app/docks/disabled", True, False),
            ("/app/asyncRendering", True, True),
            ("/app/hydraEngine/waitIdle", True, False),
            ("/app/renderer/waitIdle", True, False),
            ("/renderer/multiGpu/autoEnable", False, True),
            ("/rtx/materialDb/syncLoads", True, False),
            ("/omni.kit.plugin/syncUsdLoads", True, False),
            ("/rtx/hydra/materialSyncLoads", True, False),
            ("/exts/omni.usd/updatePriority", 1, 0),
        ]

        self._render_settings = [
            ("/app/captureFrame/setAlphaTo1", True, False),
            ("/rtx/post/aa/op", 0, 0),
            ("/rtx/shadows/enabled", False, True),
            ("/rtx/reflections/enabled", False, True),
            ("/rtx/ambientOcclusion/enabled", False, True),
            ("/rtx/post/tonemap/op", 1, 6),
            ("/rtx/pathtracing/lightcache/cached/enabled", False, True),
            ("/rtx/raytracing/lightcache/spatialCache/enabled", False, True),
            ("/rtx/materialDb/syncLoads", True, True),
            ("/omni.kit.plugin/syncUsdLoads", True, True),
            ("/rtx/hydra/materialSyncLoads", True, True),
            ("/renderer/multiGpu/autoEnable", False, True),
        ]

        self._settings_cache = {}
        self._crop_config = (None, None, None, None)

    def _setup_settings(self, settings_list):
        for name, value, _ in settings_list:
            self._settings_cache[name] = settings.get(name)
            settings.set(name, value)

    async def _setup_base_settings(self):
        self._setup_settings(self._base_settings)
        await omni.kit.app.get_app().next_update_async()

    async def _setup_viewport_settings(self, profile=False):
        self._layout_dump = ui.Workspace.dump_workspace()
        if profile:
            self._setup_settings(self._viewport_profile_settings)
        else:
            self._setup_settings(self._viewport_settings)
        await omni.kit.app.get_app().next_update_async()

        # force fake viewport with hidden ui forward when in physics test runner
        viewport_hideui = ui.Workspace.get_window("Viewport##HideUi")
        if viewport_hideui:
            viewport_hideui.visible = True

    async def _setup_render_settings(self):
        self._setup_settings(self._render_settings)
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

    async def _restore_settings(self, profile=False):
        if len(self._settings_cache) == 0:
            return

        def restore(settings_list):
            for name, _, default in settings_list:
                try:
                    cache = self._settings_cache[name]
                    settings.set(name, cache if cache is not None else default)
                except KeyError:
                    pass

        restore(self._base_settings)
        if profile:
            restore(self._viewport_profile_settings)
        else:
            restore(self._viewport_settings)
        restore(self._render_settings)

        if self._layout_dump is not None:
            ui.Workspace.restore_workspace(self._layout_dump)

        self._settings_cache.clear()
        await omni.kit.app.get_app().next_update_async()

    async def _setup_window(self, width, height):
        app_window = omni.appwindow.get_default_app_window()
        dpi_scale = ui.Workspace.get_dpi_scale()

        width_with_dpi = int(width * dpi_scale)
        height_with_dpi = int(height * dpi_scale)

        current_width = app_window.get_width()
        current_height = app_window.get_height()

        if width_with_dpi == current_width and height_with_dpi == current_height:
            self._saved_width = None
            self._saved_height = None
        else:
            self._saved_width = current_width
            self._saved_height = current_height
            app_window.resize(width_with_dpi, height_with_dpi)
            await omni.appwindow.get_default_app_window().get_window_resize_event_stream().next_event()

        # Move the cursor away to avoid hovering on element and trigger tooltips that break the tests
        windowing = _get_windowing()
        os_window = app_window.get_window()
        if windowing:
            windowing.set_cursor_position(os_window, (0, 0))

        self._restore_window = None
        self._restore_position = None
        self._restore_dock_window = None

    async def _setup_docked(
        self,
        window,
        restore_window=None,
        width=800,
        height=600,
        restore_position=ui.DockPosition.SAME,
        curve_editor_special_flags=False,
    ):
        window.undock()
        await omni.kit.app.get_app().next_update_async()
        window.focus()

        # This is a hack for allowing scrolling DOWN in Curve Editor
        if curve_editor_special_flags:
            window.flags = (
                ui.WINDOW_FLAGS_NO_SCROLL_WITH_MOUSE
                | ui.WINDOW_FLAGS_NO_SCROLLBAR
                | ui.WINDOW_FLAGS_NO_TITLE_BAR
                | ui.WINDOW_FLAGS_NO_RESIZE
            )
        else:
            window.flags = ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_NO_TITLE_BAR | ui.WINDOW_FLAGS_NO_RESIZE
        window.width = width
        window.height = height
        window.position_x = 0
        window.position_y = 0

        await self._setup_window(width, height)

        self._restore_dock_window = window
        self._restore_window = restore_window
        self._restore_position = restore_position

    async def _restore_windows(self):
        if self._saved_width is not None and self._saved_height is not None:
            app_window = omni.appwindow.get_default_app_window()
            app_window.resize(self._saved_width, self._saved_height)
            await omni.appwindow.get_default_app_window().get_window_resize_event_stream().next_event()

        if self._restore_dock_window and self._restore_window:
            self._restore_dock_window.dock_in(self._restore_window, self._restore_position)
            self._restore_window = None
            self._restore_position = None
            self._restore_dock_window = None

    async def do_capture(self, img_name=None, img_suffix=""):
        await capture(self.get_img_name(img_name, img_suffix))
        await self.restore()

    async def capture_and_compare(self, image_name, threshold, compare_op, golden_image_name=None):
        golden_img_dir = self._GOLDEN_IMG_DIR
        image1 = OUTPUTS_DIR.joinpath(image_name)
        image2 = golden_img_dir.joinpath(golden_image_name or image_name)
        image_diffmap_name = f"{Path(image_name).stem}.diffmap.png"
        image_diffmap = OUTPUTS_DIR.joinpath(image_diffmap_name)

        await capture(image_name, publish=False)

        carb.log_info(f"Capturing {image1} and comparing with {image2}")

        try:
            diff_ratio = compare(image1, image2, image_diffmap, threshold, compare_op, *self._crop_config)
            if compare_op(diff_ratio, threshold):
                print(
                    f"##teamcity[testMetadata name='Difference Ratio {image_name}' type='number' value='{diff_ratio}']"
                )
                print(f"##teamcity[testMetadata name='Threshold {image_name}' type='number' value='{threshold}']")
                # print(f"##teamcity[publishArtifacts '{image2} => golden']")
                # print(f"##teamcity[testMetadata type='image' value='golden/{image_name}']")
                print(f"##teamcity[publishArtifacts '{image1} => results']")
                print(f"##teamcity[testMetadata type='image' value='results/{image_name}']")
                print(f"##teamcity[publishArtifacts '{image_diffmap} => results']")
                print(f"##teamcity[testMetadata type='image' value='results/{image_diffmap_name}']")

            return diff_ratio
        except CompareError as e:
            carb.log_error(f"Failed to compare images for {image_name}. Error: {e}")
            return 0

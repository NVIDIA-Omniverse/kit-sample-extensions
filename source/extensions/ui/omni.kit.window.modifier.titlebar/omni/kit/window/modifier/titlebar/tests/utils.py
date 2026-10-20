import sys
import traceback
from pathlib import Path
from typing import Tuple

import carb
import omni.kit.app
from omni.ui.tests.compare_utils import OUTPUTS_DIR, CompareError

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
GOLDEN_IMAGE_PATH = TEST_DATA_PATH.joinpath("golden_img")
PRINT_DEBUG = False


def DBG_PRINT(*args):  # pragma: no cover
    if PRINT_DEBUG:
        print(*args)


def set_mouse_pos(x, y):  # pragma: no cover
    if sys.platform != "win32":
        return
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


class MainWindowInfo:  # pragma: no cover
    def __init__(self, max_width, max_height):
        self._x = 0
        self._y = 0
        self._w = 0
        self._h = 0

        self._border_width = 0
        self._caption_height = 0

        self._max_width = max_width - 120
        self._max_height = max_height - 120

        if self.fetch_info():
            DBG_PRINT("MainWindowInfo:")
            DBG_PRINT(f"x: {self._x}")
            DBG_PRINT(f"y: {self._y}")
            DBG_PRINT(f"w: {self._w}")
            DBG_PRINT(f"h: {self._h}")

            DBG_PRINT(f"border_width: {self._border_width}")
            DBG_PRINT(f"caption_height: {self._caption_height}")
        else:
            DBG_PRINT("MainWindowInfo fetch information failed")

    def fetch_info(self):
        cur_process = ctypes.windll.kernel32.GetCurrentProcessId()
        hwnd = 0
        class_name = "GLFW30"
        while True:
            hwnd = ctypes.windll.user32.FindWindowExW(0, hwnd, class_name, 0)
            if hwnd == 0:
                break

            pid_buf = ctypes.c_ulong(0)
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.pointer(pid_buf))
            pid = pid_buf.value
            if pid == cur_process:
                break

        if hwnd == 0:
            DBG_PRINT("ERROR: Failed to find main window!")
            return False

        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.SetForegroundWindow(hwnd)

        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))
        width = min(rect.right - rect.left, self._max_width)
        height = min(rect.bottom - rect.top, self._max_height)

        ctypes.windll.user32.MoveWindow(hwnd, 60, 60, width, height, True)
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))

        self._x = rect.left
        self._y = rect.top
        self._w = rect.right - rect.left
        self._h = rect.bottom - rect.top

        ctypes.windll.user32.GetClientRect(hwnd, ctypes.pointer(rect))
        client_width = rect.right - rect.left
        client_height = rect.bottom - rect.top
        self._border_width = (self._w - client_width) / 2
        self._caption_height = self._h - self._border_width - client_height

        return True

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def w(self):
        return self._w

    @property
    def h(self):
        return self._h

    @property
    def border_w(self):
        return self._border_width

    @property
    def caption_h(self):
        return self._caption_height

    @property
    def client_w(self):
        return self._w - self._border_width * 2

    @property
    def client_h(self):
        return self._h - self._caption_height - self._border_width


def compare_pixels(image1: Path, image2: Path, mask: Path, image_diffmap: Path):  # pragma: no cover
    """
    Compares two images and return a value that indicates the maximum differrence between pixels. 0 is no difference
    in the range [0-255].

    It uses Pillow for image read.

    Args:
        image1, image2: images to compare
        image_diffmap: the difference map image will be saved if there is any difference between given images

    """
    if not image1.exists():
        raise CompareError(f"File image1 {image1} does not exist")
    if not image2.exists():
        raise CompareError(f"File image2 {image2} does not exist")

    if "PIL" not in sys.modules.keys():
        # OMFP-1890: Pillow should come from pip prebundle
        carb.log_error("Cannot find Pillow from pip prebundle. Image comparison failed.")
        return

    from PIL import Image, ImageChops

    original = Image.open(str(image1))
    contrast = Image.open(str(image2))
    mask_img = Image.open(str(mask))

    DBG_PRINT(f"Original: {original.width}x{original.height}")
    DBG_PRINT(f"contrast: {contrast.width}x{contrast.height}")
    DBG_PRINT(f"mask_img: {mask_img.width}x{mask_img.height}")

    if original.width != contrast.width or original.height != contrast.height:
        raise CompareError(
            f"[omni.ui.test] Can't compare different resolutions\n\n"
            f"{image1} {original.size[0]}x{original.size[1]}\n"
            f"{image2} {contrast.size[0]}x{contrast.size[1]}\n\n"
            f"It's possible that your monitor DPI is not 100%.\n\n"
        )

    differs = 0
    original_data = original.load()
    contrast_data = contrast.load()
    mask_data = mask_img.load()

    cx = min(original.width, mask_img.width)
    cy = min(original.height, mask_img.height)
    for x in range(cx):
        for y in range(cy):
            mask_pixel = mask_data[x, y]
            if mask_pixel[0] == 0 and mask_pixel[1] == 0 and mask_pixel[2] == 0:
                continue
            if original_data[x, y] != contrast_data[x, y]:
                differs += 1

    if differs > 0:
        difference = ImageChops.difference(original, contrast).convert("RGB")
        # Images are different
        # Multiply image by 255
        difference = difference.point(lambda i: min(i * 255, 255))
        difference.save(str(image_diffmap))

    return differs


async def capture_and_compare(image_name: str, capture_region, threshold=20) -> bool:  # pragma: no cover
    # The window has transparent round corner and total 16 pixles will be different
    capture_filename = OUTPUTS_DIR.joinpath(image_name + ".png")
    golden_filename = GOLDEN_IMAGE_PATH.joinpath(image_name + ".png")
    mask_filename = GOLDEN_IMAGE_PATH.joinpath("mask.png")
    differ_filename = OUTPUTS_DIR.joinpath(image_name + ".differmap.png")

    if "PIL" not in sys.modules.keys():
        # OMFP-1890: Pillow should come from pip prebundle
        carb.log_error("Cannot find Pillow from pip prebundle. Image comparison failed.")
        return

    from PIL import ImageGrab

    ss_img = ImageGrab.grab(capture_region)
    ss_img.save(capture_filename)

    try:
        diff = compare_pixels(capture_filename, golden_filename, mask_filename, differ_filename)
        if diff >= threshold:
            DBG_PRINT(f"##teamcity[publishArtifacts '{capture_filename} => results']")
            DBG_PRINT(f"##teamcity[publishArtifacts '{differ_filename} => results']")
            DBG_PRINT(f"##teamcity[publishArtifacts '{golden_filename} => golden']")

        return diff < threshold
    except CompareError as e:
        carb.log_error(f"[omni.ui.tests.compare] Failed to compare images for {image_name}. Error: {e}")
        exc = traceback.format_exc()
        carb.log_error(f"[omni.ui.tests.compare] Traceback:\n{exc}")
        return False

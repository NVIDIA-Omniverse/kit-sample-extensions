import os
import platform
from functools import lru_cache
from pathlib import Path

import omni.kit.app
import omni.usd
from omni.kit import ui_test
from omni.kit.ui_test import Vec2, WidgetRef
from pxr import Usd

try:
    import omni.mdl.neuraylib.utils

    ENABLE_NEURAYLIB_UTILS = True
except:
    ENABLE_NEURAYLIB_UTILS = False


def get_test_file_names():
    # OMPE-55763: FBX is not supported on aarch64
    if platform.machine() == "aarch64":
        file_names = ["cube.obj", "cube.gltf"]
    else:
        file_names = ["cube.fbx", "cube.obj", "cube.gltf"]
    if ENABLE_NEURAYLIB_UTILS:
        file_names.append("cube_mdl.gltf")
    # TODO: return ["cube.fbx", "cube.obj", "cube.gltf", "cube_mdl.gltf"] directly when neyraylib fixed in 106.0.3
    return file_names


async def set_content_browser_grid_view(grid_view_enabled: bool):
    from omni.kit.window.content_browser.test_helper import ContentBrowserTestHelper

    async with ContentBrowserTestHelper() as content_browser_helper:
        await content_browser_helper.toggle_grid_view_async(grid_view_enabled)


async def get_content_browser_path_item(path: str):
    import omni.ui as ui
    from omni.kit.window.content_browser import get_content_window

    # content_browser to path
    content_browser = get_content_window()
    # grid_view_enabled = content_browser.window.widget.api.view.show_grid_view
    current = content_browser.get_current_selections()
    # FIXME - if navigate_to(path) and path widget is last in listview and listview is scrollable scroll_here doesn't work as expected. IE it will be not visible in listview
    if not (current and len(current) == 1 and current[0].replace("\\", "/").lower() == path.replace("\\", "/").lower()):
        content_browser.navigate_to(path)
        await ui_test.human_delay()

    # get content window file index from texture_path
    treeview_widget = ui_test.find("Content//Frame/**/TreeView[*].identifier=='content_browser_treeview'")
    file_name = path.split("/")[-1]
    tree_item = treeview_widget.find(f"**/Label[*].text=='{file_name}'")
    return tree_item, file_name

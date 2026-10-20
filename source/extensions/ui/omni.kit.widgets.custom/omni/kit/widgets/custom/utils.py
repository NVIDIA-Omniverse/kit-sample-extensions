# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

import carb


def Singleton(class_):
    """
    A singleton decorator.

    TODO: It's also available in omni.kit.widget.stage. Do we have a utility extension where we can put the utilities
    like this?
    """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@Singleton
class EditorCheck(object):
    """The singleton that checks if the editor is available. We need it to disable USD examples id we are in Kit Mini"""

    def __init__(self):
        # Check if kit::IEditor is present, if not, we're in kit-mini
        try:
            import omni.kit.editor

            editor = omni.kit.editor.get_editor_interface()
            self._has_ieditor = editor is not None
            self._editor = editor
        except (ModuleNotFoundError, RuntimeError):
            self._has_ieditor = False
            self._editor = None

    @property
    def has_editor(self):
        """Read-only property that indicates if omni.kit.editor is available"""
        return self._has_ieditor

    def capture_screenshot(self, capture_filename, wait_result=False):  # pragma: no cover
        # TODO: viewport_legacy is not in kit 105.1+ should we remove this function?
        import omni.kit.viewport_legacy as viewport
        import omni.renderer_capture

        viewport_interface = viewport.acquire_viewport_interface()
        self._renderer = omni.renderer_capture.acquire_renderer_capture_interface()
        viewport_window = viewport_interface.get_viewport_window(None)

        def _capture_helper(viewport_rp_resource):
            self._renderer.capture_next_frame_rp_resource(capture_filename, viewport_rp_resource)

        viewport.deferred_capture(
            viewport_window, _capture_helper, is_hdr=False, subscription_name="view capture helper"
        )


def get_icon_path(icon_file):
    path = Path(__file__).parent
    count = 7
    while count > 0:
        if Path.exists(path.joinpath("icons")):
            return path.joinpath(f"icons/{icon_file}").as_posix()
        path = path.parent
        count = count - 1

    carb.log_error(f"Can not find icon path for {__file__}")
    return ""


def merge_dicts(a, b):
    result = a.copy()
    result.update(b)
    return result


def uniform_absolute_path(path):
    if len(path) == 1:
        return path[0].lower()

    # Windows path
    if len(path) > 1 and path[1] == ":":
        # Here use upper drive letter, otherwise content_browser.navigate_to does not work
        path = path[0].upper() + path[1:]
    path = path.replace("\\", "/")
    path = path.replace("\\\\", "/")

    if path.startswith("omniverse://"):
        path = path[0:12] + path[12:].replace("//", "/")
    else:
        path = path.replace("//", "/")
    path = path.replace("\\/", "/")
    path = path.replace("/\\", "/")

    if path.startswith("omniverse://"):  # omni path
        path_prefix = "omniverse://"
        asset_path = path[12:]
        if "/" in path[12:]:
            index = asset_path.index("/")
            path_prefix += asset_path[0:index]
            asset_path = asset_path[index:]
    elif path[1] == ":":  # windows path
        path_prefix = path[0:2]
        asset_path = path[2:]
    else:  # linux path
        path_prefix = ""
        asset_path = path

    parts = asset_path.split("/")
    results = []
    for part in parts:
        if part == "..":
            if results:
                results.pop(-1)
            if not results:
                break
        elif part != ".":
            results.append(part)

    return path_prefix + "/".join(results)

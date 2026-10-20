# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from .zoom_bar import ZoomBar


class FileZoomBar(ZoomBar):
    """
    Reprent a zoom bar used for file system to replace omni.kit.window.filepicker.ZoomBar with same args.

    Keyword args:
        grid_view_scale (int): Initial value of the slider. Default 2.
        show_grid_view (bool): Show in icon mode or detail mode. Default False means show in detail mode.
        on_toggle_grid_view_fn (callable): Function called when view mode changed. Default None, also means view mode will never be changed. Function signure:
            void on_toggle_grid_view_fn(icon_mode: bool)
        on_scale_grid_view_fn (callable): Function called when slider value changed. Value is mapped to {0: 0.25, 1: 0.5, 2: 0.75, 3: 1, 4: 1.5, 5: 2.0}.
            Default None. Function signure:
            void on_scale_grid_view_fn(value: float)
    """

    def __init__(
        self,
        show_grid_view: bool = False,
        grid_view_scale: int = 2,
        on_toggle_grid_view_fn: callable = None,
        on_scale_grid_view_fn: callable = None,
    ):
        self._on_scale_grid_view_fn = on_scale_grid_view_fn
        super().__init__(
            value=grid_view_scale,
            icon_mode=show_grid_view,
            on_view_mode_changed_fn=on_toggle_grid_view_fn,
            on_value_changed_fn=self._on_scale_grid_view,
        )

    def _on_scale_grid_view(self, value: int):
        scale_map = {0: 0.25, 1: 0.5, 2: 0.75, 3: 1, 4: 1.5, 5: 2.0}
        scale = scale_map.get(value, 2)
        if self._on_scale_grid_view_fn:
            self._on_scale_grid_view_fn(scale)

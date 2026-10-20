# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.ui as ui

from ..style import CONTEXT_MENU_STYLE


class ContextMenu(ui.Menu):  # pragma: no cover - never called
    """
    Context menu for folder browser's category item right click.
    """

    def __init__(self):
        super().__init__("Folder browser category menu", style=CONTEXT_MENU_STYLE)
        self.urls = []
        self.folder_name = None
        try:
            # pylint: disable=redefined-outer-name
            import omni.kit.tool.collect  # noqa: F401

            with self:
                ui.MenuItem(
                    f"{omni.kit.ui.get_custom_glyph_code('${glyphs}/none.svg')}  Collect", triggered_fn=self._collect
                )
        except ImportError:
            carb.log_warn("Plese enable omni.kit.tool.collect first to collect.")

    def _collect(self):
        try:
            # pylint: disable=redefined-outer-name
            import omni.kit.tool.collect

            collect_instance = omni.kit.tool.collect.get_instance()
            collect_instance.collect_multiple(self.urls, self.folder_name)
            collect_instance = None
        except ImportError:
            carb.log_warn("Failed to import collect module (omni.kit.tool.collect). Please enable it first.")
        except AttributeError:
            carb.log_warn("Require omni.kit.tool.collect v2.1.8 or later!")

    def show_menu(self):
        try:
            # pylint: disable=redefined-outer-name
            import omni.kit.tool.collect

            collect_instance = omni.kit.tool.collect.get_instance()
            if hasattr(collect_instance, "collect_multiple"):
                self.show()
        except ImportError:
            carb.log_warn("Failed to import collect module (omni.kit.tool.collect). Please enable it first.")
        except AttributeError:
            carb.log_warn("Require omni.kit.tool.collect v2.1.8 or later!")

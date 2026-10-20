# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ui as ui
from omni.kit import ui_test


async def toggle_on_named_column(column_name: str):
    from omni.kit.ui_test.query import MenuRef

    # Click on the Options hamburger menu
    await ui_test.find("Stage//Frame/**/Button[*].name=='options'").click()
    await ui_test.human_delay(10)

    menu = MenuRef(widget=ui.Menu.get_current(), path="Menu")
    # get treeview
    tree_menu = menu.find("**/TreeView[*]")

    # Find the specified child out of the treeview options and toggle it ON
    for child in tree_menu.widget.model.get_item_children(None):
        if child.name_model.as_string == column_name:
            child.checked_model.as_bool = True

    # click reset to hide menu
    await ui_test.select_context_menu("Reset", offset=ui_test.Vec2(10, 10))
    await ui_test.human_delay(50)

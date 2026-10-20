# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""
* Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
"""

import omni.ui as ui
import omni.usd


class VariantSetsDelegate(ui.AbstractItemDelegate):
    """Delegate of the Mapper Batcher"""

    def __init__(self):
        super(VariantSetsDelegate, self).__init__()
        self.style = {
            "Circle::variant_set": {"color": 0xFF8A8777, "background_color": 0xFF8A8777},
            "Label::object_name": {"color": 0xFF8A8777},
            "Label::object_name:selected": {"color": 0xFF23211F},
            "Circle::variant_set:selected": {"color": 0xFF23211F, "background_color": 0xFF23211F},
        }

    def build_branch(self, model, item, column_id, level, expanded):
        pass

    def build_widget(self, model, item, column_id, level, expanded):
        """Create a widget per item"""
        if column_id == 0:
            with ui.HStack(style=self.style):
                ui.Spacer(width=4)
                with ui.VStack(width=0):
                    ui.Spacer()
                    with ui.VStack(width=0, height=0):
                        # FIXME: Adding the spacer for alignment
                        ui.Spacer(height=2)
                        circle = ui.Circle(
                            width=5,
                            height=5,
                            alignment=ui.Alignment.CENTER,
                            name="variant_set",
                            # style_type_name_override="TreeView.Item",
                        )
                    ui.Spacer()
                ui.Spacer(width=4)
                label = ui.Label(item.variant_set_name, name="object_name", elided_text=True)

            selected = omni.usd.get_context().get_selection().is_prim_path_selected(str(item.path))
            label.selected = selected
            circle.selected = selected

        if column_id == 1:
            model = item.get_variant_model()
            with ui.VStack():
                ui.Spacer()
                ui.ComboBox(model)
                ui.Spacer()

    def build_header(self, column_id):
        """Build the header"""
        return

    def destroy(self):
        pass

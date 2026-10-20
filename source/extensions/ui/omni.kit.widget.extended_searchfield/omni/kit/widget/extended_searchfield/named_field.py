# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ui as ui


class NamedField:
    def __init__(self, name: str, hint: str = ""):
        self._name = name
        self._hint = hint
        self._default = ""
        self._clear_button = None
        self._hint_container = None
        self._build_ui()

    def set_default(self):
        self._model.set_value(self._default)

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._sub_begin_edit = None
        self._sub_end_edit = None
        self._sub_value_changed = None
        self._string_field = None
        self._container = None
        self._hint_container = None
        self._clear_button = None
        self._model = None

    @property
    def name(self):
        return self._name

    @property
    def model(self):
        return self._model

    @property
    def container(self):
        return self._container

    def _on_begin_edit(self, model: ui.AbstractValueModel):
        if self._hint_container:
            self._hint_container.visible = False
        if self._clear_button:
            self._clear_button.visible = False

    def _on_end_edit(self, model: ui.AbstractValueModel):
        empty = model.get_value_as_string().strip() == ""
        if self._hint_container:
            self._hint_container.visible = empty
        if self._clear_button:
            self._clear_button.visible = not empty

    def _on_clear_clicked(self):
        self._model.set_value("")
        if self._hint_container:
            self._hint_container.visible = True
        if self._clear_button:
            self._clear_button.visible = False

    def _build_ui(self):
        self._container = ui.ZStack()
        with self._container:
            self._background = ui.Rectangle(style_type_name_override="ExtendedSearchField.Frame")
            with ui.HStack():
                with ui.ZStack():
                    self._string_field = ui.StringField(name=self._name, alignment=ui.Alignment.LEFT_CENTER)
                    self._model = self._string_field.model

                    self._sub_begin_edit = self._model.subscribe_begin_edit_fn(self._on_begin_edit)
                    self._sub_end_edit = self._model.subscribe_end_edit_fn(self._on_end_edit)
                    self._sub_value_changed = self._model.subscribe_value_changed_fn(self._on_end_edit)

                    self._hint_container = ui.HStack(spacing=5)
                    with self._hint_container:
                        ui.Spacer(width=10)
                        ui.Label(self._hint, style_type_name_override="ExtendedSearchField.Hint")

                # Close icon
                with ui.VStack(width=20):
                    ui.Spacer(height=2)
                    self._clear_button = ui.Button(
                        image_width=12,
                        style_type_name_override="SearchField.ClearButton",
                        clicked_fn=self._on_clear_clicked,
                    )
                    self._clear_button.visible = False
                    ui.Spacer(height=2)
                ui.Spacer(width=2)

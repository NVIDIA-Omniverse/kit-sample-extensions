# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["get_style"]

import carb.settings
import omni.ui as ui


def get_style():
    """Get UI default style.

    Returns:
        dict: style dictionary.
    """
    kit_green = 0xFF8A8777
    kit_green_checkbox = 0xFF9A9A9A
    border_radius = 1.5
    font_size = 14.0

    style_settings = carb.settings.get_settings().get("/persistent/app/window/uiStyle")
    if not style_settings:
        style_settings = "NvidiaDark"

    if style_settings == "NvidiaLight":
        window_background_color = 0xFF444444
        button_background_color = 0xFF545454
        button_background_hovered_color = 0xFF9E9E9E
        button_background_pressed_color = 0xC22A8778
        button_label_disabled_color = 0xFF606060

        frame_text_color = 0xFF545454
        field_background = 0xFF545454
        field_secondary = 0xFFABABAB
        field_text_color = 0xFFD6D6D6
        field_text_color_read_only = 0xFF9C9C9C
        field_text_color_hidden = 0x01000000
        field_text_color_url = 0xFFB99B00

        collapsableframe_border_color = 0x0
        collapsableframe_background_color = 0x7FD6D6D6
        collapsableframe_text_color = 0xFF545454

        collapsableframe_groupframe_background_color = 0xFFC9C9C9
        collapsableframe_subframe_background_color = 0xFFD6D6D6
        collapsableframe_hovered_background_color = 0xFFCCCFBF
        collapsableframe_pressed_background_color = 0xFF2E2E2B
        collapsableframe_hovered_secondary_color = 0xFFD6D6D6
        collapsableframe_pressed_secondary_color = 0xFFE6E6E6
        label_vectorlabel_color = 0xFFDDDDDD
        label_mixed_color = 0xFFD6D6D6
        light_font_size = 14.0
        light_border_radius = 3

        grab_color = 0xFF1F2123

        style = {
            "Window": {"background_color": window_background_color},
            "Button": {"background_color": button_background_color, "margin": 0, "padding": 3, "border_radius": 2},
            "Button:hovered": {"background_color": button_background_hovered_color},
            "Button:pressed": {"background_color": button_background_pressed_color},
            "Button.Label:disabled": {"color": 0xFFD6D6D6},
            "Button.Label": {"color": 0xFFD6D6D6},
            "Field::models": {
                "background_color": field_background,
                "font_size": light_font_size,
                "color": field_text_color,
                "border_radius": light_border_radius,
                "secondary_color": field_secondary,
            },
            "Field::url": {
                "background_color": field_background,
                "font_size": light_font_size,
                "color": field_text_color_url,
                "border_radius": light_border_radius,
                "secondary_color": field_secondary,
            },
            "Field::models_mixed": {
                "background_color": field_background,
                "font_size": light_font_size,
                "color": field_text_color_hidden,
                "border_radius": light_border_radius,
            },
            "Field::models_readonly": {
                "background_color": field_background,
                "font_size": light_font_size,
                "color": field_text_color_read_only,
                "border_radius": light_border_radius,
                "secondary_color": field_secondary,
            },
            "Field::models_readonly_mixed": {
                "background_color": field_background,
                "font_size": light_font_size,
                "color": field_text_color_hidden,
                "border_radius": light_border_radius,
            },
            "Field::models:pressed": {"background_color": 0xFFCECECE},
            "Field": {"background_color": 0xFF535354, "color": 0xFFCCCCCC},
            "Label": {"font_size": 12, "color": frame_text_color},
            "Label::label:disabled": {"color": button_label_disabled_color},
            "Label::label": {
                "font_size": light_font_size,
                "background_color": field_background,
                "color": frame_text_color,
            },
            "Label::title": {
                "font_size": light_font_size,
                "background_color": field_background,
                "color": frame_text_color,
            },
            "Label::mixed_overlay": {
                "font_size": light_font_size,
                "background_color": field_background,
                "color": frame_text_color,
            },
            "Label::mixed_overlay_normal": {
                "font_size": light_font_size,
                "background_color": field_background,
                "color": frame_text_color,
            },
            "ComboBox::choices": {
                "font_size": 12,
                "color": 0xFFD6D6D6,
                "background_color": field_background,
                "secondary_color": field_background,
                "border_radius": light_border_radius * 2,
            },
            "ComboBox::choices:disabled": {
                "color": button_label_disabled_color,
                "secondary_selected_color": button_label_disabled_color,
            },
            "ComboBox::xform_op": {
                "font_size": 10,
                "color": 0xFF333333,
                "background_color": 0xFF9C9C9C,
                "secondary_color": 0x0,
                "selected_color": 0xFFACACAF,
                "border_radius": light_border_radius * 2,
            },
            "ComboBox::xform_op:hovered": {"background_color": 0x0},
            "ComboBox::xform_op:selected": {"background_color": 0xFF545454},
            "ComboBox": {
                "font_size": 10,
                "color": 0xFFE6E6E6,
                "background_color": 0xFF545454,
                "secondary_color": 0xFF545454,
                "selected_color": 0xFFACACAF,
                "border_radius": light_border_radius * 2,
            },
            # "ComboBox": {"background_color": 0xFF535354, "selected_color": 0xFFACACAF, "color": 0xFFD6D6D6},
            "ComboBox:hovered": {"background_color": 0xFF545454},
            "ComboBox:selected": {"background_color": 0xFF545454},
            "ComboBox::choices_mixed": {
                "font_size": light_font_size,
                "color": 0xFFD6D6D6,
                "background_color": field_background,
                "secondary_color": field_background,
                "secondary_selected_color": field_text_color,
                "border_radius": light_border_radius * 2,
            },
            "ComboBox:hovered:choices": {"background_color": field_background, "secondary_color": field_background},
            "Slider::value": {
                "font_size": light_font_size,
                "color": field_text_color,  # collapsableframe_text_color
                "border_radius": light_border_radius,
                "background_color": field_background,
                "secondary_color": kit_green,
            },
            "Slider::value_mixed": {
                "font_size": light_font_size,
                "color": field_text_color_hidden,
                "border_radius": light_border_radius,
                "background_color": field_background,
                "secondary_color": kit_green,
            },
            "Slider::multivalue": {
                "font_size": light_font_size,
                "color": field_text_color,
                "border_radius": light_border_radius,
                "background_color": field_background,
                "secondary_color": kit_green,
                "draw_mode": ui.SliderDrawMode.HANDLE,
            },
            "Slider::multivalue_mixed": {
                "font_size": light_font_size,
                "color": field_text_color_hidden,
                "border_radius": light_border_radius,
                "background_color": field_background,
                "secondary_color": kit_green,
                "draw_mode": ui.SliderDrawMode.HANDLE,
            },
            "CheckBox::greenCheck": {"font_size": 10, "background_color": kit_green, "color": 0xFF23211F},
            "CheckBox::greenCheck_mixed": {
                "font_size": 10,
                "background_color": kit_green,
                "color": field_text_color_hidden,
                "border_radius": light_border_radius,
            },
            "CollapsableFrame": {
                "background_color": collapsableframe_background_color,
                "secondary_color": collapsableframe_background_color,
                "color": collapsableframe_text_color,
                "border_radius": light_border_radius,
                "border_color": 0x0,
                "border_width": 1,
                "font_size": light_font_size,
                "padding": 6,
            },
            "CollapsableFrame::groupFrame": {
                "background_color": collapsableframe_groupframe_background_color,
                "secondary_color": collapsableframe_groupframe_background_color,
                "border_radius": border_radius * 2,
                "padding": 6,
            },
            "CollapsableFrame::groupFrame:hovered": {
                "background_color": collapsableframe_groupframe_background_color,
                "secondary_color": collapsableframe_groupframe_background_color,
            },
            "CollapsableFrame::groupFrame:pressed": {
                "background_color": collapsableframe_groupframe_background_color,
                "secondary_color": collapsableframe_groupframe_background_color,
            },
            "CollapsableFrame::subFrame": {
                "background_color": collapsableframe_subframe_background_color,
                "secondary_color": collapsableframe_subframe_background_color,
            },
            "CollapsableFrame::subFrame:hovered": {
                "background_color": collapsableframe_subframe_background_color,
                "secondary_color": collapsableframe_hovered_background_color,
            },
            "CollapsableFrame::subFrame:pressed": {
                "background_color": collapsableframe_subframe_background_color,
                "secondary_color": collapsableframe_pressed_background_color,
            },
            "CollapsableFrame.Header": {
                "font_size": light_font_size,
                "background_color": frame_text_color,
                "color": frame_text_color,
            },
            "CollapsableFrame:hovered": {"secondary_color": collapsableframe_hovered_secondary_color},
            "CollapsableFrame:pressed": {"secondary_color": collapsableframe_pressed_secondary_color},
            "Label::vector_label": {"font_size": 14, "color": label_vectorlabel_color},
            "Rectangle::vector_label": {"border_radius": border_radius * 2, "corner_flag": ui.CornerFlag.LEFT},
            "Rectangle::mixed_overlay": {
                "border_radius": light_border_radius,
                "background_color": field_background,
                "border_width": 3,
            },
            "Rectangle::mixed_overlay_text": {"background_color": field_background},
            "Rectangle": {"border_radius": light_border_radius, "background_color": field_background},
            "Rectangle::xform_op:hovered": {"background_color": 0x0},
            "Rectangle::xform_op": {"background_color": 0x0},
            "Rectangle::backdrop": {"border_radius": 2.0, "padding": 0, "margin": 0},
            # text remove
            "Button::remove": {"background_color": field_background, "margin": 0},
            "Button::remove:hovered": {"background_color": field_background},
            "Line::grab": {"color": grab_color},
        }
    else:
        label_color = 0xFF8F8E86
        field_background = 0xFF23211F
        field_text_color = 0xFFD5D5D5
        field_text_color_read_only = 0xFF5C5C5C
        field_text_color_hidden = 0x01000000
        field_text_color_url = 0xFFB99B00
        frame_text_color = 0xFFCCCCCC
        window_background_color = 0xFF444444
        button_background_color = 0xFF292929
        button_background_hovered_color = 0xFF9E9E9E
        button_background_pressed_color = 0xC22A8778
        button_label_disabled_color = 0xFF606060
        label_label_color = 0xFF9E9E9E
        label_title_color = 0xFFAAAAAA
        label_mixed_color = 0xFFE6B067
        label_vectorlabel_color = 0xFFDDDDDD
        colorwidget_border_color = 0xFF1E1E1E
        combobox_hovered_background_color = 0xFF33312F
        collapsableframe_border_color = 0x0
        collapsableframe_background_color = 0xFF343432
        collapsableframe_groupframe_background_color = 0xFF23211F
        collapsableframe_subframe_background_color = 0xFF343432
        collapsableframe_hovered_background_color = 0xFF2E2E2B
        collapsableframe_pressed_background_color = 0xFF2E2E2B
        grab_color = 0xFF1F2123
        backdrop_color = 0xFF4A4A4A

        style = {
            "Window": {"background_color": window_background_color},
            "Button": {"background_color": button_background_color, "margin": 0, "padding": 3, "border_radius": 2},
            "Button:hovered": {"background_color": button_background_hovered_color},
            "Button:pressed": {"background_color": button_background_pressed_color},
            "Button.Label:disabled": {"color": button_label_disabled_color},
            "SearchField.Frame": {
                "background_color": field_background,
                "border_radius": border_radius,
            },
            "Field::models": {
                "background_color": field_background,
                "font_size": font_size,
                "color": field_text_color,
                "border_radius": border_radius,
            },
            "Field::url": {
                "background_color": field_background,
                "font_size": font_size,
                "color": field_text_color_url,
                "border_radius": border_radius,
            },
            "Field::models_mixed": {
                "background_color": field_background,
                "font_size": font_size,
                "color": field_text_color_hidden,
                "border_radius": border_radius,
            },
            "Field::models_readonly": {
                "background_color": field_background,
                "font_size": font_size,
                "color": field_text_color_read_only,
                "border_radius": border_radius,
            },
            "Field::models_readonly_mixed": {
                "background_color": field_background,
                "font_size": font_size,
                "color": field_text_color_hidden,
                "border_radius": border_radius,
            },
            "Label": {"font_size": 12, "color": label_color},
            "Label::label": {"font_size": font_size, "color": label_label_color},
            "Label::label:disabled": {"color": button_label_disabled_color},
            "Label::title": {"font_size": font_size, "color": label_title_color},
            "Label::mixed_overlay": {"font_size": font_size, "color": label_mixed_color},
            "Label::mixed_overlay_normal": {"font_size": font_size, "color": field_text_color},
            "Label::path_label": {"font_size": font_size, "color": label_label_color},
            "Label::stage_label": {"font_size": font_size, "color": label_label_color},
            "ComboBox::choices": {
                "font_size": font_size,
                "color": field_text_color,
                "background_color": field_background,
                "secondary_color": field_background,
                "secondary_selected_color": field_text_color,
                "border_radius": border_radius,
            },
            "ComboBox::choices:disabled": {
                "color": button_label_disabled_color,
                "secondary_selected_color": button_label_disabled_color,
            },
            "ComboBox::choices_mixed": {
                "font_size": font_size,
                "color": field_text_color_hidden,
                "background_color": field_background,
                "secondary_color": field_background,
                "secondary_selected_color": field_text_color,
                "border_radius": border_radius,
            },
            "ComboBox:hovered:choices": {
                "background_color": combobox_hovered_background_color,
                "secondary_color": combobox_hovered_background_color,
            },
            "Slider::value": {
                "font_size": font_size,
                "color": field_text_color,
                "border_radius": border_radius,
                "background_color": field_background,
                "secondary_color": window_background_color,
            },
            "Slider::value_mixed": {
                "font_size": font_size,
                "color": field_text_color_hidden,
                "border_radius": border_radius,
                "background_color": field_background,
                "secondary_color": window_background_color,
            },
            "Slider::multivalue": {
                "font_size": font_size,
                "color": field_text_color,
                "border_radius": border_radius,
                "background_color": field_background,
                "secondary_color": window_background_color,
                "draw_mode": ui.SliderDrawMode.HANDLE,
            },
            "Slider::multivalue_mixed": {
                "font_size": font_size,
                "color": field_text_color_hidden,
                "border_radius": border_radius,
                "background_color": field_background,
                "secondary_color": window_background_color,
                "draw_mode": ui.SliderDrawMode.HANDLE,
            },
            "CheckBox::greenCheck": {
                "font_size": 12,
                "background_color": kit_green_checkbox,
                "color": field_background,
                "border_radius": border_radius,
            },
            "CheckBox::greenCheck_mixed": {
                "font_size": 12,
                "background_color": kit_green_checkbox,
                "color": field_text_color_hidden,
                "border_radius": border_radius,
            },
            "CollapsableFrame": {
                "background_color": collapsableframe_background_color,
                "secondary_color": collapsableframe_background_color,
                "border_radius": border_radius * 2,
                "border_color": collapsableframe_border_color,
                "border_width": 1,
                "padding": 6,
            },
            "CollapsableFrame::groupFrame": {
                "background_color": collapsableframe_groupframe_background_color,
                "secondary_color": collapsableframe_groupframe_background_color,
                "border_radius": border_radius * 2,
                "padding": 6,
            },
            "CollapsableFrame::groupFrame:hovered": {
                "background_color": collapsableframe_groupframe_background_color,
                "secondary_color": collapsableframe_groupframe_background_color,
            },
            "CollapsableFrame::groupFrame:pressed": {
                "background_color": collapsableframe_groupframe_background_color,
                "secondary_color": collapsableframe_groupframe_background_color,
            },
            "CollapsableFrame::subFrame": {
                "background_color": collapsableframe_subframe_background_color,
                "secondary_color": collapsableframe_subframe_background_color,
            },
            "CollapsableFrame::subFrame:hovered": {
                "background_color": collapsableframe_subframe_background_color,
                "secondary_color": collapsableframe_hovered_background_color,
            },
            "CollapsableFrame::subFrame:pressed": {
                "background_color": collapsableframe_subframe_background_color,
                "secondary_color": collapsableframe_pressed_background_color,
            },
            "CollapsableFrame.Header": {
                "font_size": font_size,
                "background_color": frame_text_color,
                "color": frame_text_color,
            },
            "CollapsableFrame:hovered": {"secondary_color": collapsableframe_hovered_background_color},
            "CollapsableFrame:pressed": {"secondary_color": collapsableframe_pressed_background_color},
            "ColorWidget": {
                "border_radius": border_radius,
                "border_color": colorwidget_border_color,
                "border_width": 0.5,
            },
            "Label::vector_label": {"font_size": 16, "color": label_vectorlabel_color},
            "Rectangle::vector_label": {"border_radius": border_radius * 2, "corner_flag": ui.CornerFlag.LEFT},
            "Rectangle::mixed_overlay": {
                "border_radius": border_radius,
                "background_color": label_mixed_color,
                "border_width": 3,
            },
            "Rectangle::mixed_overlay_text": {"background_color": field_background},
            "Rectangle::xform_op:hovered": {"background_color": 0xFF444444},
            "Rectangle::xform_op": {"background_color": 0xFF333333},
            "Rectangle::backdrop": {
                "background_color": backdrop_color,
                "border_radius": 2.0,
                "padding": 0,
                "margin": 0,
            },
            # text remove
            "Button::remove": {"background_color": field_background, "margin": 0},
            "Button::remove:hovered": {"background_color": field_background},
            "Line::grab": {"color": grab_color},
        }

    return style

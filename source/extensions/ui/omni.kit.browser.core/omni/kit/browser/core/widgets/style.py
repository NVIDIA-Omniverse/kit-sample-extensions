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
Centralized styling for omni.kit.browser.core extension.

This module defines all colors, constants, and styles following best practices:
- Uses omni.ui.color, omni.ui.constant, and omni.ui.url for all styling values
- Extension-specific prefixes (browser_*) prevent conflicts with other extensions
- Proper Type::Name:State selector hierarchy
"""

from omni import ui
from omni.ui import color as cl
from omni.ui import constant as fl
from omni.ui import url

# Layout constants
DETAIL_VIEW_PADDING = 2
FULL_LINE_HEIGHT = 20

# ==============================================================================
# Color Constants - Extension-specific with 'browser_' prefix
# ==============================================================================
# Background colors
cl.browser_background_dark = cl("1F2123")
cl.browser_background_light = cl("545353")
cl.browser_background = cl.shade(cl.browser_background_dark, light=cl.browser_background_light)

cl.browser_scrollbar_dark = cl("808080")
cl.browser_scrollbar_light = cl("9E9E9E")
cl.browser_scrollbar = cl.shade(cl.browser_scrollbar_dark, light=cl.browser_scrollbar_light)

# Selection colors
cl.browser_selected_dark = cl("34C7FF")
cl.browser_selected_light = cl("1A91C5")
cl.browser_selected = cl.shade(cl.browser_selected_dark, light=cl.browser_selected_light)

# Text colors
cl.browser_text_dark = cl("A1A1A1")
cl.browser_text_light = cl("E0E0E0")
cl.browser_text = cl.shade(cl.browser_text_dark, light=cl.browser_text_light)

cl.browser_darktext_dark = cl("504F50")
cl.browser_darktext_light = cl("A1A1A1")
cl.browser_darktext = cl.shade(cl.browser_darktext_dark, light=cl.browser_darktext_light)

cl.browser_lighttext = cl("ACACAC")

# Image colors
cl.browser_image = cl("A8A8A8")

# TreeView branch colors
cl.browser_branch = cl(0.36, 0.36, 0.36, 1.0)
cl.browser_expand = cl(0.65, 0.65, 0.65, 1.0)

# TreeView colors
cl.browser_treeview_selected_bg = cl("6E6E6E")
# ComboBox colors
cl.browser_combobox_selected_dark = cl("434A4C")
cl.browser_combobox_selected_light = cl("484848")
cl.browser_combobox_selected = cl.shade(cl.browser_combobox_selected_dark, light=cl.browser_combobox_selected_light)
# Overview colors
cl.browser_overview_header_gray = cl("929292")
cl.browser_overview_line_gray = cl("707070")

# Button hover colors
cl.browser_button_hover = cl("3A3A3A")
# Splitter colors
cl.browser_splitter_hover = cl("3B70B0")

cl.tree_browser_widget_text = cl.shade(cl("828282"), light=cl("E0E0E0"))
cl.tree_browser_widget_selected = cl.shade(cl("2497E3"), light=cl("1A91C5"))
cl.tree_browser_widget_selected_bg = cl(0.16, 0.16, 0.16, 1.0)

# ==============================================================================
# Float Constants - Extension-specific with 'browser_' prefix
# ==============================================================================
fl.browser_border_radius_small = 1.0
fl.browser_padding_frame = 8.0
fl.browser_scrollbar_size = 10.0

# ==============================================================================
# URL Constants - Extension-specific with 'browser_' prefix
# ==============================================================================
url.browser_icon_cloud_download = "${omni.kit.browser.core}/icons/cloud_download.svg"
url.browser_icon_navtree = "${omni.kit.browser.core}/icons/navtree.svg"
url.browser_icon_options = "${omni.kit.browser.core}/icons/options.svg"


UI_STYLES = {
    # ==========================================================================
    # CollapsableFrame - used in overview view
    # ==========================================================================
    "CollapsableFrame": {
        "background_color": cl.transparent,
        "secondary_color": cl.transparent,
        "padding": 0,
        "margin": 0,
    },
    # ==========================================================================
    # CollectionList - combobox for collections
    # ==========================================================================
    "CollectionList": {
        "background_color": cl.browser_background,
        "selected_color": cl.browser_combobox_selected,
        "color": cl.browser_text,
        "border_radius": fl.browser_border_radius_small,
    },
    # ==========================================================================
    # GridView - detail view and overview
    # ==========================================================================
    "GridView.Frame": {
        "background_color": cl.browser_background,
        "secondary_color": cl.browser_scrollbar,
        "border_radius": 0,
        "scrollbar_size": fl.browser_scrollbar_size,
    },
    "GridView.Grid": {"background_color": cl.transparent},
    "GridView.Item": {"background_color": cl.transparent, "color": cl.browser_text},
    "GridView.Image": {"border_width": 0},
    "GridView.Image:selected": {
        "border_width": 2,
        "border_color": cl.browser_selected,
        "border_radius": 3.0,
    },
    "GridView.Image.Placeholder": {
        "image_url": url.browser_icon_cloud_download,
        "color": cl.browser_image,
    },
    # ==========================================================================
    # Overview - overview view headers and layout
    # ==========================================================================
    "Overview.Frame": {"background_color": cl.transparent},
    "Overview.Header.Arrow": {"background_color": cl.browser_overview_header_gray},
    "Overview.Header.Label": {"color": cl.browser_overview_header_gray},
    "Overview.Header.Line": {"color": cl.browser_overview_line_gray},
    # ==========================================================================
    # SearchBar - search bar buttons and components
    # ==========================================================================
    "SearchBar.Button": {
        "background_color": cl.transparent,
        "padding": 3,
        "margin": 0,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "SearchBar.Button:hovered": {"background_color": cl.browser_button_hover},
    "SearchBar.Button:pressed": {"background_color": cl.browser_background},
    "SearchBar.Button:selected": {"background_color": cl.browser_background},
    "SearchBar.Button.Image::navigation": {
        "image_url": url.browser_icon_navtree,
        "color": cl.browser_image,
    },
    "SearchBar.Button.Image::options": {
        "image_url": url.browser_icon_options,
        "color": cl.browser_image,
    },
    "SearchBar.Button.Label": {"color": cl.browser_lighttext},
    # ==========================================================================
    # Splitter - vertical splitter between category and detail
    # ==========================================================================
    "Splitter": {"background_color": cl.transparent, "margin_width": 0},
    "Splitter:hovered": {"background_color": cl.browser_splitter_hover},
    "Splitter:pressed": {"background_color": cl.browser_splitter_hover},
    # ==========================================================================
    # TreeView - category view
    # ==========================================================================
    "TreeView": {
        "background_color": cl.transparent,
        "background_selected_color": cl.browser_treeview_selected_bg,
    },
    "TreeView:selected": {"background_color": cl.transparent, "secondary_color": cl.transparent},
    "TreeView.Frame": {
        "background_color": cl.browser_background,
        "secondary_color": cl.browser_scrollbar,
        "border_radius": 0,
        "scrollbar_size": fl.browser_scrollbar_size,
    },
    "TreeView.Branch.Line": {
        "color": cl.browser_branch,
        "background_color": cl.browser_branch,
        "margin": 0,
    },
    # + and - signs
    "TreeView.Item": {
        "color": cl.browser_expand,
        "border_width": 1.5,
        "border_color": cl.browser_expand,
    },
    "TreeView.Item:selected": {"color": cl.browser_expand},
    "TreeView.Item.Name": {"background_color": cl.transparent, "color": cl.browser_text},
    "TreeView.Item.Name:selected": {"color": cl.browser_selected},
    "TreeView.Item.Count": {"background_color": cl.transparent, "color": cl.browser_darktext},
    "TreeView.Item.Count:selected": {"color": cl.browser_text},
    "TreeView.Mark": {"color": cl.transparent, "border_width": 4},
    "TreeView.Mark:selected": {"color": cl.browser_selected, "border_width": 4},
}


# ==============================================================================
# Tree-specific style overrides for TreeBrowserWidget (public API)
# These styles override UI_STYLES when using TreeBrowserWidget
# ==============================================================================
TREE_UI_STYLES = {
    "TreeView": {"background_selected_color": cl.tree_browser_widget_selected_bg},
    "TreeView.Frame": {"padding": fl.browser_padding_frame},
    "TreeView.Item.Name": {"color": cl.tree_browser_widget_text},
    "TreeView.Item.Name:selected": {"color": cl.tree_browser_widget_selected},
    "TreeView.Item.Count:selected": {"color": cl.tree_browser_widget_text},
}

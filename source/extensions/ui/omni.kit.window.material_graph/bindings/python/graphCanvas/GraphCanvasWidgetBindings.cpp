// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "BindingsForward.h"
#include "GraphCanvasWidget.h"

using namespace omni::kit::materialGraph;

void registerGraphCanvasWidgetBindings(py::module& m)
{
    py::class_<GraphCanvasWidget, std::shared_ptr<GraphCanvasWidget>>(m, "GraphCanvasWidget")
        .def_static("create", &GraphCanvasWidget::create,
                    "Create a graph-level canvas widget that draws all nodes and connections in one pass.")
        .def("set_scene", &GraphCanvasWidget::setScene, py::arg("scene"))
        .def("clear_scene", &GraphCanvasWidget::clearScene)
        .def("set_node_selected", &GraphCanvasWidget::setNodeSelected, py::arg("stable_id"), py::arg("selected"))
        .def("set_marquee_rect", &GraphCanvasWidget::setMarqueeRect, py::arg("x0"), py::arg("y0"), py::arg("x1"),
             py::arg("y1"))
        .def("clear_marquee", &GraphCanvasWidget::clearMarquee)
        .def("set_drag_noodle", &GraphCanvasWidget::setDragNoodle, py::arg("x0"), py::arg("y0"), py::arg("x1"),
             py::arg("y1"), py::arg("color"))
        .def("clear_drag_noodle", &GraphCanvasWidget::clearDragNoodle)
        .def("set_node_position", &GraphCanvasWidget::setNodePosition, py::arg("stable_id"), py::arg("pos_x"),
             py::arg("pos_y"))
        .def("set_node_size", &GraphCanvasWidget::setNodeSize, py::arg("stable_id"), py::arg("width"), py::arg("height"))
        .def("set_view_transform", &GraphCanvasWidget::setViewTransform, py::arg("zoom"), py::arg("pan_x"),
             py::arg("pan_y"), py::arg("frame_screen_x"), py::arg("frame_screen_y"), py::arg("dpi_scale"))
        .def("hit_test", &GraphCanvasWidget::hitTest, py::arg("screen_x"), py::arg("screen_y"))
        .def(
            "get_port_anchor",
            [](GraphCanvasWidget& w, uint32_t nodeId, int portIndex, bool isInput) {
                auto a = w.getPortAnchor(nodeId, portIndex, isInput);
                return py::make_tuple(a.x, a.y);
            },
            py::arg("node_id"), py::arg("port_index"), py::arg("is_input"))
        .def_property_readonly("visible_node_count", [](GraphCanvasWidget& w) { return w.getVisibleNodeCount(); })
        .def_property_readonly(
            "visible_connection_count", [](GraphCanvasWidget& w) { return w.getVisibleConnectionCount(); })
        .def_property_readonly("view_zoom", [](GraphCanvasWidget& w) { return w.getViewZoom(); })
        .def_property_readonly("view_pan_x", [](GraphCanvasWidget& w) { return w.getViewPanX(); })
        .def_property_readonly("view_pan_y", [](GraphCanvasWidget& w) { return w.getViewPanY(); })
        .def_property_readonly("computed_width", [](GraphCanvasWidget& w) { return w.getComputedWidth(); })
        .def_property_readonly("computed_height", [](GraphCanvasWidget& w) { return w.getComputedHeight(); })
        .def_property_readonly("screen_position_x", [](GraphCanvasWidget& w) { return w.getScreenPositionX(); })
        .def_property_readonly("screen_position_y", [](GraphCanvasWidget& w) { return w.getScreenPositionY(); })
        .def_property(
            "visible", [](GraphCanvasWidget& w) { return w.isVisible(); },
            [](GraphCanvasWidget& w, bool v) { w.setVisible(v); })
        .def(
            "set_icon_pixels",
            [](GraphCanvasWidget& w, const std::string& key, int width, int height, py::bytes data) {
                std::string raw = data;
                w.setIconPixels(key, width, height, reinterpret_cast<const uint8_t*>(raw.data()), raw.size());
            },
            py::arg("key"), py::arg("width"), py::arg("height"), py::arg("data"),
            "Upload RGBA8 pixel data as an icon texture for a node type key.")
        .def(
            "set_icon_path",
            [](GraphCanvasWidget& w, const std::string& key, const std::string& path) { w.setIconPath(key, path); },
            py::arg("key"), py::arg("path"), "Set an icon file path (SVG/PNG) for a node type key. Loads asynchronously.")
        .def("set_breadcrumb", &GraphCanvasWidget::setBreadcrumb, py::arg("path"))
        .def_property_readonly(
            "breadcrumb_clicked_index", [](GraphCanvasWidget& w) { return w.getBreadcrumbClickedIndex(); })
        .def("clear_breadcrumb_clicked", &GraphCanvasWidget::clearBreadcrumbClicked)
        .def_property_readonly("breadcrumb_hovered", [](GraphCanvasWidget& w) { return w.isBreadcrumbHovered(); })
        .def_property_readonly("hover_connection_index", [](GraphCanvasWidget& w) { return w.getHoverConnectionIndex(); })
        .def_property_readonly("hover_node_id", [](GraphCanvasWidget& w) { return w.getHoverNodeId(); })
        .def_property_readonly("hover_port_index", [](GraphCanvasWidget& w) { return w.getHoverPortIndex(); })
        .def("set_tooltip_text", &GraphCanvasWidget::setTooltipText, py::arg("text"))
        .def(
            "set_style_config",
            [](GraphCanvasWidget& w, py::dict d) {
                StyleConfig c = w.getStyleConfig();
                auto f = [&](const char* k, float& v) {
                    if (d.contains(k))
                        v = d[k].cast<float>();
                };
                auto u = [&](const char* k, uint32_t& v) {
                    if (d.contains(k))
                        v = d[k].cast<uint32_t>();
                };
                auto i = [&](const char* k, int& v) {
                    if (d.contains(k))
                        v = d[k].cast<int>();
                };
                f("header_height", c.headerHeight);
                f("icon_size", c.iconSize);
                f("port_height", c.portHeight);
                f("port_radius", c.portRadius);
                f("border_radius", c.borderRadius);
                f("connection_curve", c.connectionCurve);
                f("connection_thickness", c.connectionThickness);
                f("group_indent", c.groupIndent);
                u("selection_color", c.selectionColor);
                f("selection_width", c.selectionWidth);
                f("selection_glow_pad", c.selectionGlowPad);
                u("selection_glow_alpha", c.selectionGlowAlpha);
                u("selection_outline_alpha", c.selectionOutlineAlpha);
                f("grid_minor_spacing", c.gridMinorSpacing);
                i("grid_major_every", c.gridMajorEvery);
                u("grid_minor_color", c.gridMinorColor);
                u("grid_major_color", c.gridMajorColor);
                f("lod_threshold_3", c.lodThreshold3);
                f("lod_threshold_2", c.lodThreshold2);
                f("lod_threshold_0", c.lodThreshold0);
                f("conn_min_thickness", c.connMinThickness);
                f("conn_min_thickness_lod3", c.connMinThicknessLod3);
                f("min_node_screen_w", c.minNodeScreenW);
                f("min_node_screen_h", c.minNodeScreenH);
                f("port_size_lod1", c.portSizeLod1);
                f("port_alpha_lod1", c.portAlphaLod1);
                f("port_size_lod2", c.portSizeLod2);
                f("port_alpha_lod2", c.portAlphaLod2);
                u("type_color_float4", c.typeColorFloat4);
                u("type_color_float2", c.typeColorFloat2);
                u("type_color_color", c.typeColorColor);
                u("type_color_normal", c.typeColorNormal);
                u("type_color_token", c.typeColorToken);
                u("type_color_int", c.typeColorInt);
                u("type_color_bool", c.typeColorBool);
                u("type_color_asset", c.typeColorAsset);
                u("type_color_string", c.typeColorString);
                u("type_color_default", c.typeColorDefault);
                u("header_accent_color", c.headerAccentColor);
                u("icon_badge_bg", c.iconBadgeBg);
                u("port_label_color", c.portLabelColor);
                u("port_glow_alpha", c.portGlowAlpha);
                u("connected_dot", c.connectedDot);
                f("port_glow_scale", c.portGlowScale);
                u("unresolved_port_color", c.unresolvedPortColor);
                f("interface_only_port_alpha", c.interfaceOnlyPortAlpha);
                u("closed_port_color", c.closedPortColor);
                f("closed_port_scale", c.closedPortScale);
                u("empty_port_circle", c.emptyPortCircle);
                u("empty_port_text", c.emptyPortText);
                u("backdrop_body_alpha", c.backdropBodyAlpha);
                u("backdrop_header_alpha", c.backdropHeaderAlpha);
                f("backdrop_desaturate", c.backdropDesaturate);
                f("backdrop_body_bright", c.backdropBodyBright);
                f("backdrop_header_bright", c.backdropHeaderBright);
                f("backdrop_depth_darken", c.backdropDepthDarken);
                u("text_backing_color", c.textBackingColor);
                u("backdrop_title_color", c.backdropTitleColor);
                u("backdrop_desc_color", c.backdropDescColor);
                f("bc_offset_x", c.bcOffsetX);
                f("bc_offset_y", c.bcOffsetY);
                f("bc_bar_height", c.bcBarHeight);
                f("bc_h_pad", c.bcHPad);
                f("bc_corner_radius", c.bcCornerRadius);
                f("bc_seg_h_pad", c.bcSegHPad);
                f("bc_sep_block_w", c.bcSepBlockW);
                f("bc_max_seg_w", c.bcMaxSegW);
                f("bc_max_bar_frac", c.bcMaxBarFrac);
                u("bc_bg", c.bcBg);
                u("bc_border", c.bcBorder);
                u("bc_sep_color", c.bcSepColor);
                u("bc_root_text", c.bcRootText);
                u("bc_ancestor_text", c.bcAncestorText);
                u("bc_current_text", c.bcCurrentText);
                u("bc_hover_text", c.bcHoverText);
                u("bc_hover_bg", c.bcHoverBg);
                u("bc_hover_border", c.bcHoverBorder);
                f("tooltip_delay", c.tooltipDelay);
                f("tooltip_font_size", c.tooltipFontSize);
                f("tooltip_pad", c.tooltipPad);
                f("tooltip_offset_x", c.tooltipOffsetX);
                f("tooltip_offset_y", c.tooltipOffsetY);
                f("tooltip_max_w", c.tooltipMaxW);
                f("tooltip_radius", c.tooltipRadius);
                f("tooltip_section_gap", c.tooltipSectionGap);
                f("tooltip_title_scale", c.tooltipTitleScale);
                f("tooltip_meta_scale", c.tooltipMetaScale);
                f("tooltip_desc_scale", c.tooltipDescScale);
                f("tooltip_line_spacing", c.tooltipLineSpacing);
                u("tooltip_bg", c.tooltipBg);
                u("tooltip_border", c.tooltipBorder);
                u("tooltip_text_color", c.tooltipText);
                u("tooltip_title", c.tooltipTitle);
                u("tooltip_meta", c.tooltipMeta);
                u("tooltip_desc", c.tooltipDesc);
                u("marquee_outline", c.marqueeOutline);
                u("marquee_fill", c.marqueeFill);
                f("base_font_size", c.baseFontSize);
                f("bc_font_size", c.bcFontSize);
                u("expand_icon_tint", c.expandIconTint);
                u("expand_fallback", c.expandFallback);
                f("expand_icon_size", c.expandIconSize);
                u("menu_dot_color", c.menuDotColor);
                f("menu_dot_radius", c.menuDotRadius);
                f("menu_dot_gap", c.menuDotGap);
                f("texture_preview_padding", c.texturePreviewPadding);
                f("texture_preview_corner_r", c.texturePreviewCornerR);
                u("error_color", c.errorColor);
                u("warning_color", c.warningColor);
                u("error_band_alpha", c.errorBandAlpha);
                f("error_band_width", c.errorBandWidth);
                f("error_band_corner_scale", c.errorBandCornerScale);
                u("error_aura_alpha", c.errorAuraAlpha);
                f("error_aura_width", c.errorAuraWidth);
                f("error_conn_glow_extra", c.errorConnGlowExtra);
                u("error_conn_glow_alpha", c.errorConnGlowAlpha);
                f("error_conn_outer_glow", c.errorConnOuterGlow);
                u("error_conn_outer_alpha", c.errorConnOuterAlpha);
                f("error_port_halo_width", c.errorPortHaloWidth);
                u("error_port_halo_alpha", c.errorPortHaloAlpha);
                u("error_port_ring_alpha", c.errorPortRingAlpha);
                f("error_port_ring_width", c.errorPortRingWidth);
                f("conn_hover_threshold", c.connHoverThreshold);
                f("conn_hover_outer_glow", c.connHoverOuterGlow);
                u("conn_hover_outer_alpha", c.connHoverOuterAlpha);
                f("conn_hover_glow_extra", c.connHoverGlowExtra);
                u("conn_hover_glow_alpha", c.connHoverGlowAlpha);
                u("group_icon_color", c.groupIconColor);
                u("group_label_color", c.groupLabelColor);
                f("io_active_alpha", c.ioActiveAlpha);
                f("io_other_label_alpha", c.ioOtherLabelAlpha);
                f("io_other_port_alpha", c.ioOtherPortAlpha);
                f("io_other_glow_alpha", c.ioOtherGlowAlpha);
                f("io_unused_label_alpha", c.ioUnusedLabelAlpha);
                f("io_unused_port_alpha", c.ioUnusedPortAlpha);
                f("io_unused_glow_alpha", c.ioUnusedGlowAlpha);
                w.setStyleConfig(c);
            },
            py::arg("config"))
        .def("start_rename", &GraphCanvasWidget::startRename, py::arg("stable_id"), py::arg("current_name"))
        .def("has_rename_result", &GraphCanvasWidget::hasRenameResult)
        .def("consume_rename_result",
             [](GraphCanvasWidget& w) {
                 auto r = w.consumeRenameResult();
                 return py::make_tuple(r.first, r.second);
             })
        .def_property_readonly("is_renaming", [](GraphCanvasWidget& w) { return w.isRenaming(); })
        .def("start_desc_edit", &GraphCanvasWidget::startDescEdit, py::arg("stable_id"), py::arg("current_desc"))
        .def("has_desc_edit_result", &GraphCanvasWidget::hasDescEditResult)
        .def("consume_desc_edit_result",
             [](GraphCanvasWidget& w) {
                 auto r = w.consumeDescEditResult();
                 return py::make_tuple(r.first, r.second);
             })
        .def_property_readonly("is_desc_editing", [](GraphCanvasWidget& w) { return w.isDescEditing(); });
}

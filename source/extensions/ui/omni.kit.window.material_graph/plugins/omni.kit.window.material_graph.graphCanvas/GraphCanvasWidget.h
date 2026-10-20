// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// GraphCanvasWidget: the main ImGui-style canvas widget that renders the
// entire material graph (nodes, connections, backdrops, breadcrumb, tooltips)
// in a single draw pass.  StyleConfig holds all tunable visual parameters.
// The widget is created via Python bindings and driven by GraphCanvasView.

#pragma once

#include "SceneData.h"

#include <carb/imgui/ImGui.h>
#include <omni/ui/Widget.h>
#include <omni/ui/ContainerScope.h>
#include <omni/ui/ImageProvider/ByteImageProvider.h>
#include <omni/ui/ImageProvider/RasterImageProvider.h>
#include <omni/ui/ImageProvider/VectorImageProvider.h>

#include <memory>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace omni
{
namespace kit
{
namespace materialGraph
{

/// Configurable style parameters for the graph canvas renderer.
/// All values have defaults matching the original hardcoded aesthetics.
/// Push from Python via setStyleConfig() to tune without C++ rebuilds.
struct StyleConfig
{
    // ---- Node layout ----
    float headerHeight = 24.0f; // Node header strip height (canvas units)
    float iconSize = 38.0f; // Icon badge size in header
    float portHeight = 22.0f; // Height of each port row
    float portRadius = 5.0f; // Port circle radius
    float borderRadius = 10.0f; // Node corner radius
    float connectionCurve = 60.0f; // Bezier curve control point offset
    float connectionThickness = 2.8f; // Connection line thickness
    float groupIndent = 15.0f; // Indent per port group nesting level

    // ---- Selection ----
    uint32_t selectionColor = 0xD0904A; // Selection accent (RGB, alpha applied separately)
    float selectionWidth = 2.0f; // Selection outline stroke width
    float selectionGlowPad = 2.0f; // Extra padding for selection glow
    uint32_t selectionGlowAlpha = 0x14; // Selection glow alpha
    uint32_t selectionOutlineAlpha = 0xC0; // Selection outline alpha

    // ---- Grid ----
    float gridMinorSpacing = 32.0f; // Minor grid line spacing (canvas units)
    int gridMajorEvery = 5; // Major line drawn every N minor lines
    uint32_t gridMinorColor = 0x08FFFFFF; // Minor grid line color+alpha
    uint32_t gridMajorColor = 0x12FFFFFF; // Major grid line color+alpha

    // ---- LOD thresholds (effScale) ----
    float lodThreshold3 = 0.18f; // Below: minimal rectangles only
    float lodThreshold2 = 0.35f; // Below: no text, reduced ports
    float lodThreshold0 = 0.60f; // At/above: full detail

    // ---- Connection min thickness per LOD ----
    float connMinThickness = 1.0f; // Normal min connection thickness
    float connMinThicknessLod3 = 1.5f; // Min thickness at LOD 3

    // ---- Min node screen size (LOD 2/3) ----
    float minNodeScreenW = 32.0f; // Min on-screen node width (pixels)
    float minNodeScreenH = 20.0f; // Min on-screen node height (pixels)

    // ---- Port LOD scaling ----
    float portSizeLod1 = 0.80f; // Port radius multiplier at LOD 1
    float portAlphaLod1 = 0.65f; // Port alpha multiplier at LOD 1
    float portSizeLod2 = 0.60f; // Port radius multiplier at LOD 2
    float portAlphaLod2 = 0.40f; // Port alpha multiplier at LOD 2

    // ---- Type colors (ABGR) ----
    uint32_t typeColorFloat4 = 0xFF66AAAA;
    uint32_t typeColorFloat2 = 0xFFAAAA66;
    uint32_t typeColorColor = 0xFFAAAA44; // Teal (moved from green to avoid conflict with structural green)
    uint32_t typeColorNormal = 0xFFCC8844;
    uint32_t typeColorToken = 0xFFCCCC44;
    uint32_t typeColorInt = 0xFF6666CC;
    uint32_t typeColorBool = 0xFFCC6666;
    uint32_t typeColorAsset = 0xFFCC66CC;
    uint32_t typeColorString = 0xFFCCCCCC;
    uint32_t typeColorDefault = 0xFF66AAAA;

    // ---- Node colors ----
    uint32_t headerAccentColor = 0xFF479960; // Header accent bar / separator (ABGR muted structural green)
    uint32_t iconBadgeBg = 0xFF424242; // Icon badge background
    uint32_t portLabelColor = 0xFFD4D4D4; // Port text label color
    uint32_t portGlowAlpha = 0x18; // Port outer glow alpha (low byte)
    uint32_t connectedDot = 0xC8FFFFFF; // Connected port inner dot
    float portGlowScale = 1.3f; // Port glow radius multiplier

    // ---- Polymorphic unresolved port ----
    uint32_t unresolvedPortColor = 0xFFFFFFFF; // White for ambiguous ports

    // ---- Interface-only port ----
    float interfaceOnlyPortAlpha = 0.50f; // Brightness multiplier for interfaceOnly ports

    // ---- InputNode io_state emphasis (per-context port visibility) ----
    float ioActiveAlpha = 1.00f; // ACTIVE_IN_CURRENT label/port/glow
    float ioOtherLabelAlpha = 0.60f; // USED_IN_OTHER label
    float ioOtherPortAlpha = 0.65f; // USED_IN_OTHER port shape
    float ioOtherGlowAlpha = 0.55f; // USED_IN_OTHER glow
    float ioUnusedLabelAlpha = 0.35f; // UNUSED label
    float ioUnusedPortAlpha = 0.40f; // UNUSED port shape
    float ioUnusedGlowAlpha = 0.30f; // UNUSED glow

    // ---- Error/warning visualization (2-pass 9-slice system) ----
    uint32_t errorColor = 0xFF4040A0; // Muted desaturated error red (ABGR)
    uint32_t warningColor = 0xFF30A8D0; // Muted yellow/amber (ABGR)
    uint32_t errorBandAlpha = 0x84; // Pass A: contour band alpha (primary signal)
    float errorBandWidth = 1.5f; // Pass A: contour band extent beyond node (canvas px)
    float errorBandCornerScale = 0.6f; // Pass A: corner radius growth factor (< 1 = tighter corners)
    uint32_t errorAuraAlpha = 0x20; // Pass B: outer aura alpha (secondary signal)
    float errorAuraWidth = 4.5f; // Pass B: outer aura extent beyond contour band (canvas px)
    float errorConnGlowExtra = 3.0f; // Inner glow extra thickness for invalid connections
    uint32_t errorConnGlowAlpha = 0x30; // Inner glow alpha for invalid connections
    float errorConnOuterGlow = 5.0f; // Outer glow extra thickness for invalid connections
    uint32_t errorConnOuterAlpha = 0x18; // Outer glow alpha for invalid connections
    float errorPortHaloWidth = 3.0f; // Halo glow extent beyond port circle
    uint32_t errorPortHaloAlpha = 0x30; // Halo glow fill alpha
    uint32_t errorPortRingAlpha = 0x80; // Crisp ring stroke alpha on error ports
    float errorPortRingWidth = 1.0f; // Ring stroke width on error ports

    // ---- Connection hover highlight (uses selectionColor) ----
    float connHoverThreshold = 6.0f; // Max screen-pixel distance to count as hovering a noodle
    float connHoverOuterGlow = 5.0f; // Outer glow extra thickness for hovered connection
    uint32_t connHoverOuterAlpha = 0x18; // Outer glow alpha
    float connHoverGlowExtra = 3.0f; // Inner glow extra thickness
    uint32_t connHoverGlowAlpha = 0x30; // Inner glow alpha

    // ---- Group UI (desaturated structural green, subdued vs separator) ----
    uint32_t groupIconColor = 0xFF689078; // Expand +/- icon (ABGR grey-green, slightly brighter for affordance)
    uint32_t groupLabelColor = 0xFF608068; // Group label text (ABGR grey-green, subdued)

    // ---- Texture preview (below node body) ----
    float texturePreviewPadding = 6.0f; // Padding around preview image
    float texturePreviewCornerR = 4.0f; // Corner radius for preview

    // ---- Closed node ----
    uint32_t closedPortColor = 0xB0999999; // Port dots when node is closed
    float closedPortScale = 0.75f; // Closed port radius multiplier

    // ---- Empty (Add Port) ----
    uint32_t emptyPortCircle = 0x48777777; // Empty port circle color
    uint32_t emptyPortText = 0x48666666; // "Add Port" text color

    // ---- Backdrop ----
    uint32_t backdropBodyAlpha = 0x28; // Body fill alpha
    uint32_t backdropHeaderAlpha = 0x58; // Header strip alpha
    float backdropDesaturate = 0.35f; // Color desaturation factor
    float backdropBodyBright = 0.25f; // Body color brightness multiplier
    float backdropHeaderBright = 0.40f; // Header color brightness multiplier
    float backdropDepthDarken = 0.06f; // Darken per stacking depth level
    uint32_t textBackingColor = 0xB0202020; // Text backing panel color
    uint32_t backdropTitleColor = 0xFFE8E8E8; // Backdrop title text color
    uint32_t backdropDescColor = 0xB0CCCCCC; // Backdrop description text color

    // ---- Breadcrumb bar ----
    float bcOffsetX = 12.0f; // X offset from viewport edge
    float bcOffsetY = 10.0f; // Y offset from viewport edge
    float bcBarHeight = 32.0f; // Bar height (screen pixels)
    float bcHPad = 10.0f; // Horizontal padding
    float bcCornerRadius = 6.0f; // Bar corner radius
    float bcSegHPad = 6.0f; // Segment horizontal padding
    float bcSepBlockW = 13.0f; // Separator block width
    float bcMaxSegW = 160.0f; // Max segment text width
    float bcMaxBarFrac = 0.4f; // Max bar width as viewport fraction
    uint32_t bcBg = 0xB4181818; // Background color
    uint32_t bcBorder = 0x40606060; // Border color
    uint32_t bcSepColor = 0x73AAAAAA; // Separator chevron color
    uint32_t bcRootText = 0xB3DDDDDD; // Root segment text
    uint32_t bcAncestorText = 0xB3CCCCCC; // Ancestor segment text
    uint32_t bcCurrentText = 0xFFEEEEEE; // Current segment text
    uint32_t bcHoverText = 0xE0DDDDDD; // Hovered segment text
    uint32_t bcHoverBg = 0x1E606060; // Hover backing fill
    uint32_t bcHoverBorder = 0x0C888888; // Hover backing border

    // ---- Tooltip ----
    float tooltipDelay = 0.45f;
    float tooltipFontSize = 13.0f;
    float tooltipPad = 12.0f;
    float tooltipOffsetX = 10.0f;
    float tooltipOffsetY = 6.0f;
    float tooltipMaxW = 340.0f;
    float tooltipRadius = 6.0f;
    float tooltipSectionGap = 8.0f;
    float tooltipTitleScale = 1.22f;
    float tooltipMetaScale = 0.98f;
    float tooltipDescScale = 1.08f;
    float tooltipLineSpacing = 1.1f;
    uint32_t tooltipBg = 0xEE232428;
    uint32_t tooltipBorder = 0x18606060;
    uint32_t tooltipTitle = 0xFFE6E6E6;
    uint32_t tooltipMeta = 0xFF9A9A9A;
    uint32_t tooltipDesc = 0xFFBDBDBD;
    uint32_t tooltipText = 0xFFDDDDDD;

    // ---- Marquee selection ----
    uint32_t marqueeOutline = 0xFFE0A020; // Marquee border color
    uint32_t marqueeFill = 0x20E0A020; // Marquee fill color

    // ---- Font ----
    float baseFontSize = 14.0f; // Base node text font size
    float bcFontSize = 14.0f; // Breadcrumb text font size

    // ---- Expansion icon ----
    uint32_t expandIconTint = 0xFFC8C8C8; // SVG expansion icon tint
    uint32_t expandFallback = 0xFFC0C0C0; // Fallback line-drawn icon color
    float expandIconSize = 12.0f; // Expansion icon render size

    // ---- Menu dots ----
    uint32_t menuDotColor = 0xFF909090; // Node menu "..." dot color
    float menuDotRadius = 1.5f; // Menu dot circle radius
    float menuDotGap = 4.0f; // Gap between menu dots
};

/// Single native widget that draws an entire material graph (nodes, ports,
/// connections) in one rendering pass.  Replaces the per-node-widget
/// architecture (Strategy B+) with a graph-level canvas renderer.
///
/// Scene data is pushed from Python as a compact GraphScene snapshot.
/// The widget performs visible-set culling, LOD, and hit testing natively.
class GraphCanvasWidget : public omni::ui::Widget
{
public:
    GraphCanvasWidget();
    ~GraphCanvasWidget() override;

    static std::shared_ptr<GraphCanvasWidget> create();

    // ---- Style configuration ----
    void setStyleConfig(const StyleConfig& config)
    {
        m_style = config;
    }
    const StyleConfig& getStyleConfig() const
    {
        return m_style;
    }

    // ---- Scene management ----
    void setScene(const GraphScene& scene);
    const GraphScene& getScene() const
    {
        return m_scene;
    }
    void clearScene();

    // ---- View transform (set from Python when CanvasFrame pan/zoom changes) ----
    void setViewTransform(float zoom, float panX, float panY, float frameScreenX, float frameScreenY, float dpiScale);

    float getViewZoom() const
    {
        return m_zoom;
    }
    float getViewPanX() const
    {
        return m_panX;
    }
    float getViewPanY() const
    {
        return m_panY;
    }

    // ---- Hit testing ----
    HitResult hitTest(float screenX, float screenY) const;

    // ---- Anchor positions for connection drag compatibility ----
    struct AnchorPoint
    {
        float x = 0.0f;
        float y = 0.0f;
    };
    AnchorPoint getPortAnchor(uint32_t nodeId, int portIndex, bool isInput) const;

    // ---- Selection (O(1) per node, no scene rebuild) ----
    void setNodeSelected(uint32_t stableId, bool selected);

    // ---- Marquee rectangle (canvas coords, drawn on top of everything) ----
    void setMarqueeRect(float x0, float y0, float x1, float y1);
    void clearMarquee();

    // ---- Drag noodle (canvas coords, Bezier curve during connection drag) ----
    void setDragNoodle(float x0, float y0, float x1, float y1, uint32_t color);
    void clearDragNoodle();

    // ---- Node position update (O(1), no scene rebuild) ----
    void setNodePosition(uint32_t stableId, float posX, float posY);

    // ---- Node size update (O(1), for live backdrop resize) ----
    void setNodeSize(uint32_t stableId, float width, float height);

    // ---- Icon textures (keyed by node type / shader identifier) ----
    void setIconPixels(const std::string& key, int w, int h, const uint8_t* rgba, size_t len);
    void setIconPath(const std::string& key, const std::string& path);
    void* getIconTexture(const std::string& key) const;
    void updateIconProviders();

    // ---- Stats ----
    int getVisibleNodeCount() const
    {
        return m_visibleNodeCount;
    }
    int getVisibleConnectionCount() const
    {
        return m_visibleConnectionCount;
    }

    // ---- Breadcrumb (rendered in draw pass, on top of all nodes) ----
    void setBreadcrumb(const std::vector<std::string>& path);
    int getBreadcrumbClickedIndex() const
    {
        return m_bcClickedIndex;
    }
    void clearBreadcrumbClicked()
    {
        m_bcClickedIndex = -1;
    }
    bool isBreadcrumbHovered() const
    {
        return m_bcHovered;
    }

    // ---- Connection hover (C++ distance-to-Bezier, Python reads index) ----
    int getHoverConnectionIndex() const
    {
        return m_hoverConnectionIndex;
    }

    // ---- Hover tooltip (hybrid: C++ detects hover, Python pushes text) ----
    int getHoverNodeId() const
    {
        return m_hoverNodeId;
    }
    int getHoverPortIndex() const
    {
        return m_hoverPortIndex;
    }
    void setTooltipText(const std::string& text)
    {
        m_tooltipText = text;
    }

    // ---- Inline node rename ----
    void startRename(uint32_t stableId, const std::string& currentName);
    bool isRenaming() const
    {
        return m_renameActive;
    }
    bool hasRenameResult() const
    {
        return m_renameCommitted;
    }
    std::pair<uint32_t, std::string> consumeRenameResult();

    // ---- Inline backdrop description edit ----
    void startDescEdit(uint32_t stableId, const std::string& currentDesc);
    bool isDescEditing() const
    {
        return m_descEditActive;
    }
    bool hasDescEditResult() const
    {
        return m_descEditCommitted;
    }
    std::pair<uint32_t, std::string> consumeDescEditResult();

protected:
    void _drawContent(float elapsedTime) override;

private:
    StyleConfig m_style;
    GraphScene m_scene;
    std::unordered_map<uint32_t, size_t> m_nodeIdToIndex;

    // Icon texture cache
    std::unordered_map<std::string, std::shared_ptr<omni::ui::ImageProvider>> m_iconProviders;
    std::unordered_map<std::string, void*> m_iconTextures;

    // 9-slice rounded-rect textures (background + shadow)
    std::shared_ptr<omni::ui::ByteImageProvider> m_bgTexProvider;
    std::shared_ptr<omni::ui::ByteImageProvider> m_shadowTexProvider;
    void* m_bgTexId = nullptr;
    void* m_shadowTexId = nullptr;
    bool m_bgTexCreated = false;
    static constexpr int kBgTexSize = 128;
    static constexpr int kBgTexCorner = 10;
    void ensureBgTexture();
    void draw9Slice(carb::imgui::ImGui* imgui,
                    carb::imgui::DrawList* dl,
                    void* texId,
                    float x,
                    float y,
                    float w,
                    float h,
                    float cornerPx,
                    uint32_t col) const;

    // Pre-built fonts from IGlyphManager (sorted by pixel size, ascending)
    std::vector<std::pair<float, carb::imgui::Font*>> m_fonts;
    bool m_fontsLoaded = false;
    void ensureFonts();
    std::pair<carb::imgui::Font*, float> pickFont(float desiredSize) const;

    // View transform (set from Python, matches CanvasFrame state)
    float m_zoom = 1.0f;
    float m_panX = 0.0f;
    float m_panY = 0.0f;
    float m_frameScreenX = 0.0f;
    float m_frameScreenY = 0.0f;
    float m_dpiScale = 1.0f;

    mutable int m_visibleNodeCount = 0;
    mutable int m_visibleConnectionCount = 0;

    bool m_marqueeActive = false;
    float m_marqueeX0 = 0.0f;
    float m_marqueeY0 = 0.0f;
    float m_marqueeX1 = 0.0f;
    float m_marqueeY1 = 0.0f;

    bool m_noodleActive = false;
    float m_noodleX0 = 0.0f;
    float m_noodleY0 = 0.0f;
    float m_noodleX1 = 0.0f;
    float m_noodleY1 = 0.0f;
    uint32_t m_noodleColor = 0xFFAAAAAA;

    // Inline rename state
    bool m_renameActive = false;
    uint32_t m_renameNodeId = 0;
    char m_renameBuf[256] = {};
    bool m_renameFocusSet = false;
    bool m_renameCommitted = false;
    std::string m_renameResult;
    uint32_t m_renameResultNodeId = 0;

    // Inline description edit state
    bool m_descEditActive = false;
    uint32_t m_descEditNodeId = 0;
    char m_descEditBuf[4096] = {};
    bool m_descEditFocusSet = false;
    bool m_descEditCommitted = false;
    std::string m_descEditResult;
    uint32_t m_descEditResultNodeId = 0;

    // Connection hover state (index into m_scene.connections, -1 = none)
    int m_hoverConnectionIndex = -1;

    // Hover tooltip state
    int m_hoverNodeId = -1;
    int m_hoverPortIndex = -1;
    float m_hoverTime = 0.0f;
    static constexpr float kTooltipDelay = 0.45f;
    std::string m_tooltipText;
    float m_tipAnchorX = 0.0f;
    float m_tipAnchorY = 0.0f;
    bool m_tipAnchorRight = true;

    // Breadcrumb state
    std::vector<std::string> m_breadcrumbs;
    int m_bcClickedIndex = -1;
    bool m_bcHovered = false;
    bool m_bcPrevMouseDown = false;
    bool m_bcEllipsisOpen = false;
    float m_bcPopupX = 0.0f;
    float m_bcPopupY = 0.0f;
    std::vector<std::pair<int, std::string>> m_bcHiddenSegments;
    void drawBreadcrumb(carb::imgui::ImGui* imgui, carb::imgui::DrawList* dl, float dpiScale);

    // Layout constants
    static constexpr float kHeaderHeight = 24.0f;
    static constexpr float kIconSize = 38.0f;
    static constexpr float kBodyTopInset = 8.0f;
    static constexpr float kPortHeight = 22.0f;
    static constexpr float kPortRadius = 5.0f;
    static constexpr float kPortMargin = 8.0f;
    static constexpr float kLabelMarginLeft = 20.0f;
    static constexpr float kLabelMarginRight = 20.0f;
    static constexpr float kBorderRadius = 10.0f;
    static constexpr float kBorderWidth = 1.5f;
    static constexpr float kSelectionPad = 3.5f;
    static constexpr float kSelectionWidth = 3.0f;
    static constexpr float kGroupIndent = 15.0f;
    static constexpr float kExpandIconSize = 8.0f;
    static constexpr float kConnectionCurve = 60.0f;
    static constexpr float kConnectionThickness = 2.8f;
    static constexpr int kBezierSegments = 48;

    // Coordinate transforms: canvas → screen pixel
    float canvasToScreenX(float cx) const;
    float canvasToScreenY(float cy) const;
    float screenToCanvasX(float sx) const;
    float screenToCanvasY(float sy) const;

    // Drawing helpers
    void drawNode(carb::imgui::ImGui* imgui,
                  carb::imgui::DrawList* dl,
                  const SceneNodeEntry& node,
                  float sx,
                  float sy,
                  float sw,
                  float sh,
                  float effScale);
    void drawBackdrop(carb::imgui::ImGui* imgui,
                      carb::imgui::DrawList* dl,
                      const SceneNodeEntry& node,
                      float sx,
                      float sy,
                      float sw,
                      float sh,
                      float effScale);
    void drawNodeHeader(carb::imgui::ImGui* imgui,
                        carb::imgui::DrawList* dl,
                        float x,
                        float y,
                        float w,
                        float h,
                        float effScale,
                        const NodeData& data,
                        uint32_t stableId = 0);
    void drawNodePort(carb::imgui::ImGui* imgui,
                      carb::imgui::DrawList* dl,
                      const PortData& port,
                      float x,
                      float portY,
                      float w,
                      float effScale,
                      bool drawText) const;
    void drawInputNodePort(carb::imgui::ImGui* imgui,
                           carb::imgui::DrawList* dl,
                           const PortData& port,
                           float x,
                           float portY,
                           float w,
                           float rowHeight,
                           float effScale,
                           bool drawText) const;
    void drawGrid(carb::imgui::ImGui* imgui, carb::imgui::DrawList* dl, float originX, float originY, float effScale) const;
    void drawConnection(carb::imgui::ImGui* imgui,
                        carb::imgui::DrawList* dl,
                        float x0,
                        float y0,
                        float x1,
                        float y1,
                        uint32_t color,
                        float thickness,
                        float curve) const;
    void updateAndDrawTooltip(carb::imgui::ImGui* imgui,
                              carb::imgui::DrawList* dl,
                              float originX,
                              float originY,
                              float effScale,
                              float elapsedTime);

    float nodeHeight(const NodeData& data) const;
    bool isRectInViewport(float x, float y, float w, float h, float vpX, float vpY, float vpW, float vpH) const;

    // Port anchor in screen coords (legacy, uses stale transform)
    std::pair<float, float> portScreenPosition(const SceneNodeEntry& node, int portIndex, bool isInput, float effScale) const;

    // Port anchor using live origin (from widget's CanvasFrame position)
    std::pair<float, float> portScreenPos(
        const SceneNodeEntry& node, int portIndex, bool isInput, float originX, float originY, float effScale) const;
};

} // namespace materialGraph
} // namespace kit
} // namespace omni

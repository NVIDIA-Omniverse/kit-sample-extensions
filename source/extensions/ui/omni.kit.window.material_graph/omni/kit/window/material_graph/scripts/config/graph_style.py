"""Centralised style configuration for the native graph canvas renderer.

All values here map 1:1 to the C++ ``StyleConfig`` struct in
``GraphCanvasWidget.h``.  They are pushed to the C++ widget on creation
via ``canvas_widget.set_style_config(GraphStyle.to_dict())``.

To tune the graph appearance, edit values here — no C++ rebuild required.
"""


class GraphStyle:
    """Configurable aesthetic constants for the graph canvas."""

    # ---- Node layout (canvas units) ----------------------------------------
    HEADER_HEIGHT = 24.0  # Height of the node header strip
    ICON_SIZE = 38.0  # Icon badge size inside the header
    PORT_HEIGHT = 22.0  # Height of each port row
    PORT_RADIUS = 5.0  # Radius of port circles
    BORDER_RADIUS = 10.0  # Node corner radius
    CONNECTION_CURVE = 60.0  # Bezier curve control-point offset for connections
    CONNECTION_THICKNESS = 2.8  # Connection line thickness
    GROUP_INDENT = 15.0  # Indent per port group nesting level

    # ---- Selection ---------------------------------------------------------
    SELECTION_COLOR = 0xD0904A  # Selection accent RGB (alpha applied separately)
    SELECTION_WIDTH = 2.0  # Selection outline stroke width
    SELECTION_GLOW_PAD = 2.0  # Extra padding for selection glow halo
    SELECTION_GLOW_ALPHA = 0x14  # Glow fill alpha
    SELECTION_OUTLINE_ALPHA = 0xC0  # Outline stroke alpha

    # ---- Grid --------------------------------------------------------------
    GRID_MINOR_SPACING = 32.0  # Canvas-unit spacing for minor grid lines
    GRID_MAJOR_EVERY = 5  # Draw a major line every N minor lines
    GRID_MINOR_COLOR = 0x08FFFFFF  # Minor grid line color (ABGR)
    GRID_MAJOR_COLOR = 0x12FFFFFF  # Major grid line color (ABGR)

    # ---- LOD thresholds (effScale = zoom * dpiScale) -----------------------
    LOD_THRESHOLD_3 = 0.18  # Below: minimal rectangles only, no ports/text
    LOD_THRESHOLD_2 = 0.35  # Below: reduced ports, no text
    LOD_THRESHOLD_0 = 0.60  # At/above: full detail (text, dots, labels)

    # ---- Connection min thickness ------------------------------------------
    CONN_MIN_THICKNESS = 1.0  # Normal min connection thickness (screen px)
    CONN_MIN_THICKNESS_LOD3 = 1.5  # Min thickness at LOD 3

    # ---- Min node screen size (LOD 2/3 clamp) -----------------------------
    MIN_NODE_SCREEN_W = 32.0  # Min on-screen node width (px)
    MIN_NODE_SCREEN_H = 20.0  # Min on-screen node height (px)

    # ---- Port LOD scaling --------------------------------------------------
    PORT_SIZE_LOD1 = 0.80  # Port radius multiplier at LOD 1
    PORT_ALPHA_LOD1 = 0.65  # Port alpha multiplier at LOD 1
    PORT_SIZE_LOD2 = 0.60  # Port radius multiplier at LOD 2
    PORT_ALPHA_LOD2 = 0.40  # Port alpha multiplier at LOD 2

    # ---- Type colors (ABGR) — used for accent lines, port circles ---------
    TYPE_COLOR_FLOAT4 = 0xFF66AAAA  # float4, float3
    TYPE_COLOR_FLOAT2 = 0xFFAAAA66  # float2, float
    TYPE_COLOR_COLOR = 0xFFAAAA44  # color4f, color3f (teal, not green)
    TYPE_COLOR_NORMAL = 0xFFCC8844  # normal3f
    TYPE_COLOR_TOKEN = 0xFFCCCC44  # token
    TYPE_COLOR_INT = 0xFF6666CC  # int
    TYPE_COLOR_BOOL = 0xFFCC6666  # bool
    TYPE_COLOR_ASSET = 0xFFCC66CC  # asset
    TYPE_COLOR_STRING = 0xFFCCCCCC  # string
    TYPE_COLOR_DEFAULT = 0xFF66AAAA  # fallback for unknown types

    # ---- Node colors -------------------------------------------------------
    HEADER_ACCENT_COLOR = 0xFF479960  # Header accent bar / separator (ABGR muted structural green)
    ICON_BADGE_BG = 0xFF383838  # Icon badge background fill
    PORT_LABEL_COLOR = 0xFFD4D4D4  # Port name text color
    PORT_GLOW_ALPHA = 0x18  # Outer glow alpha for port circles
    CONNECTED_DOT = 0xC8FFFFFF  # Inner dot for connected ports
    PORT_GLOW_SCALE = 1.3  # Port glow radius multiplier

    # ---- Polymorphic unresolved port ----------------------------------------
    UNRESOLVED_PORT_COLOR = 0xFF999999  # White for ambiguous/unresolved ports

    # ---- Interface-only port ------------------------------------------------
    INTERFACE_ONLY_PORT_ALPHA = 0.25  # Brightness multiplier for interfaceOnly ports

    # ---- Closed node -------------------------------------------------------
    CLOSED_PORT_COLOR = 0xB0999999  # Port dots when node is fully closed
    CLOSED_PORT_SCALE = 0.75  # Closed port radius multiplier

    # ---- Empty port (Add Port placeholder) ---------------------------------
    EMPTY_PORT_CIRCLE = 0xFF666666  # Empty port circle color
    EMPTY_PORT_TEXT = 0xFF666666  # "Add Port" text color

    # ---- Error/warning visualization (2-pass 9-slice system) ---------------
    ERROR_COLOR = 0xFF4040A0  # Muted desaturated error red (ABGR)
    WARNING_COLOR = 0xFF30A8D0  # Muted yellow/amber (ABGR)
    ERROR_BAND_ALPHA = 0x84  # Pass A: contour band alpha (primary signal)
    ERROR_BAND_WIDTH = 1.5  # Pass A: contour band extent beyond node (canvas px)
    ERROR_BAND_CORNER_SCALE = 0.6  # Pass A: corner radius growth factor
    ERROR_AURA_ALPHA = 0x20  # Pass B: outer aura alpha (secondary signal)
    ERROR_AURA_WIDTH = 4.5  # Pass B: outer aura extent beyond contour band (canvas px)
    ERROR_CONN_GLOW_EXTRA = 3.0  # Inner glow extra thickness for invalid connections
    ERROR_CONN_GLOW_ALPHA = 0x30  # Inner glow alpha for invalid connections
    ERROR_CONN_OUTER_GLOW = 5.0  # Outer glow extra thickness for invalid connections
    ERROR_CONN_OUTER_ALPHA = 0x18  # Outer glow alpha for invalid connections
    ERROR_PORT_HALO_WIDTH = 3.0  # Halo glow extent beyond port circle
    ERROR_PORT_HALO_ALPHA = 0x30  # Halo glow fill alpha
    ERROR_PORT_RING_ALPHA = 0x80  # Crisp ring stroke alpha on error ports
    ERROR_PORT_RING_WIDTH = 1.0  # Ring stroke width on error ports

    # ---- Group UI (desaturated structural green, subdued vs separator) ------
    GROUP_ICON_COLOR = 0xFF689078  # Expand +/- icon (ABGR grey-green, slightly brighter for affordance)
    GROUP_LABEL_COLOR = 0xFF608068  # Group label text (ABGR grey-green, subdued)

    # ---- Texture preview (below node body) ---------------------------------
    TEXTURE_PREVIEW_PADDING = 6.0  # Padding around preview image (canvas units)
    TEXTURE_PREVIEW_CORNER_R = 4.0  # Corner radius for preview image clipping

    # ---- Backdrop ----------------------------------------------------------
    BACKDROP_BODY_ALPHA = 0x28  # Body fill alpha
    BACKDROP_HEADER_ALPHA = 0x58  # Header strip fill alpha
    BACKDROP_DESATURATE = 0.35  # Color desaturation factor
    BACKDROP_BODY_BRIGHT = 0.25  # Body color brightness multiplier
    BACKDROP_HEADER_BRIGHT = 0.40  # Header color brightness multiplier
    BACKDROP_DEPTH_DARKEN = 0.06  # Darken per stacking depth level
    TEXT_BACKING_COLOR = 0xB0202020  # Opaque backing panel behind text
    BACKDROP_TITLE_COLOR = 0xFFE8E8E8  # Backdrop title text color
    BACKDROP_DESC_COLOR = 0xB0CCCCCC  # Backdrop description text color

    # ---- Breadcrumb bar ----------------------------------------------------
    BC_OFFSET_X = 12.0  # X offset from viewport top-left
    BC_OFFSET_Y = 10.0  # Y offset from viewport top-left
    BC_BAR_HEIGHT = 32.0  # Bar height (screen pixels)
    BC_H_PAD = 10.0  # Horizontal padding inside bar
    BC_CORNER_RADIUS = 6.0  # Bar corner radius
    BC_SEG_H_PAD = 6.0  # Segment horizontal padding
    BC_SEP_BLOCK_W = 13.0  # Separator block width
    BC_MAX_SEG_W = 160.0  # Max segment text width before truncation
    BC_MAX_BAR_FRAC = 0.4  # Max bar width as fraction of viewport
    BC_BG = 0xB4181818  # Background color
    BC_BORDER = 0x40606060  # Border color
    BC_SEP_COLOR = 0x73AAAAAA  # Separator chevron color
    BC_ROOT_TEXT = 0xB3DDDDDD  # Root segment text color
    BC_ANCESTOR_TEXT = 0xB3CCCCCC  # Ancestor segment text color
    BC_CURRENT_TEXT = 0xFFEEEEEE  # Current segment text color
    BC_HOVER_TEXT = 0xE0DDDDDD  # Hovered segment text color
    BC_HOVER_BG = 0x1E606060  # Hover backing fill
    BC_HOVER_BORDER = 0x0C888888  # Hover backing border

    # ---- Tooltip -----------------------------------------------------------
    TOOLTIP_DELAY = 0.45  # Hover delay before showing (seconds)
    TOOLTIP_FONT_SIZE = 13.0  # Base tooltip font size
    TOOLTIP_PAD = 12.0  # Internal padding
    TOOLTIP_OFFSET_X = 10.0  # X offset from anchor point
    TOOLTIP_OFFSET_Y = 6.0  # Y offset from anchor point
    TOOLTIP_MAX_W = 340.0  # Max content width before word-wrap
    TOOLTIP_RADIUS = 6.0  # Corner radius
    TOOLTIP_SECTION_GAP = 8.0  # Vertical gap at section separators
    TOOLTIP_TITLE_SCALE = 1.22  # Font scale for title line
    TOOLTIP_META_SCALE = 0.98  # Font scale for metadata lines
    TOOLTIP_DESC_SCALE = 1.08  # Font scale for description lines
    TOOLTIP_LINE_SPACING = 1.1  # Vertical line-spacing multiplier
    TOOLTIP_BG = 0xEE232428  # Background color (ABGR)
    TOOLTIP_BORDER = 0x18606060  # Border color (ABGR)
    TOOLTIP_TEXT_COLOR = 0xFFDDDDDD  # Fallback text color
    TOOLTIP_TITLE = 0xFFE6E6E6  # Title text color
    TOOLTIP_META = 0xFF9A9A9A  # Metadata text color
    TOOLTIP_DESC = 0xFFBDBDBD  # Description text color

    # ---- Marquee selection -------------------------------------------------
    MARQUEE_OUTLINE = 0xFFE0A020  # Marquee border color
    MARQUEE_FILL = 0x20E0A020  # Marquee fill color

    # ---- Font --------------------------------------------------------------
    BASE_FONT_SIZE = 14.0  # Base node text font size
    BC_FONT_SIZE = 14.0  # Breadcrumb text font size

    # ---- Expansion icon ----------------------------------------------------
    EXPAND_ICON_TINT = 0xFFC8C8C8  # SVG expansion icon tint
    EXPAND_FALLBACK = 0xFFC0C0C0  # Fallback line-drawn icon color
    EXPAND_ICON_SIZE = 12.0  # Expansion icon render size (canvas units)

    # ---- Menu dots ---------------------------------------------------------
    MENU_DOT_COLOR = 0xFF909090  # Node menu "..." dot color
    MENU_DOT_RADIUS = 1.5  # Menu dot circle radius
    MENU_DOT_GAP = 4.0  # Gap between menu dots

    @classmethod
    def to_dict(cls) -> dict:
        """Convert all style constants to a flat dict for C++ push."""
        return {
            "header_height": cls.HEADER_HEIGHT,
            "icon_size": cls.ICON_SIZE,
            "port_height": cls.PORT_HEIGHT,
            "port_radius": cls.PORT_RADIUS,
            "border_radius": cls.BORDER_RADIUS,
            "connection_curve": cls.CONNECTION_CURVE,
            "connection_thickness": cls.CONNECTION_THICKNESS,
            "group_indent": cls.GROUP_INDENT,
            "selection_color": cls.SELECTION_COLOR,
            "selection_width": cls.SELECTION_WIDTH,
            "selection_glow_pad": cls.SELECTION_GLOW_PAD,
            "selection_glow_alpha": cls.SELECTION_GLOW_ALPHA,
            "selection_outline_alpha": cls.SELECTION_OUTLINE_ALPHA,
            "grid_minor_spacing": cls.GRID_MINOR_SPACING,
            "grid_major_every": cls.GRID_MAJOR_EVERY,
            "grid_minor_color": cls.GRID_MINOR_COLOR,
            "grid_major_color": cls.GRID_MAJOR_COLOR,
            "lod_threshold_3": cls.LOD_THRESHOLD_3,
            "lod_threshold_2": cls.LOD_THRESHOLD_2,
            "lod_threshold_0": cls.LOD_THRESHOLD_0,
            "conn_min_thickness": cls.CONN_MIN_THICKNESS,
            "conn_min_thickness_lod3": cls.CONN_MIN_THICKNESS_LOD3,
            "min_node_screen_w": cls.MIN_NODE_SCREEN_W,
            "min_node_screen_h": cls.MIN_NODE_SCREEN_H,
            "port_size_lod1": cls.PORT_SIZE_LOD1,
            "port_alpha_lod1": cls.PORT_ALPHA_LOD1,
            "port_size_lod2": cls.PORT_SIZE_LOD2,
            "port_alpha_lod2": cls.PORT_ALPHA_LOD2,
            "type_color_float4": cls.TYPE_COLOR_FLOAT4,
            "type_color_float2": cls.TYPE_COLOR_FLOAT2,
            "type_color_color": cls.TYPE_COLOR_COLOR,
            "type_color_normal": cls.TYPE_COLOR_NORMAL,
            "type_color_token": cls.TYPE_COLOR_TOKEN,
            "type_color_int": cls.TYPE_COLOR_INT,
            "type_color_bool": cls.TYPE_COLOR_BOOL,
            "type_color_asset": cls.TYPE_COLOR_ASSET,
            "type_color_string": cls.TYPE_COLOR_STRING,
            "type_color_default": cls.TYPE_COLOR_DEFAULT,
            "header_accent_color": cls.HEADER_ACCENT_COLOR,
            "icon_badge_bg": cls.ICON_BADGE_BG,
            "port_label_color": cls.PORT_LABEL_COLOR,
            "port_glow_alpha": cls.PORT_GLOW_ALPHA,
            "connected_dot": cls.CONNECTED_DOT,
            "port_glow_scale": cls.PORT_GLOW_SCALE,
            "unresolved_port_color": cls.UNRESOLVED_PORT_COLOR,
            "interface_only_port_alpha": cls.INTERFACE_ONLY_PORT_ALPHA,
            "closed_port_color": cls.CLOSED_PORT_COLOR,
            "closed_port_scale": cls.CLOSED_PORT_SCALE,
            "empty_port_circle": cls.EMPTY_PORT_CIRCLE,
            "empty_port_text": cls.EMPTY_PORT_TEXT,
            "backdrop_body_alpha": cls.BACKDROP_BODY_ALPHA,
            "backdrop_header_alpha": cls.BACKDROP_HEADER_ALPHA,
            "backdrop_desaturate": cls.BACKDROP_DESATURATE,
            "backdrop_body_bright": cls.BACKDROP_BODY_BRIGHT,
            "backdrop_header_bright": cls.BACKDROP_HEADER_BRIGHT,
            "backdrop_depth_darken": cls.BACKDROP_DEPTH_DARKEN,
            "text_backing_color": cls.TEXT_BACKING_COLOR,
            "backdrop_title_color": cls.BACKDROP_TITLE_COLOR,
            "backdrop_desc_color": cls.BACKDROP_DESC_COLOR,
            "bc_offset_x": cls.BC_OFFSET_X,
            "bc_offset_y": cls.BC_OFFSET_Y,
            "bc_bar_height": cls.BC_BAR_HEIGHT,
            "bc_h_pad": cls.BC_H_PAD,
            "bc_corner_radius": cls.BC_CORNER_RADIUS,
            "bc_seg_h_pad": cls.BC_SEG_H_PAD,
            "bc_sep_block_w": cls.BC_SEP_BLOCK_W,
            "bc_max_seg_w": cls.BC_MAX_SEG_W,
            "bc_max_bar_frac": cls.BC_MAX_BAR_FRAC,
            "bc_bg": cls.BC_BG,
            "bc_border": cls.BC_BORDER,
            "bc_sep_color": cls.BC_SEP_COLOR,
            "bc_root_text": cls.BC_ROOT_TEXT,
            "bc_ancestor_text": cls.BC_ANCESTOR_TEXT,
            "bc_current_text": cls.BC_CURRENT_TEXT,
            "bc_hover_text": cls.BC_HOVER_TEXT,
            "bc_hover_bg": cls.BC_HOVER_BG,
            "bc_hover_border": cls.BC_HOVER_BORDER,
            "tooltip_delay": cls.TOOLTIP_DELAY,
            "tooltip_font_size": cls.TOOLTIP_FONT_SIZE,
            "tooltip_pad": cls.TOOLTIP_PAD,
            "tooltip_offset_x": cls.TOOLTIP_OFFSET_X,
            "tooltip_offset_y": cls.TOOLTIP_OFFSET_Y,
            "tooltip_max_w": cls.TOOLTIP_MAX_W,
            "tooltip_radius": cls.TOOLTIP_RADIUS,
            "tooltip_section_gap": cls.TOOLTIP_SECTION_GAP,
            "tooltip_title_scale": cls.TOOLTIP_TITLE_SCALE,
            "tooltip_meta_scale": cls.TOOLTIP_META_SCALE,
            "tooltip_desc_scale": cls.TOOLTIP_DESC_SCALE,
            "tooltip_line_spacing": cls.TOOLTIP_LINE_SPACING,
            "tooltip_bg": cls.TOOLTIP_BG,
            "tooltip_border": cls.TOOLTIP_BORDER,
            "tooltip_text_color": cls.TOOLTIP_TEXT_COLOR,
            "tooltip_title": cls.TOOLTIP_TITLE,
            "tooltip_meta": cls.TOOLTIP_META,
            "tooltip_desc": cls.TOOLTIP_DESC,
            "marquee_outline": cls.MARQUEE_OUTLINE,
            "marquee_fill": cls.MARQUEE_FILL,
            "base_font_size": cls.BASE_FONT_SIZE,
            "bc_font_size": cls.BC_FONT_SIZE,
            "expand_icon_tint": cls.EXPAND_ICON_TINT,
            "expand_fallback": cls.EXPAND_FALLBACK,
            "expand_icon_size": cls.EXPAND_ICON_SIZE,
            "menu_dot_color": cls.MENU_DOT_COLOR,
            "menu_dot_radius": cls.MENU_DOT_RADIUS,
            "menu_dot_gap": cls.MENU_DOT_GAP,
            "texture_preview_padding": cls.TEXTURE_PREVIEW_PADDING,
            "texture_preview_corner_r": cls.TEXTURE_PREVIEW_CORNER_R,
            "error_color": cls.ERROR_COLOR,
            "warning_color": cls.WARNING_COLOR,
            "error_band_alpha": cls.ERROR_BAND_ALPHA,
            "error_band_width": cls.ERROR_BAND_WIDTH,
            "error_band_corner_scale": cls.ERROR_BAND_CORNER_SCALE,
            "error_aura_alpha": cls.ERROR_AURA_ALPHA,
            "error_aura_width": cls.ERROR_AURA_WIDTH,
            "error_conn_glow_extra": cls.ERROR_CONN_GLOW_EXTRA,
            "error_conn_glow_alpha": cls.ERROR_CONN_GLOW_ALPHA,
            "error_conn_outer_glow": cls.ERROR_CONN_OUTER_GLOW,
            "error_conn_outer_alpha": cls.ERROR_CONN_OUTER_ALPHA,
            "error_port_halo_width": cls.ERROR_PORT_HALO_WIDTH,
            "error_port_halo_alpha": cls.ERROR_PORT_HALO_ALPHA,
            "error_port_ring_alpha": cls.ERROR_PORT_RING_ALPHA,
            "error_port_ring_width": cls.ERROR_PORT_RING_WIDTH,
            "group_icon_color": cls.GROUP_ICON_COLOR,
            "group_label_color": cls.GROUP_LABEL_COLOR,
        }

import weakref

import omni.ext
import omni.kit.app
from omni import ui

CLIP_BORDER_RADIUS = 0
TIME_FONT_SIZE = 10
g_singleton = None


class TimelineMergeStyle:
    def __init__(self):
        self._ext_id = None
        self._icon_path = None
        self._style_details_dark = {
            "Window": {"background_color": 0xFF444444},
            "CameraButton": {
                "color": 0xFF000000,
                "background_color": 0xFF23211F,
                "padding": 4,
                "stack_direction": ui.Direction.RIGHT_TO_LEFT,
            },
            "CameraButton:hovered": {
                "color": 0xFFFFAAAA,
                "background_color": 0xFF575757,
                "padding": 4,
                "stack_direction": ui.Direction.RIGHT_TO_LEFT,
            },
            "CameraButton.Image": {
                "color": 0xFFFFB900,
                "background_color": 0xFF444444,
                "alignment": ui.Alignment.CENTER,
            },
            "CameraButtonOff": {
                "color": 0xFFFFAAAA,
                "background_color": 0xFF444444,
                "padding": 4,
                "stack_direction": ui.Direction.RIGHT_TO_LEFT,
            },
            "CameraButtonOff:hovered": {
                "color": 0xFFFFAAAA,
                "background_color": 0xFF575757,
                "padding": 4,
                "stack_direction": ui.Direction.RIGHT_TO_LEFT,
            },
            "CameraButtonOff.Image": {
                "color": 0xFF848774,
                "background_color": 0xFF444444,
                "alignment": ui.Alignment.CENTER,
            },
            "Button": {
                "color": 0xFFFFFFFF,
                "background_color": 0xFF444444,
                "padding": 4,
                "stack_direction": ui.Direction.RIGHT_TO_LEFT,
            },
            "Button.Label": {"color": 0xFF9E9E9E, "alignment": ui.Alignment.LEFT_CENTER},
            "Button.Tooltip": {"color": 0xFF9E9E9E},
            "Button.Image": {"color": 0xFFFFFFFF, "background_color": 0xFF444444, "alignment": ui.Alignment.CENTER},
            "Button:hovered": {"background_color": 0xFF575757},
            "Field": {"background_color": 0xFF535354, "color": 0xFFCCCCCC},
            "Label::search": {"color": 0xFFACACAC},
            "Label::ValueY": {"color": 0xFF646464, "height": 100},
            "Rectangle::Splitter": {"background_color": 0x0, "margin": 3, "border_radius": 2},
            "Rectangle::Splitter:hovered": {"background_color": 0xFFB0703B},
            "Rectangle::Splitter:pressed": {"background_color": 0xFFB0703B},
            "Rectangle::CurveKey": {"background_color": 0x0, "border_color": 0xFF0ABAE7, "border_width": 1},
            "Rectangle::CurveKey:hovered": {"background_color": 0x0, "border_color": 0xFFAAAAAA},
            "Rectangle::CurveKey:pressed": {"background_color": 0x0, "border_color": 0xFFAAAAAA},
            "Rectangle::CurveActiveKey": {"background_color": 0x0, "border_color": 0xFFCCCCCC, "border_width": 1},
            "Rectangle::CurveActiveKey:hovered": {"background_color": 0x0, "border_color": 0xFFAAAAAA},
            "Rectangle::CurveActiveKey:pressed": {"background_color": 0x0, "border_color": 0xFFAAAAAA},
            "Rectangle::CurveKeyDrag": {"background_color": 0x08FFFFFF},
            "Rectangle::CurveKeyDrag:hovered": {"background_color": 0x08FFFFFF},
            "Rectangle::CurveKeyDrag:pressed": {"background_color": 0x08FFFFFF},
            "Rectangle::CurveControl": {"background_color": 0x7F000000},
            "Rectangle::CurveControl:hovered": {"background_color": 0x7F000000},
            "Rectangle::CurveControl:pressed": {"background_color": 0x7F000000},
            "Rectangle::CurveControlDrag": {"background_color": 0x08FFFFFF},
            "Rectangle::CurveControlDrag:hovered": {"background_color": 0x08FFFFFF},
            "Rectangle::CurveControlDrag:pressed": {"background_color": 0x08FFFFFF},
            "Rectangle::CurveControlProxy": {"background_color": 0x7F3F7FFF},
            "Rectangle::CurveControlProxy:hovered": {"background_color": 0xFF3F7FFF},
            "Rectangle::CurveControlProxy:pressed": {"background_color": 0xFF3F7FFF},
            "Rectangle::TimeRangeShading": {"background_color": 0x1FFFFFFF},
            "FreeLine::ControlLine": {"color": 0x7F3F7FFF},
            "Multi_selection_rectangle": {
                "background_color": 0x24FFFFFF,
                "border_width": 3.0,
                "border_color": 0x6EFFFFFF,
                "opacity": 0.5,
            },
            "Tools.TextField": {
                "background_color": 0xFF111111,
                "border_color": 0xFF000000,
                "border_width": 1,
                "color": 0xFFC0C0C0,
                "alignment": ui.Alignment.LEFT,
            },
            "ScrollingFrame": {
                "background_color": 0xFF444444,
                "secondary_color": 0xFFFFFFFF,
                "scrollbar_size": 10,
                "margin": 0,
                "border": 0,
            },
            "Tooltip": {
                "background_color": 0xFFC7F5FC,
                "color": 0xFF4B493B,
                "border_width": 1,
                "margin_width": 2,
                "margin_height": 1,
                "padding": 1,
            },
            "TreeView": {
                "background_color": 0xFF23211F,
                "background_selected_color": 0x664F4D43,
                "secondary_color": 0xFF403B3B,
            },
            "TreeView.ScrollingFrame": {"background_color": 0xFF23211F},
            "TreeView.Root": {"color": 0xFF111111, "font_size": 20},
            "TreeView.Header": {"background_color": 0xFF343432, "color": 0xFFCCCCCC, "font_size": 16},
            "TreeView.Header::name": {"margin": 3, "alignment": ui.Alignment.LEFT},
            "TreeView.Header::date": {"margin": 3, "alignment": ui.Alignment.CENTER},
            "TreeView.Header::size": {"margin": 3, "alignment": ui.Alignment.RIGHT},
            "TreeView.Image::object_icon_grey": {"color": 0x80FFFFFF},
            "TreeView.Item": {"color": 0xFF8A8777, "font_size": 16},
            "TreeView.Item::object_name_grey": {"color": 0xFF4D4B42},
            "TreeView.Item:selected": {"color": 0xFF23211F},
            "TreeView:selected": {"background_color": 0xFF8A8777},
            "TreeView.Icon::default": {"color": 0xFF8A8777},
            "TreeView.Icon::default_grey": {"color": 0x80FFFFFF},
            "TreeView.Icon::file": {"color": 0xFFAAAAAA},
            "TreeView.Icon::file_grey": {"color": 0xFFAAAAAA},
            "TreeView.Icon:selected": {"color": 0xFF23211F},
            "Timeline.TimelineBar": {"color": 0xFF00FF00, "background_color": 0xFF00FF00},
            "Timeline.Ticks": {"background_color": 0xFF000000, "color": 0xFF707070, "border_width": 1},
            "Timeline.TracksBackground": {"background_color": 0xFFA2A2A2, "border_width": 1},
            "Timeline.Tracks.CameraTrack": {
                "background_color": 0xFF8CAF96,
                "border_color": 0xFF5A5A5A,
                "border_width": 1,
            },
            "Timeline.Tracks.CameraTrack:hovered": {
                "background_color": 0xFFACCFB6,
                "border_color": 0xFFDCFFD6,
                "border_width": 1,
            },
            "Timeline.Tracks.CameraTrack.invisible": {
                "background_color": 0xFF555555,
                "border_color": 0xFFAAAAAA,
                "border_width": 1,
            },
            "Timeline.Tracks.CameraClip": {
                "background_color": 0xFF055005,
                "border_color": 0xFF8CAF96,
                "color": 0xFFACACAC,
                "border_width": 0,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.CameraClip.selected": {
                "background_color": 0xFF055005,
                "border_color": 0xFFFFFFFF,
                "color": 0xFFACACAC,
                "border_width": 2,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.CameraClip:hovered": {
                "background_color": 0xFF208020,
                "border_color": 0xFF002200,
                "color": 0xFFACACAC,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AssetTrack": {
                "background_color": 0xFFB4A48E,
                "border_color": 0xFF5A5A5A,
                "border_width": 1,
            },
            "Timeline.Tracks.AssetTrack:hovered": {
                "background_color": 0xFFD4C4AE,
                "border_color": 0xFFC4B49E,
                "border_width": 1,
            },
            "Timeline.Tracks.AssetTrack.invisible": {
                "background_color": 0xFF555555,
                "border_color": 0xFFAAAAAA,
                "border_width": 1,
            },
            "Timeline.Tracks.AssetClip": {
                "background_color": 0xFF54340E,
                "border_color": 0xFF54340E,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AssetClip.Hold": {
                "background_color": 0xFF2A1A07,
                "border_color": 0xFF54340E,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AssetClip.Selected": {
                "background_color": 0xFF54340E,
                "border_color": 0xFFFFFFFF,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AssetClip.selected": {
                "background_color": 0xFF54340E,
                "border_color": 0xFFFFFFFF,
                "border_width": 2,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AssetClip:hovered": {
                "background_color": 0xFF74542E,
                "border_color": 0xFF54340E,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AudioClip": {
                "background_color": 0xFF505050,
                "border_color": 0xFF505050,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AudioClip:hovered": {
                "background_color": 0xFF707070,
                "border_color": 0xFF505050,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.AudioTrack": {
                "background_color": 0xFFC0C0C0,
                "border_color": 0xFF5A5A5A,
                "border_width": 1,
            },
            "Timeline.Tracks.AudioTrack:hovered": {
                "background_color": 0xFFE0E0E0,
                "border_color": 0xFFE0E0E0,
                "border_width": 1,
            },
            "Timeline.Tracks.CustomClip": {
                "background_color": 0xFF808080,
                "border_color": 0xFFACFFA6,
                "border_width": 1,
                "border_radius": CLIP_BORDER_RADIUS,
            },
            "Timeline.Tracks.CustomTrack": {
                "background_color": 0xFF4E7494,
                "border_color": 0xA6FFAC,
                "border_width": 1,
            },
            "Sequencer.Stack": {
                "stack_direction": ui.Direction.LEFT_TO_RIGHT,
                "color": 0xFFFF0000,
                "background_color": 0xFF23211F,
            },
            "Sequencer.TrackListBackground": {"background_color": 0xFFA2A2A2, "border_width": 1},
            "Sequencer.TrackBackground": {"background_color": 0xFFACBFA6, "border_width": 0},
            "Sequencer.TrackTypeName": {"color": 0xFF101010, "border_width": 0},
            "Sequencer.TrackIcon": {"color": 0xFF404040},
            "Timeline.ClipName": {"color": 0xFFEEEEEE, "border_width": 0, "font_size": 12},
            "Timeline.ClipRange": {"color": 0xFFEEEEEE, "border_width": 0, "font_size": TIME_FONT_SIZE},
            "Timeline.ClipIcon": {"color": 0xFF404040},
            "CurveGeneralColor": {"color": 0xFF6BC7CE},
            "Curve.xformOp:scale:x": {"color": 0xFF8989E5},
            "Curve.xformOp:scale:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:scale:z": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateX:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateY:x": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateZ:x": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateXYZ:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateXYZ:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateXYZ:z": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateXZY:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateXZY:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateXZY:z": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateYXZ:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateYXZ:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateYXZ:z": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateYZX:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateYZX:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateYZX:z": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateZXY:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateZXY:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateZXY:z": {"color": 0xFFFF9100},
            "Curve.xformOp:rotateZYX:x": {"color": 0xFF8989E5},
            "Curve.xformOp:rotateZYX:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:rotateZYX:z": {"color": 0xFFFF9100},
            "Curve.xformOp:translate:x": {"color": 0xFF8989E5},
            "Curve.xformOp:translate:y": {"color": 0xFF9AFF8E},
            "Curve.xformOp:translate:z": {"color": 0xFFFF9100},
        }

    def set_ext_id(self, ext_id):  # pragma: no cover    Unused code
        self._ext_id = ext_id
        manager = omni.kit.app.get_app().get_extension_manager()
        extension_path = manager.get_extension_path(ext_id)
        self._icon_path = f"{extension_path}/data/icons"

    def get_icon_path(self, style, icon_name):  # pragma: no cover    Unused code
        if style is None:
            self.get_style()
            style = self._style
        return f"{self._icon_path}/{style}/{icon_name}"

    def get_style(self):
        self._style = "NvidiaDark"
        if self._style == "NvidiaLight":
            style = {
                # TODO relam -- Yeah...
            }
        else:
            style = self._style_details_dark

        return style

    def get_track_background(self, type):  # pragma: no cover    Unused code
        # TODO relam -- Make this data-driven!!
        track_types = [
            ("Shot", "Timeline.Tracks.CameraTrack"),
            ("Asset", "Timeline.Tracks.AssetTrack"),
            ("Audio", "Timeline.Tracks.AudioTrack"),
            ("Custom", "Timeline.Tracks.CustomTrack"),
            ("translateX", "Timeline.Tracks.CameraTrack"),
            ("translateY", "Timeline.Tracks.CameraTrack"),
            ("translateZ", "Timeline.Tracks.CameraTrack"),
            ("rotateX", "Timeline.Tracks.AssetTrack"),
            ("rotateY", "Timeline.Tracks.AssetTrack"),
            ("rotateZ", "Timeline.Tracks.AssetTrack"),
            ("scaleX", "Timeline.Tracks.AudioTrack"),
            ("scaleY", "Timeline.Tracks.AudioTrack"),
            ("scaleZ", "Timeline.Tracks.AudioTrack"),
        ]

        for track_type in track_types:
            if track_type[0] == type:
                return track_type[1]
        return "Timeline.Tracks.CustomTrack"

    def get_clip_background(self, type):  # pragma: no cover    Unused code
        # TODO relam -- Make this data-driven!!
        track_types = [
            ("Shot", "Timeline.Tracks.CameraClip"),
            ("Asset", "Timeline.Tracks.AssetClip"),
            ("Audio", "Timeline.Tracks.AudioClip"),
            ("Custom", "Timeline.Tracks.CustomClip"),
        ]

        for track_type in track_types:
            if track_type[0] == type:
                return track_type[1]

        return "Timeline.Tracks.CustomTrack"

    # -----------------------------------------
    @staticmethod
    def get_instance():
        global g_singleton
        if g_singleton == None:
            g_singleton = TimelineMergeStyle()
        return weakref.proxy(g_singleton)

    # must call before extension unload GC
    @staticmethod
    def destroy():
        global g_singleton
        g_singleton = None

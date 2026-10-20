# Public API for module omni.kit.graph.delegate.modern:

## Classes

- class BackdropDelegate(GraphNodeDelegateFull)
  - def node_header(self, model, node_desc: GraphNodeDescription)
  - def node_background(self, model, node_desc: GraphNodeDescription)

- class GraphNodeDelegate(GraphNodeDelegateRouter)
  - def __init__(self)
  - static def get_style(border = None, background = None, node_background = None, icon_background = None, border_selected = None, node_background_selected = None)
  - static def specialized_color_style(name, color, icon, secondary_color)
  - static def specialized_port_style(name, color)

- class AbstractGraphNodeDelegate
  - def destroy(self)
  - def get_node_layout(self, model, node_desc: GraphNodeDescription)
  - def node_background(self, model, node_desc: GraphNodeDescription)
  - def node_header_input(self, model, node_desc: GraphNodeDescription)
  - def node_header_output(self, model, node_desc: GraphNodeDescription)
  - def node_header(self, model, node_desc: GraphNodeDescription)
  - def node_footer(self, model, node_desc: GraphNodeDescription)
  - def port_input(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription)
  - def port_output(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription)
  - def port(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription)
  - def connection(self, model, source_desc: GraphConnectionDescription, target_desc: GraphConnectionDescription, foreground: bool = False)

- class GraphConnectionDescription
  - def __init__(self, node, port, widget, level, is_tangent_reversed = False)

- class GraphNodeDescription
  - def __init__(self, node, connected_source = None, connected_target = None)

- class GraphPortDescription
  - def __init__(self, port, level, relative_position, parent_child_count, connected_source = None, connected_target = None)

- class GraphModel
  - class ExpansionState(Enum)
    - OPEN: int
    - MINIMIZED: int
    - CLOSED: int
  - class PreviewState(IntFlag)
    - NONE: int
    - OPEN: Unknown
    - CACHED: Unknown
    - LARGE: Unknown
  - DISPLAY_NAME: NoneType
  - def __init__(self)
  - def subscribe_item_changed(self, fn)
  - def subscribe_selection_changed(self, fn)
  - def subscribe_node_changed(self, fn)
  - static def has_nodes(obj)
  - [property] def name(self, item) -> str
  - [name.setter] def name(self, value: str, item = None)
  - [property] def type(self, item)
  - [property] def inputs(self, item)
  - [inputs.setter] def inputs(self, value, item = None)
  - [property] def outputs(self, item)
  - [outputs.setter] def outputs(self, value, item = None)
  - [property] def nodes(self, item = None)
  - [property] def ports(self, item = None)
  - [ports.setter] def ports(self, value, item = None)
  - [property] def expansion_state(self, item = None) -> ExpansionState
  - [expansion_state.setter] def expansion_state(self, value: ExpansionState, item = None)
  - def can_connect(self, source, target)
  - [property] def position(self, item = None)
  - [position.setter] def position(self, value, item = None)
  - def position_begin_edit(self, item)
  - def position_end_edit(self, item)
  - [property] def size(self, item)
  - [size.setter] def size(self, value, item = None)
  - def size_begin_edit(self, item)
  - def size_end_edit(self, item)
  - [property] def description(self, item)
  - [description.setter] def description(self, value, item = None)
  - [property] def display_color(self, item)
  - [display_color.setter] def display_color(self, value, item = None)
  - [property] def stacking_order(self, item)
  - [property] def selection(self)
  - [selection.setter] def selection(self, value: list)
  - def special_select_widget(self, node, node_widget)
  - def destroy(self)
  - [property] def icon(self, item) -> Optional[Union[str, Any]]
  - [icon.setter] def icon(self, value: Optional[Union[str, Any]], item = None)
  - [property] def preview(self, item) -> Optional[Union[str, Any]]
  - [preview.setter] def preview(self, value: Optional[Union[str, Any]], item = None)
  - [property] def preview_state(self, item) -> PreviewState
  - [preview_state.setter] def preview_state(self, value: PreviewState, item = None)
  - [property] def add_empty_input_port(self, item) -> bool
  - [property] def add_empty_output_port(self, item) -> bool

- class GraphNodeDelegateFull(AbstractGraphNodeDelegate)
  - def __init__(self, *args)
  - def switch_expansion(self, model, node)
  - def build_expansion_widget(self, model, node, style_name)
  - def node_header(self, model, node_desc: GraphNodeDescription)
  - def node_background(self, model, node_desc: GraphNodeDescription)
  - def node_header_input(self, model, node_desc: GraphNodeDescription)
  - def node_header_output(self, model, node_desc: GraphNodeDescription)
  - def node_footer(self, model, node_desc: GraphNodeDescription)
  - static def build_tooltip(text_tips = [], visible_min = None, visible_max = None)
  - def port_input(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription)
  - static def build_port_input(model, node_desc, port_desc, style, override_style_name)
  - def port(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription)
  - static def build_port(model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription, port_name, can_edit_fn = None)
  - def port_output(self, model, node_desc: GraphNodeDescription, port_desc: GraphPortDescription)
  - static def build_port_output(model, node_desc, port_desc, style, override_style_name)
  - def connection(self, model: GraphModel, source: GraphConnectionDescription, target: GraphConnectionDescription, foreground: bool = False) -> Tuple[ui.ZStack, ui.FreeLine, ui.FreeBezierCurve]
  - static def build_connection(model: GraphModel, source: GraphConnectionDescription, target: GraphConnectionDescription, style: dict, override_style_name: str, foreground: bool = False) -> Tuple[ui.ZStack, ui.FreeLine, ui.FreeBezierCurve]

- class NoteDelegate(GraphNodeDelegateFull)
  - def node_header(self, model, node_desc: GraphNodeDescription)
  - def node_background(self, model, node_desc: GraphNodeDescription)

## Variables

- color: Unknown
- NODE_MIN_WIDTH: int
- BACKGROUND_RADIUS: float
- TEXT_VISIBLE_MIN: float
- PORT_VISIBLE_MIN: float
- PORT_RADIUS: int
- CURRENT_PATH: Unknown
- ICON_PATH: Unknown
- HIGHLIGHT_THICKNESS: float
- CONNECTION_PORT_WIDTH: float
- NODE_WIDTH_MARGIN: Unknown
- INPUT_PORT_WIDTH_MARGIN: Unknown
- OUTPUT_PORT_WIDTH_MARGIN: float
- PORT_HEIGHT: int
- HEADER: Dict
- STATE_TOGGER: Dict
- ICON: Dict

## Other

- partial: unknown
- Path: unknown
- Tuple: unknown
- omni.ui: public module

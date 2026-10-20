# Public API for module omni.kit.graph.editor.core:

## Classes

- class GraphEditorCoreWidget
  - def __init__(self, model = None, delegate = None, view_type = GraphView, style = None, catalog_model: Optional[ui.AbstractItemModel] = None, catalog_delegate: Optional[ui.AbstractItemDelegate] = None, has_catalog: bool = True, toolbar_items = [], **kwargs)
  - [property] def style(self)
  - [style.setter] def style(self, style)
  - def destroy(self)
  - def get_current_graph_item(self)
  - def on_accept_drop(self, drop_data: str)
  - def on_drop(self, event: ui.WidgetMouseDropEvent)
  - def on_build_catalog(self)
  - def on_build_breadcrumbs(self)
  - def on_build_graph(self)
  - def on_build_startup(self)
  - def on_left_mouse_button_pressed(self, items)
  - def on_right_mouse_button_pressed(self, items)
  - def on_left_mouse_button_double_clicked(self, items)
  - def on_key_pressed(self, key, mod, pressed)
  - def on_catalog_context_menu(self, items: List[ui.AbstractItem])
  - def focus_on_nodes(self)
  - def set_current_compound(self, item, focus = True)
  - [property] def model(self)
  - [model.setter] def model(self, model)
  - def set_toolbar_items(self, items)
  - def clear_all(self)

# Public API for module omni.kit.graph.widget.variables:

## Classes

- class GraphEditorVariablesWidget
  - def __init__(self, model: ui.AbstractItemModel, delegate: ui.AbstractItemDelegate = None, on_add_variable: Optional[Callable[[], None]] = None, on_add_variable_category: Optional[Callable[[], None]] = None, on_find_variable_reference: Optional[Callable[[ui.AbstractItem], None]] = None, on_build_variable_value_widget: Optional[Callable[[ui.AbstractItem], bool]] = None, supported_variable_types: Optional[list] = None, **kwargs)
  - def destroy(self)
  - [property] def visible(self)
  - [visible.setter] def visible(self, value: bool)
  - def set_on_add_variable_fn(self, fn: Optional[Callable[[ui.AbstractItem], None]])
  - def set_on_add_variable_category_fn(self, fn: Optional[Callable[[], None]])
  - def set_on_find_variable_reference_fn(self, fn: Optional[Callable[[ui.AbstractItem], None]])
  - def set_on_build_variable_value_widget_fn(self, fn: Optional[Callable[[ui.AbstractItem], bool]])

- class GraphEditorVariablesTreeDelegate(GraphEditorCoreTreeDelegate)
  - def __init__(self, on_drag_variable_read: Optional[Callable[[ui.AbstractItem], str]] = None, on_drag_variable_write: Optional[Callable[[ui.AbstractItem], str]] = None)
  - def build_item_widget(self, model, item, column_id, level, expanded)

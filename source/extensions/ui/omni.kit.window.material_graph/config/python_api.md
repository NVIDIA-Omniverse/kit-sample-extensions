# Public API for module omni.kit.window.material_graph:

## Classes

- class GraphExtension(omni.ext.IExt, MenuHelperExtension)
  - def __init__(self)
  - def on_startup(self, ext_id: str)
  - def on_shutdown(self)
  - static def show_materials(prim_list: List[object] = None)
  - static def add_node(mime_data: str)

## Functions

- def add_background_menu_item(label: str, callback: Callback) -> bool
- def add_node_menu_item(label: str, callback: Callback, node_types: Optional[Union[str, Iterable[str]]] = None) -> bool
- def remove_background_menu_item(label: str, callback: Optional[Callback] = None)
- def remove_node_menu_item(label: str, callback: Optional[Callback] = None)
- def add_mdl_catalog_module(path: str)
- def get_extension() -> Optional[GraphExtension]
- def get_graph_window() -> Optional[GraphWindow]
- def remove_mdl_catalog_module(path: str)

## Other



# Public API for module omni.kit.window.material_graph.scripts.api:

## Functions

- def add_background_menu_item(label: str, callback: Callback) -> bool
- def add_node_menu_item(label: str, callback: Callback, node_types: Optional[Union[str, Iterable[str]]] = None) -> bool
- def remove_background_menu_item(label: str, callback: Optional[Callback] = None)
- def remove_node_menu_item(label: str, callback: Optional[Callback] = None)

# Material Graph - Developer API Cookbook

This cookbook documents the supported integration helpers in
`omni.kit.window.material_graph`.

## Imports

```python
import omni.kit.window.material_graph as mg
```

## Context Menu API

### `add_background_menu_item(label: str, callback: Callback) -> bool`

Registers a graph-background context-menu action.

- `label`: menu label shown to users.
- `callback`: called with `(items, mouse_position)` when selected.
- returns `True` when registration succeeds.

```python
def on_background(items, mouse_position):
    print("Background click at:", mouse_position)

ok = mg.add_background_menu_item("My Background Action", on_background)
```

### `add_node_menu_item(label: str, callback: Callback, node_types: Optional[Union[str, Iterable[str]]] = None) -> bool`

Registers a node context-menu action.

- `label`: menu label shown to users.
- `callback`: called with `(node_type, prim_path)` when selected.
- `node_types`: optional node-type filter (`"Shader"`, `"NodeGraph"`, list/set, etc.).
- returns `True` when registration succeeds.

```python
def on_node(node_type, prim_path):
    print("Node action:", node_type, prim_path)

mg.add_node_menu_item("Inspect Node", on_node, node_types={"Shader", "NodeGraph"})
```

### `remove_background_menu_item(label: str, callback: Optional[Callback] = None)`

Unregisters background context-menu items by label.

- if `callback` is provided, removes only matching `(label, callback)`.
- if `callback` is `None`, removes all entries with that `label`.

```python
mg.remove_background_menu_item("My Background Action", on_background)
```

### `remove_node_menu_item(label: str, callback: Optional[Callback] = None)`

Unregisters node context-menu items by label.

- if `callback` is provided, removes only matching `(label, callback)`.
- if `callback` is `None`, removes all entries with that `label`.

```python
mg.remove_node_menu_item("Inspect Node", on_node)
```

## Extension / Window Helpers

### `get_extension() -> Optional[GraphExtension]`

Returns the active Material Graph extension instance, or `None` if unavailable
(not started yet, shutting down, etc.).

```python
ext = mg.get_extension()
if ext is None:
    print("Material Graph extension is not active")
```

### `get_graph_window() -> Optional[GraphWindow]`

Returns the active graph window instance if it exists.

```python
window = mg.get_graph_window()
if window:
    window.visible = True
```

## MDL Catalog Module Helpers

### `add_mdl_catalog_module(path: str)`

Adds an MDL module path to settings and triggers catalog reload when the
extension is active.

```python
mg.add_mdl_catalog_module("MyLibrary.mdl")
```

### `remove_mdl_catalog_module(path: str)`

Removes an MDL module path from settings and triggers catalog reload when the
extension is active.

```python
mg.remove_mdl_catalog_module("MyLibrary.mdl")
```

## Lifecycle Pattern

Register in startup, unregister in shutdown.

```python
class MyExt:
    def on_startup(self):
        import omni.kit.window.material_graph as mg
        mg.add_background_menu_item("My Action", self._on_bg)
        mg.add_node_menu_item("My Node Action", self._on_node, node_types="Shader")

    def on_shutdown(self):
        import omni.kit.window.material_graph as mg
        mg.remove_background_menu_item("My Action", self._on_bg)
        mg.remove_node_menu_item("My Node Action", self._on_node)

    def _on_bg(self, items, mouse_position):
        pass

    def _on_node(self, node_type, prim_path):
        pass
```

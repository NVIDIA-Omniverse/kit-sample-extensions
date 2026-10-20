# Material Graph Editor Developer Reference

## 1. Scope

This document targets extension integrators and tooling developers.
Public APIs listed in Section 2 are intended for integration use; internal behavior sections describe observed implementation details and can change between releases.

## 2. Public API

### Stable API Surface

Import:

```python
import omni.kit.window.material_graph as mg
```

#### Context menu API

```python
mg.add_background_menu_item(label: str, callback: Callback) -> bool
mg.add_node_menu_item(
    label: str,
    callback: Callback,
    node_types: Optional[Union[str, Iterable[str]]] = None
) -> bool
mg.remove_background_menu_item(label: str, callback: Optional[Callback] = None) -> None
mg.remove_node_menu_item(label: str, callback: Optional[Callback] = None) -> None
```

Callback signatures:

- Background menu callback: `(items, mouse_position)`
- Node menu callback: `(node_type, prim_path)`

Example:

```python
import omni.kit.window.material_graph as mg

def on_background(items, mouse_position):
    print("Background:", mouse_position)

def on_node(node_type, prim_path):
    print("Node:", node_type, prim_path)

mg.add_background_menu_item("My Background Action", on_background)
mg.add_node_menu_item("My Node Action", on_node, node_types={"Shader", "NodeGraph"})
```

#### Window helpers

```python
mg.get_extension() -> Optional[GraphExtension]
mg.get_graph_window() -> Optional[GraphWindow]
```

Example:

```python
window = mg.get_graph_window()
if window:
    window.visible = True
```

#### MDL module helpers

```python
mg.add_mdl_catalog_module(path: str) -> None
mg.remove_mdl_catalog_module(path: str) -> None
```

Example:

```python
mg.add_mdl_catalog_module("MyLibrary.mdl")
mg.remove_mdl_catalog_module("MyLibrary.mdl")
```

### Internal Details (Non-API)

- Callback registration performs signature checks.
- Duplicate label/callback registration is rejected.
- Dead callback targets are pruned from registries.
- Window instance access is extension-lifecycle dependent.

## 3. Settings and Identifiers

### Settings prefixes

- Normal runtime prefix: `/persistent/app/properties/materialGraph/`
- Test runtime prefix: `/persistent/app/properties/materialGraphTest/`

### Core keys and defaults

- `forceConnect` = `false`
- `showCatalog` = `true`
- `confineNodeGraphs` = `true`
- `backdropDefaultColor` = `[0.84, 0.71, 0.29]`
- `confineBackdrops` = `true`
- `previewTextureInput` = `false`
- `droppableTextureFormats` = `["bmp","dds","exr","gif","hdr","jpeg","jpg","png","psd","tga","tif"]`
- `catalogTextureIconSize` = `128`
- `catalogTextures` = token-resolved `${data}/catalog_textures` path
- `compoundPaths` = list containing the token-resolved `${data}/nodegraphs` path
- `compoundDefaultExportPath` = token-resolved `${data}/nodegraphs` path

### Plugin property keys

Under `plugins/<pluginName>/...`:

- MDL:
  - `enablePolymorphic` (default `true`)
  - `modules` (default from extension settings)
  - `catalogExcludedAnnotations` (default `["deprecated","unused","hidden"]`)
  - `outputPorts` (default `["displacement","surface","volume"]`)
- MaterialX:
  - `outputPorts`
  - `ignoreContexts`
  - `ignoreFamilies`
  - `ignoreNameRegexes`
- Universal:
  - `outputPorts`

### Hydra render context key

- `/persistent/app/hydra/material/renderContexts`

## 4. MDL Module Loading Internals

- **Module source (settings):** Loaded from MDL plugin `modules` setting.
- **.mdl suffix requirement:** Entries must end with `.mdl`.
- **Resolver validation:** Each entry is validated through asset resolution before use.
- **Deduplication:** Duplicate module entries are removed while preserving effective order.
- **Registration flow:** Valid modules are registered, then shader subidentifiers are enumerated into catalog items.
- **Reload behavior:** Changing module settings triggers catalog refresh.
- **Caching:** Module signatures are cached to avoid redundant re-registration for unchanged module sets.

## 5. Annotation Filtering Logic

- **Default excluded annotations:** `deprecated`, `unused`, `hidden` (MDL plugin default behavior).
- **MDL override behavior:** `catalogExcludedAnnotations` can override exclusion list.
- **Normalization:** Annotation names are normalized to lowercase, trimmed, and deduplicated before filtering.

## 6. MDL Icon & Thumbnail Authoring

Use exact MDL annotation syntax:

- `anno::thumbnail(<relative path>)`
- `export annotation icon(string path);`

Behavior:

- **Relative resolution:** Paths are resolved relative to the MDL file that defines the node.
- **Precedence order:** `thumbnail` -> `icon` -> generic fallback per render context.
- **Fallback logic:** Missing files do not block node creation; generic visuals are used instead.

## 7. Hydra Material Delegate Error Semantics

- Required output missing -> delegate error.
- Incompatible link -> delegate error.
- Errors are reported through application logging.
- No automatic graph repair is performed.

## 8. Render Context Handling

- **Context list source:** Hydra render contexts are read from `/persistent/app/hydra/material/renderContexts`.
- **Default behavior:** One active context is used for catalog, validation, and output interpretation at a time.
- **Interaction with UI:** Active context selection updates visible catalog content and context-scoped graph presentation.

## 9. Verification Checklist

Validate the following in a runtime build:

1. Public API import and callable signatures for context menu, window helpers, and MDL module helpers.
2. MDL module setting update triggers catalog reload and ignores invalid/unresolvable entries.
3. Annotation filtering reflects defaults and custom `catalogExcludedAnnotations`.
4. MDL icon/thumbnail precedence resolves as `thumbnail -> icon -> fallback`.
5. Missing required outputs produce Hydra material delegate logging errors.
6. Force-connected incompatible links produce Hydra material delegate logging errors.
7. Context switching updates catalog content and context-scoped visibility as expected.

# Public API for module omni.kit.widget.collection:

## Classes

- class ContextMenu
  - def __init__(self)
  - class def generate_create_for_stage_widget(cls) -> Dict
  - class def material_features_supported(cls, event = None) -> bool
  - def on_mouse_event(self, event)
  - def is_under_collection(objects)
  - def is_under_collection_and_is_directly_included(objects)
  - def is_under_collection_and_is_indirectly_included(objects)
  - def is_not_under_collection(objects)
  - def is_collection_selected(objects)
  - def delete_collection(objects)
  - def duplicate_collection(objects)
  - def clear_collection(objects)
  - def remove_from_collection(objects)
  - def exclude_from_collection(objects)
  - def create_collection(objects)
  - def block_collection(objects)
  - def select_collection_contents(objects)
  - def toggle_visibility(objects)
  - def menu_rename_collection_dialog(objects)
  - def bind_material_to_prim_dialog(objects)
  - def copy_path(objects)
  - def show_expandrules_menu(objects)
  - def show_actions_menu(objects)
  - def rename_collection(stage, helper, window, field_widget)
  - def rename_collection_dialog(objects)

- class CollectionWidgetExtension(omni.ext.IExt)
  - def on_startup(self)
  - def on_shutdown(self)

- class CollectionIcons
  - def __init__(self)
  - def set(self, prim_type: str, icon_path: Union[str, Path])
  - def get(self, prim_type: str, default: Union[str, Path] = None) -> str
  - def subscribe_icons_changed(self, fn)

- class CollectionWidget
  - def __init__(self, stage: Usd.Stage, **kwargs)
  - def build_layout(self)
  - def set_selection_watch(self, selection)
  - def set_collection_watch(self, collection_watch)
  - def expand(self, path: Sdf.Path)
  - def destroy(self)
  - def open_stage(self, stage: Usd.Stage)
  - def update_icons(self)

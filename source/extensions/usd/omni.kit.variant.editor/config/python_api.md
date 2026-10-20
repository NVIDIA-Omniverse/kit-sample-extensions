# Public API for module omni.kit.variant.editor:

## Classes

- class VariantEditorCore
  - class AuthorVariant
  - def __init__(self)
  - [property] def add_props_to_all_variants(self)
  - [add_props_to_all_variants.setter] def add_props_to_all_variants(self, value)
  - [property] def create_visibility_by_default(self)
  - [create_visibility_by_default.setter] def create_visibility_by_default(self, value)
  - [property] def active_variant(self)
  - [active_variant.setter] def active_variant(self, value)
  - def bind_to(self, callback)
  - static def get_instance()
  - def destroy(self)
  - def get_settings(self)
  - def validate_variant_edit(self, show_warning = True)
  - def find_spec_in_variant(self, spec_path)
  - def anchor_reference_asset_path_to_layer(self, ref: Sdf.Reference, intro_layer: Sdf.Layer, anchor_layer: Sdf.Layer)
  - def anchor_payload_asset_path_to_layer(self, ref: Sdf.Payload, intro_layer: Sdf.Layer, anchor_layer: Sdf.Layer)
  - def is_prim_path_in_metadata(self, path_to_check: str)
  - def save_property_metadata(self, prim: Usd.Prim)
  - def get_property_display_name(self, path: Sdf.Path) -> str
  - async def process_prim(self, prim_path)
  - def check_prim_for_property(self, prim_path, property_name)

- class AddVariantSetCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, auto_postfix: bool)
  - def do(self)
  - def undo(self)

- class RemoveVariantSetCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str)
  - def do(self)
  - def undo(self)

- class RenameVariantSetCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, new_name: str)
  - def do(self)
  - def undo(self)

- class AddVariantCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, variant_name: str, auto_postfix: bool)
  - def do(self)
  - def undo(self)

- class RemoveVariantCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, variant_name: str)
  - def do(self)
  - def undo(self)

- class RenameVariantCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, variant_name: str, new_name: str)
  - def do(self)
  - def undo(self)

- class DuplicateVariantCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, variant_name: str, new_name: str, auto_postfix: bool)
  - def do(self)
  - def undo(self)

- class EditVariantCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, cmd_name: str, cmd_args: dict, target_variant: str = None)
  - def do(self)
  - def undo(self)

- class PasteVariantCommand(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, variant_set_name: str, clipboard: Dict[Sdf.Path, Any], target_path: Sdf.Path = None)
  - def do(self)
  - def undo(self)

- class RefreshVariantUiCommand(omni.kit.commands.Command)
  - def do(self)
  - def undo(self)

- class CreateUsdRelationshipCommand(omni.kit.commands.Command)
  - def __init__(self, prim: Usd.Prim, rel_name: str, custom: bool = False, usd_context_name: str = '')
  - def do(self)
  - def undo(self)

- class CollapseSessionPropertyCommand(omni.kit.commands.Command)
  - def __init__(self, prim: Usd.Prim, prop_name: str, usd_context_name: str = '')
  - def do(self)
  - def undo(self)

- class SetVariantEditorActiveVariantCommand(omni.kit.commands.Command)
  - def __init__(self, variant_path: str)
  - def do(self)
  - def undo(self)

- class HotkeyBuilder
  - def __init__(self, ext_id: str, var_window: VariantEditorWindow)
  - def on_shutdown(self)

- class UsdVariantPropertiesWidgetBuilder(UsdPropertiesWidgetBuilder)
  - class def startup(cls)
  - class def init_arg_writer_table(cls)
  - class def floating_point_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def integer_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def bool_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def string_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def vec_per_channel_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def tftoken_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def sdf_asset_path_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def time_code_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def sdf_asset_path_array_arg_writer(cls, metadata, additional_widget_kwargs)
  - class def write_args(cls, property_type: type[Usd.Attribute | Usd.Relationship], metadata, additional_widget_kwargs)
  - class def build(cls, stage, attr_name, metadata, property_type, prim_paths: List[Sdf.Path], additional_label_kwargs = None, additional_widget_kwargs = None)
  - class def create_label(cls, attr_name, metadata = None, additional_label_kwargs = None)
  - class def create_attribute_context_menu(cls, widget, model, comp_index = -1)

- class VariantEditorWindow(StageChangeHelper)
  - static def get_instance()
  - def __init__(self)
  - def destroy(self)
  - def show(self)
  - def hide(self)
  - def show_options_menu(self)
  - def set_tree_view_expanded(self, model: VariantTreeModel, item)
  - def is_changed_path_needed(self, path: Sdf.Path)
  - def on_stage_changed(self)
  - def duplicate_variant_action(self)
  - def rename_variant_action(self)

- class Extension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_window()
- def get_instance()

## Variables

- TEST_DATA_PATH: str

## Other

- weakref: builtin module
- Path: unknown
- carb: public module
- omni.ext: public module
- re: builtin module
- Any: unknown
- Dict: unknown
- Union: unknown
- omni.kit.commands: public module
- omni.kit.usd_undo: public module
- Sdf: unknown module
- Usd: unknown module
- Vt: unknown

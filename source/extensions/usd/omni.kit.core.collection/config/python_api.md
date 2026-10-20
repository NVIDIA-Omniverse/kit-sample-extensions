# Public API for module omni.kit.core.collection:

## Classes

- class ToggleVisibilitySelectedPrimsCommand(omni.kit.commands.Command)
  - def __init__(self, selected_paths: List[str], stage: Optional[Usd.Stage] = None, visible: Optional[bool] = None)
  - def do(self)
  - def undo(self)

- class CollectionHelper
  - prop_prefix: str
  - prop_dotted_prefix: str
  - API_prefix: str
  - collection_properties: List
  - def __init__(self, collection_path: str, stage = None)
  - class def from_collection_api(cls, collection: Usd.CollectionAPI)
  - def get_all_members(self, prims_only = False) -> Set[Usd.Object]
  - def get_members(self, filter = '') -> List[Sdf.Path]
  - class def is_valid_collection_path(cls, path: Sdf.Path)
  - class def is_collection_property_path(cls, path: Sdf.Path)
  - class def strip_property_from_path(cls, path: Sdf.Path) -> Sdf.Path
  - def is_valid(self) -> bool
  - def get_collection_api(self) -> Usd.CollectionAPI
  - def get_prim(self) -> Usd.Prim
  - def get_collection_name(self, namespace = False)
  - def get_full_path(self)
  - class def get_collection_properties(cls)
  - def duplicate_with_name(self, new_collection_name: str, generate_valid_name: bool = False) -> str
  - def delete_collection(self)

- class StageHelper
  - static def get_stage(usd_context_name: str = '') -> Union[Usd.Stage, None]

- class AddItemToCollection(omni.kit.commands.Command)
  - def __init__(self, path_to_add: str, collection_path: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class RemoveItemFromCollection(omni.kit.commands.Command)
  - def __init__(self, prim_or_prop_path: str, collection_path: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class ExcludeItemFromCollection(omni.kit.commands.Command)
  - def __init__(self, prim_or_prop_path: str, collection_path: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class ClearCollection(omni.kit.commands.Command)
  - def __init__(self, collection_path: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class BlockCollection(omni.kit.commands.Command)
  - def __init__(self, collection_path: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class SetCollectionExpansionRule(omni.kit.commands.Command)
  - string_to_token_mapping: Dict
  - def __init__(self, collection_path: str, expansion_rule: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class DuplicateCollection(omni.kit.commands.Command)
  - def __init__(self, collection_path: str, new_collection_name: str = '', usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class RenameCollection(omni.kit.commands.Command)
  - def __init__(self, old_collection_path: str, new_collection_name: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class DeleteCollection(omni.kit.commands.Command)
  - def __init__(self, collection_path: str, usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class CreateCollection(omni.kit.commands.Command)
  - def __init__(self, prim_path: str, collection_name: str = '', usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class SelectPrimsInCollection(omni.kit.commands.Command)
  - def __init__(self, collection_path: str = '', usd_context_name: str = '', **kwargs)
  - def do(self)
  - def undo(self)

- class SetCollectionVisibility(ToggleVisibilitySelectedPrimsCommand)
  - def __init__(self, selected_paths: List[str], visible: bool, stage: Optional[Usd.Stage] = None)
  - def do(self)
  - def undo(self)

## Functions

- def increment_pathname(path)
- def apply_stored_edit_target(stage: Usd.Stage, edit_target: Union[Usd.EditTarget, None] = None)

## Other

- contextlib: builtin module
- List: unknown
- Optional: unknown
- Union: unknown
- carb: public module
- omni: unknown module
- omni.kit.commands: public module
- Sdf: unknown
- Usd: unknown
- UsdGeom: unknown

# Public API for module omni.kit.property.collection:

## Classes

- class CollectionPropertiesWidget(UsdPropertiesWidget)
  - def on_new_payload(self, payload)
  - def build_group_frames(self, stage, ungrouped_props: List)
  - def build_items(self)

- class UsdCollectionPropertyWidgets(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Other

- List: unknown
- omni.ext: public module
- omni.kit.app: public module
- omni.usd: public module

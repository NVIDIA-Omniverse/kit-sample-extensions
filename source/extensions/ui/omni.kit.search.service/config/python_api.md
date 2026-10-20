# Public API for module omni.kit.search.service:

## Classes

- class SearchEngineRegistry
  - def __init__(self)
  - def register_search_model(self, name, model_type)
  - def get_search_names(self)
  - def get_available_search_names(self, server: str)
  - def get_search_model(self, name)
  - def subscribe_engines_changed(self, fn)

- class NGSearchServiceModel(AbstractSearchModel)
  - def __init__(self, **kwargs)
  - def destroy(self)
  - [property] def items(self) -> List[SearchServiceItem]
  - async def get_prefixes(self, url: str) -> List[str]

- class OmniSearch(omni.ext.IExt)
  - def on_startup(self)
  - def on_shutdown(self)

## Other

- omni.client: unknown module
- omni.ext: public module

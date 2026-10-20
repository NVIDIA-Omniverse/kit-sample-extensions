# Public API for module omni.kit.window.quicksearch:

## Classes

- class QuickSearchDelegate(ui.AbstractItemDelegate)
  - def __init__(self, *args, **kwargs)
  - def build_branch(self, model, item, column_id, level, expanded)
  - def build_section_widget(self, model, item, column_id, level, expanded)
  - def build_item_widget(self, model, item, column_id, level, expanded)
  - def build_widget(self, model, item, column_id, level, expanded)
  - def filter_by_text(self, filter_name_text: str)

- class QuickSearchExtension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def on_input(self, event)
  - def show_window(self)

- class QuickSearchRegistry
  - class QuickSearchModelHandler
    - name: str
    - model_type: Type[ui.AbstractItemModel]
    - delegate_type: Type[ui.AbstractItemDelegate]
    - accept_fn: Optional[Callable[[], bool]]
    - exclusive_fn: Optional[Callable[[], bool]]
    - priority: int
    - flat_search: bool
    - style: Optional[Dict[str, Any]]
  - def __init__(self)
  - def register_quick_search_model(self, name: str, model_type: Type[ui.AbstractItemModel], delegate_type: Type[ui.AbstractItemDelegate], accept_fn: Callable[[], bool] = None, exclusive_fn: Callable[[], bool] = None, priority: int = 100, flat_search: bool = True, style: Optional[Dict[str, Any]] = {}) -> Optional[QuickSearchRegistry._QuickSearchSubscription]
  - def get_names(self) -> List[str]
  - def get_quick_search(self, name: str) -> Optional[QuickSearchRegistry.QuickSearchModelHandler]
  - def subscribe_quick_search_changed(self, fn)

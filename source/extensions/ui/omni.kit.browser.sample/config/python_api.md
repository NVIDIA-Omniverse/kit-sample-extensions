# Public API for module omni.kit.browser.sample:

## Classes

- class SampleBrowserExtension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def get_model(self)
  - def get_window(self)

## Functions

- def get_instance()
- def register_sample_folder(url: str, name: Optional[str] = None)
- def unregister_sample_folder(url: str)

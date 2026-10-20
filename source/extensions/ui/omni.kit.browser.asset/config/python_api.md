# Public API for module omni.kit.browser.asset:

## Classes

- class AssetBrowserExtension(omni.ext.IExt)
  - [property] def window(self) -> Optional[AssetBrowserWindow]
  - [property] def browser_widget(self) -> Optional[TreeFolderBrowserWidget]
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_instance()

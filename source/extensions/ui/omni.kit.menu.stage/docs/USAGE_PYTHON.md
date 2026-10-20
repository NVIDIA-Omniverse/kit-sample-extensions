# Usage Examples

## Initialize ContentBrowserOptions

```python
import omni.kit.menu.stage

# Create a ContentBrowserOptions instance
content_browser_options = omni.kit.menu.stage.ContentBrowserOptions()

# Initialize the ContentBrowserOptions
# This registers additional context menus in the content browser
# for adding file-based assets to a USD stage
content_browser_options.startup()

# When you're done with it (e.g., when your extension shuts down)
content_browser_options.shutdown()
```
---

## Integrate ContentBrowserOptions in an Extension

```python
import omni.ext
import omni.kit.menu.stage

class MyExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        # Create ContentBrowserOptions instance when the extension starts
        # This adds context menu options to the content browser
        # allowing users to add USD assets to the stage with proper placement
        self._content_browser_options = omni.kit.menu.stage.ContentBrowserOptions()
        self._content_browser_options.startup()
        
    def on_shutdown(self):
        # Clean up when extension is shutting down
        if hasattr(self, "_content_browser_options"):
            self._content_browser_options.shutdown()
            self._content_browser_options = None
```

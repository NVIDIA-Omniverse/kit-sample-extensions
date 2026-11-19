# Usage Examples

## Add Custom Option Menu Item

```python
from omni.kit.browser.core import OptionMenuDescription
from omni.kit.window.material import get_instance

instance = get_instance()

# Create stage menu item description
def on_custom_stage_menu_item():
    print("Click on custom stage menu item")

stage_menu_desc = OptionMenuDescription(
    "Custom stage menu item",
    clicked_fn=on_custom_stage_menu_item,
)

# Add stage menu item to the material window
if instance.stage_options_menu:
    instance.stage_options_menu.append_menu_item(stage_menu_desc)

# Create library menu item description
def on_custom_library_menu_item():
    print("Click on custom library menu item")

library_menu_desc = OptionMenuDescription(
    "Custom library menu item",
    clicked_fn=on_custom_library_menu_item,
)

# Add library menu item to the material window
if instance.library_options_menu:
    instance.library_options_menu.append_menu_item(library_menu_desc)

```
---

## Integrate Material Browser Widget into a Custom Window

```python
import omni.ui as ui
from omni.kit.window.material import MaterialBrowserWidget

# Create a window for the Material Browser
window = ui.Window("Material Browser", width=800, height=600)

# Create the Material Browser Widget inside the window
with window.frame:
    material_browser = MaterialBrowserWidget()

```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.window.material/data/docs_images/integrate_material_browser_widget.png
---
align: center
---
```

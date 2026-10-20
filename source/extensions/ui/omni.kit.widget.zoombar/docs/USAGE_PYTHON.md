# Usage Examples

## Create a Basic ZoomBar Widget

```python
import omni.ui as ui
from omni.kit.widget.zoombar import ZoomBar

# Create a window to hold the ZoomBar widget
window = ui.Window("ZoomBar Example", width=300, height=100)

# Define callback functions for view mode and value changes
def on_view_mode_changed(icon_mode: bool):
    print(f"View mode changed to: {'Icon' if icon_mode else 'Detail'}")

def on_value_changed(value: int):
    print(f"Zoom value changed to: {value}")

def on_hovered(is_hovered: bool):
    print(f"ZoomBar hovered: {is_hovered}")

# Add the ZoomBar widget to the window
with window.frame:
    zoom_bar = ZoomBar(
        min=0,
        max=5,
        value=2,
        width=150,
        icon_mode=False,
        on_view_mode_changed_fn=on_view_mode_changed,
        on_value_changed_fn=on_value_changed
    )

    # Set hover callback
    zoom_bar.set_on_hovered_fn(on_hovered)

    # Access the slider model to programmatically set values
    model = zoom_bar.model
    model.set_value(4)  # Set zoom value to 7
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.widget.zoombar/data/docs_images/usage_preview.png
---
align: center
---
```

---

## Create a FileZoomBar for File System Navigation

```python
import omni.ui as ui
from omni.kit.widget.zoombar import FileZoomBar

# Create a window to hold the FileZoomBar widget
window = ui.Window("FileZoomBar Example", width=300, height=100)

# Define callback functions for grid view toggle and scale changes
def on_toggle_grid_view(icon_mode: bool):
    print(f"Grid view toggled to: {'Icon' if icon_mode else 'Detail'}")

def on_scale_grid_view(scale_value: float):
    print(f"Grid view scale changed to: {scale_value}")

# Add the FileZoomBar widget to the window
with window.frame:
    file_zoom_bar = FileZoomBar(
        show_grid_view=False,
        grid_view_scale=2,
        on_toggle_grid_view_fn=on_toggle_grid_view,
        on_scale_grid_view_fn=on_scale_grid_view
    )
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.widget.zoombar/data/docs_images/create_a_filezoombar_for_file_system_navigation.png
---
align: center
---
```

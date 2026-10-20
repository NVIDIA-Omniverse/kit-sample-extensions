# Usage Examples

## Control Minibar Visibility

```python
import omni.kit.timeline.minibar
import carb

# Get settings interface
settings = carb.settings.get_settings()

# Show/hide the timeline minibar
settings.set_bool(omni.kit.timeline.minibar.MINIBAR_VISIBLE_PATH, True)  # Show minibar
settings.set_bool(omni.kit.timeline.minibar.MINIBAR_VISIBLE_PATH, False)  # Hide minibar

# Check current visibility state
is_visible = settings.get_as_bool(omni.kit.timeline.minibar.MINIBAR_VISIBLE_PATH)
print(f"Minibar is visible: {is_visible}")
```
---

## Configure Minibar Bottom Position

```python
import carb
from omni.kit.timeline.minibar import MINIBAR_BOTTOM_SETTINGS_PATH

# Get the settings interface
settings = carb.settings.get_settings()

# Set the bottom offset for the timeline minibar (in pixels)
settings.set_int(MINIBAR_BOTTOM_SETTINGS_PATH, 50)

# Get the current bottom offset
bottom_offset = settings.get_as_int(MINIBAR_BOTTOM_SETTINGS_PATH)
print(f"Timeline minibar bottom offset: {bottom_offset} pixels")

# Reset to default position
settings.set_int(MINIBAR_BOTTOM_SETTINGS_PATH, 30)
```
---

## Enable Hover Toggle Behavior

```python
import omni.kit.timeline.minibar
import carb

# Get settings interface
settings = carb.settings.get_settings()

# Enable minibar to toggle visibility on hover
settings.set_bool(omni.kit.timeline.minibar.MINIBAR_TOGGLE_BY_HOVER_PATH, True)

# Disable hover toggle behavior
settings.set_bool(omni.kit.timeline.minibar.MINIBAR_TOGGLE_BY_HOVER_PATH, False)

# Check current hover toggle setting
hover_toggle_enabled = settings.get_as_bool(omni.kit.timeline.minibar.MINIBAR_TOGGLE_BY_HOVER_PATH)
print(f"Hover toggle enabled: {hover_toggle_enabled}")
```

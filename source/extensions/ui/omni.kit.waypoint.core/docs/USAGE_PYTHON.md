# Usage Examples

## Create Waypoint Browser Widget

```python
import omni.ui as ui
from omni.kit.waypoint.core import WaypointBrowserWidget, WaypointModel, WaypointDelegate

# Create a window for the waypoint browser
window = ui.Window("Waypoint Browser", width=400, height=300)

with window.frame:
    # Create waypoint model and delegate
    model = WaypointModel()
    delegate = WaypointDelegate(model)

    # Create the waypoint browser widget
    browser_widget = WaypointBrowserWidget(
        model=model,
        delegate=delegate,
        max_thumbnail_size=320
    )
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.waypoint.core/data/docs_images/usage_preview.png
---
align: center
---
```

---

## Create Waypoint List Window

```python
import omni.ui as ui
from omni.kit.waypoint.core import WaypointListWindow, WaypointItem

def on_edit_waypoint(item: WaypointItem, x: float, y: float):
    print(f"Editing waypoint: {item.waypoint.name} at position ({x}, {y})")

# Create a waypoint list window
waypoint_window = WaypointListWindow(on_edit_waypoint_fn=on_edit_waypoint)

# Show the window
waypoint_window.visible = True

# Access selected waypoint index
selected_index = waypoint_window.selected_index
if selected_index is not None:
    print(f"Selected waypoint index: {selected_index}")
```
### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.waypoint.core/data/docs_images/create_waypoint_list_window.png
---
align: center
---
```

---

## Setup Waypoint Change Callbacks

```python
from omni.kit.waypoint.core import get_instance, WaypointChangeCallbacks, ViewportWaypoint

def on_waypoint_created(waypoint: ViewportWaypoint):
    print(f"Waypoint created: {waypoint.name}")

def on_waypoint_deleted(waypoint: ViewportWaypoint):
    print(f"Waypoint deleted: {waypoint.name}")

def on_waypoint_changed(waypoint: ViewportWaypoint):
    print(f"Waypoint changed: {waypoint.name}")

def on_reset():
    print("Waypoints reset")

# Create callback handler
callbacks = WaypointChangeCallbacks(
    on_waypoint_created=on_waypoint_created,
    on_waypoint_deleted=on_waypoint_deleted,
    on_waypoint_changed=on_waypoint_changed,
    on_reset=on_reset
)

# Register callbacks with waypoint extension
waypoint_ext = get_instance()
waypoint_ext.register_callback(callbacks)

# Later, deregister callbacks when no longer needed
waypoint_ext.deregister_callback(callbacks)
```
---

## Create Waypoint Instance and Basic Operations

```python
from omni.kit.waypoint.core import get_instance, ViewportWaypoint
import omni.usd
import asyncio

async def setup_and_use_waypoints():
    # Ensure USD context is available and create a new stage
    usd_context = omni.usd.get_context()
    await usd_context.new_stage_async()

    # Get the waypoint extension instance
    waypoint_ext = get_instance()

    # Create a new waypoint synchronously
    waypoint_ext.create_waypoint("MyWaypoint")

    # Get all waypoints
    all_waypoints = waypoint_ext.get_waypoints()

    # Get a specific waypoint by name
    my_waypoint = waypoint_ext.get_waypoint("MyWaypoint")

    # Recall a waypoint (restore its settings)
    if my_waypoint:
        waypoint_ext.recall_waypoint(my_waypoint)

# Execute the async function
asyncio.ensure_future(setup_and_use_waypoints())
```

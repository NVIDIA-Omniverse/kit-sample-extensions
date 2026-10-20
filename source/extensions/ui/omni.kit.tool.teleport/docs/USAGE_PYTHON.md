# Usage Examples

## Configure Teleport Widget and Settings

```python
from omni.kit.tool.teleport import Teleport

# Create teleport instance with test mode
teleport = Teleport.get_instance(test=True)

# Set custom USD file for the teleport widget
teleport.set_widget_usd_file("path/to/custom_teleport_widget.usda")

# Enable or disable object picking in viewport
teleport.set_enabled_picking(False)

# Check if using ring manipulator
using_ring = teleport.is_using_ring_manipulator()
print(f"Using ring manipulator: {using_ring}")

# Get the teleport model for advanced operations
model = teleport.get_model()
```
---

## Create and Initialize Teleport Tool

```python
from omni.kit.tool.teleport import Teleport

# Create a new teleport instance directly
teleport = Teleport.get_instance()

# Activate the teleport tool
teleport.set_active(True)

# Show the teleport arc/beam visualization
teleport.show_arc(True)

# Check if teleport tool is active
is_active = teleport.get_active()
print(f"Teleport tool is active: {is_active}")

# Check if using ring manipulator
using_ring = teleport.is_using_ring_manipulator()
print(f"Using ring manipulator: {using_ring}")
```
---

## Cleanup and Destroy Teleport

```python
from omni.kit.tool.teleport import Teleport

# Create teleport instance directly
teleport = Teleport.get_instance()

# Deactivate the teleport tool
teleport.set_active(False)

# Unbind widget materials (useful for testing)
teleport.unbind_widget_material()

# Destroy the teleport instance and release resources
teleport.destroy()
```
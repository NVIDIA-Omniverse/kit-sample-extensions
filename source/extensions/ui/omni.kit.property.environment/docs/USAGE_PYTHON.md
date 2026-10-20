# Usage Examples

## Show Environment Property Widget in window

```python
import omni.ui as ui
import omni.usd
from omni.kit.property.environment import EnvironmentPropertyWidget
from omni.kit.property.usd import PrimSelectionPayload

# Create a window to hold the environment property widget
window = ui.Window("Environment Property Widget Example", width=400, height=600)

with window.frame:
    # Show the environment property widget
    property_widget = EnvironmentPropertyWidget()
    property_widget.build()

    # Set the payload to the environment prim
    usd_context = omni.usd.get_context()
    stage = usd_context.get_stage()
    if stage:
        payload = PrimSelectionPayload(weakref.ref(stage), ["/Environment"])
        property_widget.on_new_payload(payload)
```

### Screenshot:
```{image} ../../../../source/extensions/ui/omni.kit.property.environment/data/docs_images/usage_preview.png
---
align: center
---
```

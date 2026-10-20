# omni.kit.tool.teleport

```
from omni.kit.tool.teleport import Teleport

# do this in start up
teleport = Teleport.get_instance()
teleport.set_active(True)

# if you want to use your usd widget file
teleport.set_widget_usd_file(full_usd_file_path)

# release it in shut down
teleport.set_active(False)
teleport.destroy()

def _on_global_mouse_event(self, event, *_):
    # trigger the teleport on click
    if mouse_click:
        teleport.on_click()
```

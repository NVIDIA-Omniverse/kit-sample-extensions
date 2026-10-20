# Usage Examples

## Generate MDL and USD Material Thumbnails

```python
from omni.kit.thumbnails.mdl import MdlThumbnailGenerator, UsdThumbnailGenerator, ThumbnailManager
import tempfile
import os
from functools import partial

# Create thumbnail manager with custom retry settings
thumbnail_manager = ThumbnailManager(max_retry_count=5)

# Define callback function for when thumbnail generation is complete
def on_thumbnail_done(result, url):
    if result:
        print(f"thumbnail successfully created: {url}")
    else:
        print(f"Failed to create thumbnail: {url}")

# Generate thumbnails for each material
mdl_generator = MdlThumbnailGenerator(
    mdl_url="mdl_material.mdl",
    output_url="mdl_material.png",
    mtl_name=None,  # No sub material
    width=256,
    height=256,
    on_thumbnail_done_fn=on_thumbnail_done,
)
thumbnail_manager.put(mdl_generator, timeout=60)

# Generate thumbnail for a USD file
usd_generator = UsdThumbnailGenerator(
    usd_url="usd_material.usd",
    output_url="usd_material.png",
    width=256,
    height=256,
    on_thumbnail_done_fn=on_thumbnail_done
)
thumbnail_manager.put(usd_generator, timeout=60)
```

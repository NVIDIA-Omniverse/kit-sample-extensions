# Kit thumbnails manager for mdl files.

To use:

```
from omni.kit.thumbnails.mdl import ThumbnailManager, MdlThumbnailGenerator

def on_thumbnail_generated(result: bool, url: str):
  if result:
    print(f"Generate thumbnail {url} succeeded")
  else:
    print(f"Failed to generate thumbnail {url})

manager = ThumbnailManager()
manager.put(
            MdlThumbnailGenerator(
                "<Url of MDL material>",
                "<Url of output thumbnail>",
                on_thumbnail_done_fn=on_thumbnail_generated,
            )
        )
```

Stopping the manager:

```
manager.destroy()
```
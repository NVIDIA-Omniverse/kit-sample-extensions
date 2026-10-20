# Public API for module omni.kit.thumbnails.usd:

## Classes

- class ThumbnailGenerator(ext.IExt)
  - def __init__(self)
  - def on_startup(self)
  - def on_shutdown(self)

- class ThumbnailManager
  - def __init__(self)
  - async def destroy(self)
  - def put(self, thumbnail_generator: ViewportThumbnailGenerator, timeout: int = 10)

- class UsdThumbnailGenerator(ViewportThumbnailGenerator)
  - def __init__(self, usd_url: str, output_url: str, template_url: str = DEFAULT_ASSET_TEMPLATE, width: int = 256, height: int = 256, on_thumbnail_done_fn: callable = None)
  - def prepare_thumbnail(self) -> bool

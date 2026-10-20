# Public API for module omni.kit.thumbnails.mdl:

## Classes

- class MdlThumbnailGenerator(ViewportThumbnailGenerator)
  - def __init__(self, mdl_url: str, output_url: str, mtl_name: Optional[str] = None, template_url: Optional[str] = None, stdin: Optional[str] = None, render_mode: Optional[str] = None, width: int = 256, height: int = 256, on_thumbnail_done_fn: callable = None)
  - def prepare_thumbnail(self) -> Tuple[str]

- class ThumbnailManager
  - def __init__(self, max_retry_count: int = 3)
  - def destroy(self)
  - def put(self, thumbnail_generator: ViewportThumbnailGenerator, timeout: int = None, retry: int = 0)

- class UsdThumbnailGenerator(ViewportThumbnailGenerator)
  - def __init__(self, usd_url: str, output_url: str, material_prim_path: Optional[str] = None, template_url: Optional[str] = None, stdin: Optional[str] = None, width: int = 256, height: int = 256, on_thumbnail_done_fn: callable = None)
  - def prepare_thumbnail(self) -> Tuple[str]

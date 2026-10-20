# Public API for module omni.storage_api.auth:

## Classes

- class AuthPortalError(Exception)
  - def __init__(self, discovery_url: str, error_code: str, error_message: str)

- class StorageAuthHandler
  - def __init__(self)
  - def destroy(self)
  - def get_effective_auth_timeout(self) -> float
  - def register_handler(self, discovery_url: str)
  - def unregister_handler(self, discovery_url: str)
  - async def discover_and_register(self, discovery_url: str, timeout: float = 180.0) -> Tuple[str, Ellipsis]
  - static def get_preconfigured_urls() -> Set[str]
  - async def auto_mount_preconfigured(self, timeout_per_url: float = 180.0) -> Dict[str, Tuple[str, Ellipsis]]
  - static def manual_token_refresh(deployment_url: str)
  - static def manual_new_storage_url(discovery_url: str)

- class StorageAuthExtension(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id: str)
  - def on_shutdown(self)
  - def get_auth_handler(self) -> Optional[StorageAuthHandler]
  - async def discover_and_register(self, discovery_url: str, timeout: float = 60.0) -> Tuple[str, Ellipsis]

## Functions

- def get_instance() -> Optional[StorageAuthExtension]

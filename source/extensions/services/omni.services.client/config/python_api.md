# Public API for module omni.services.client:

## Classes

- class BaseConsumer
  - def __init__(self, parsed_uri: ParseResult, app: Optional[Any], version: Optional[Any], persist_connections: bool = False, raise_for_status: bool = True)
  - def close(self)
  - async def close_async(self)

- class TransportNotFoundError(Exception)

- class Client(object)
  - def __init__(self, uri: str, app: Optional[Any] = None, api_version: Optional[Any] = None, persist_connections: bool = False, raise_for_status: bool = True)
  - def stop(self)

- class AsyncClient(Client)
  - async def stop_async(self)

## Functions

- def register(scheme: str, cls: Type[BaseConsumer], is_async: bool = False)
- def unregister(scheme: str, is_async: bool = False)
- def get_available_transports(is_async: bool = False) -> Dict[str, Type[BaseConsumer]]

## Other

- Any: unknown
- Dict: unknown
- Optional: unknown
- Type: unknown
- urlparse: unknown

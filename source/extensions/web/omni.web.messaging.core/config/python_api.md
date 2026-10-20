# Public API for module omni.web.messaging.core:

## Classes

- class WebMessagingAPI
  - def __init__(self)
  - def cleanup(self)
  - def incoming(self, name_or_func = None) -> Callable
  - def outgoing(self, name_or_func = None) -> Callable

- class BaseWebMessaging
  - def __init__(self)
  - class def incoming(cls, name_or_func = None)
  - class def outgoing(cls, name_or_func = None)
  - def destroy(self)

from types import MethodType
from typing import Callable, ForwardRef, TypeVar
from weakref import WeakMethod, ref

Self = TypeVar("Self", bound="WeakEvent")


class WeakEvent:
    def __init__(self, **data) -> None:
        self._handlers = set()
        self._data = data

    def add_handler(self: Self, handler: "Callable[..., object]") -> Self:
        if not callable(handler):
            raise ValueError("Event handler's must be callable.")

        if isinstance(handler, MethodType):
            self._handlers.add(WeakMethod(handler))
        else:
            self._handlers.add(ref(handler))
        return self

    def remove_handler(self: Self, handler: "Callable[..., object]") -> Self:
        if not callable(handler):
            raise ValueError("Event handler's must be callable.")

        if isinstance(handler, MethodType):
            self._handlers.discard(WeakMethod(handler))
        else:
            self._handlers.discard(ref(handler))
        return self

    def run(self, *args, **kwargs) -> None:
        active_handlers = {r() for r in self._handlers if r()}
        self._handlers.clear()
        for handler in active_handlers:
            d = {**self._data, **kwargs}
            handler(*args, **d)
            self.add_handler(handler)

    __iadd__ = add_handler
    __isub__ = remove_handler
    __call__ = run

"""Implement material graph extension logic for `commands/impl/connections/utils.py`."""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class _PortLike(Protocol):
    """Minimal protocol for ports used by connection commands."""

    def GetPrim(self):  # noqa: N802 - USD style
        """Return the owning prim for this port."""


def is_valid_port(port: Optional[_PortLike]) -> bool:
    """Return True when the port is non-null and backed by a valid prim."""
    if not port:
        return False
    prim = port.GetPrim()
    return bool(prim)

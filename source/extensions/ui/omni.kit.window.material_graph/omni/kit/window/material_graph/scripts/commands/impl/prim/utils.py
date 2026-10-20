"""Utility helpers shared by prim-creation command implementations."""


def sanitize_identifier(identifier: str) -> str:
    """Return a stable prim name from an SDR identifier."""
    if not identifier:
        return ""
    return identifier.split(">")[0].split("<")[-1].split("(")[0]

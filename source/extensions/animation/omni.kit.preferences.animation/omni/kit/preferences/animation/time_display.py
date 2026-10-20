from __future__ import annotations

import typing
from enum import Enum


class TimeDisplay(str, Enum):
    """Time Display enum.
    Timecode is a synonym for 'SMPTE' and has the same enum value.
    This is on purpose to avoid confustion with USD Timecodes.
    """

    FRAMES = "frames"
    SECONDS = "seconds"
    SMPTE = "smpte"
    TIMECODE = "smpte"

    @classmethod
    def default(cls):
        return cls.FRAMES

    def __str__(self) -> str:
        return self.value

    @classmethod
    def values(cls) -> typing.List[str]:
        return [item.value for item in cls]

    @staticmethod
    def from_string(value: str) -> TimeDisplay:
        value = str(value).lower()
        for item in TimeDisplay:
            if item.value == value:
                return item
        raise ValueError(f"Invalid string: {value}. Valid strings: {(item for item in TimeDisplay)}")

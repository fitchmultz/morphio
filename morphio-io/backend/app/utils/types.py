"""Type definitions for the Morphio backend."""

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

# JSON-serializable type hierarchy (Python 3.12+)
type JsonPrimitive = str | int | float | bool | None
type JsonDict = Mapping[str, "JsonValue"]
type JsonList = Sequence["JsonValue"]
type JsonValue = JsonPrimitive | JsonDict | JsonList

# For cache key components - must be stringifiable
type CacheKeyComponent = str | int | float | bool


@runtime_checkable
class SupportsToDict(Protocol):
    """Protocol for objects with to_dict() method."""

    def to_dict(self) -> dict[str, JsonValue]: ...


@runtime_checkable
class HasDictAttr(Protocol):
    """Protocol for objects with __dict__ attribute."""

    __dict__: dict[str, JsonValue]


@runtime_checkable
class HasText(Protocol):
    """Protocol for objects with a text attribute."""

    text: str


# Transcription can be: string, object with to_dict(), object with __dict__, or object with .text
type TranscriptionLike = str | SupportsToDict | HasDictAttr | HasText

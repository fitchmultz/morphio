from typing import List, Protocol, TypedDict


class TranscriptEntry(TypedDict, total=False):
    text: str
    start: float
    duration: float


class Transcript(Protocol):
    def fetch(self) -> List[TranscriptEntry]: ...


class TranscriptList(Protocol):
    def find_manually_created_transcript(self, languages: List[str]) -> Transcript: ...

    def find_generated_transcript(self, languages: List[str]) -> Transcript: ...

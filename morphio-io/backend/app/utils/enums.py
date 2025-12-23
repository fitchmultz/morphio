import json
from enum import Enum
from typing import Any, Dict


class SerializableEnum(Enum):
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {member.name: member.value for member in cls}

    @classmethod
    def to_json(cls) -> str:
        return json.dumps(cls.to_dict())

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def from_string(cls, value: str) -> "SerializableEnum":
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"{value} is not a valid {cls.__name__}")


class AuthProvider(SerializableEnum):
    LOCAL = "local"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    TWITTER = "twitter"


class ContentType(SerializableEnum):
    TEXT = "text"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    PDF = "pdf"
    URL = "url"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"


class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class MediaSource(str, Enum):
    UPLOAD = "upload"
    YOUTUBE = "youtube"
    RUMBLE = "rumble"
    TWITTER = "twitter"  # Includes x.com
    TIKTOK = "tiktok"


class MediaProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(SerializableEnum):
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class ProcessingStage(str, SerializableEnum):
    """Detailed processing stages for progress reporting.

    Each stage has a typical progress range:
    - QUEUED: 0-5%
    - DOWNLOADING: 5-20%
    - CHUNKING: 20-30%
    - TRANSCRIBING: 30-60%
    - DIARIZING: 50-70% (overlaps with transcribing)
    - GENERATING: 70-90%
    - SAVING: 90-100%
    """

    QUEUED = "queued"
    DOWNLOADING = "downloading"
    CHUNKING = "chunking"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    GENERATING = "generating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


class ResponseStatus(str, SerializableEnum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class SubscriptionTier(SerializableEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TemplateType(SerializableEnum):
    DEFAULT = "default"
    CUSTOM = "custom"
    SHARED = "shared"


class TranscriptionSource(str, SerializableEnum):
    YOUTUBE = "youtube"
    WHISPER = "whisper"


class TranscriptionStatus(str, SerializableEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INVALID = "invalid"


class UsageType(str, SerializableEnum):
    VIDEO_PROCESSING = "video_processing"
    AUDIO_PROCESSING = "audio_processing"
    WEB_SCRAPING = "web_scraping"
    CONTENT_GENERATION = "content_generation"
    LOG_PROCESSING = "log_processing"  # <--- ADDED
    OTHER = "other"


class UserRole(SerializableEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    POWER = "POWER"
    MODERATOR = "MODERATOR"
    GUEST = "GUEST"

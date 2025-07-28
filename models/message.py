"""
Pydantic models for normalized message structures across platforms.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages that can be sent/received."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    LOCATION = "location"
    STICKER = "sticker"
    QUICK_REPLY = "quick_reply"


class ContentType(str, Enum):
    """Content types for media messages."""

    TEXT_PLAIN = "text/plain"
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    VIDEO_MP4 = "video/mp4"
    AUDIO_MP3 = "audio/mp3"
    AUDIO_WAV = "audio/wav"
    APPLICATION_PDF = "application/pdf"


class Location(BaseModel):
    """Geographic location information."""

    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    address: str | None = Field(None, description="Human-readable address")
    title: str | None = Field(None, description="Location title/name")


class MediaContent(BaseModel):
    """Media content information."""

    url: str = Field(..., description="URL to the media content")
    content_type: ContentType = Field(..., description="MIME type of the content")
    size: int | None = Field(None, description="File size in bytes")
    duration: int | None = Field(
        None, description="Duration for audio/video in seconds"
    )
    thumbnail_url: str | None = Field(None, description="Thumbnail URL for media")


class QuickReply(BaseModel):
    """Quick reply option for interactive messages."""

    text: str = Field(..., description="Display text for the quick reply")
    payload: str = Field(..., description="Payload sent when quick reply is selected")


class IncomingMessage(BaseModel):
    """Normalized incoming message from any platform."""

    message_id: str = Field(..., description="Unique message identifier")
    user_id: str = Field(..., description="User identifier")
    platform: str = Field(..., description="Source platform (line, facebook, web)")
    message_type: MessageType = Field(..., description="Type of message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )

    # Content fields
    text: str | None = Field(None, description="Text content")
    media: MediaContent | None = Field(None, description="Media content")
    location: Location | None = Field(None, description="Location data")

    # Platform-specific data
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Original platform data"
    )

    # Quick reply payload if this is a quick reply response
    quick_reply_payload: str | None = Field(None, description="Quick reply payload")


class OutgoingMessage(BaseModel):
    """Normalized outgoing message to any platform."""

    message_type: MessageType = Field(..., description="Type of message to send")

    # Content fields
    text: str | None = Field(None, description="Text content to send")
    media: MediaContent | None = Field(None, description="Media content to send")
    location: Location | None = Field(None, description="Location to send")

    # Interactive elements
    quick_replies: list[QuickReply] | None = Field(
        None, description="Quick reply options"
    )

    # Platform-specific customization
    platform_data: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific data"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}

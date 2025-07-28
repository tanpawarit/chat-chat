"""
LINE platform adapter implementation.
"""

import base64
import hashlib
import hmac
from datetime import datetime
from typing import Any

from linebot.v3.messaging import ApiClient, Configuration, MessagingApi
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage  # type: ignore

from adapters.base.platform_base import PlatformAdapter
from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.platform import LineConfig, PlatformType
from models.user import User, UserProfile


class LineAdapter(PlatformAdapter):
    """LINE platform adapter."""

    def __init__(self, config: LineConfig):
        """Initialize LINE adapter with LINE-specific configuration."""
        super().__init__(config)
        self.line_config = config
        configuration = Configuration(access_token=config.channel_access_token)
        api_client = ApiClient(configuration)
        self.messaging_api = MessagingApi(api_client)

    @property
    def platform_type(self) -> PlatformType:
        """Return LINE platform type."""
        return PlatformType.LINE

    async def parse_incoming(
        self, webhook_data: dict[str, Any]
    ) -> IncomingMessage | None:
        """
        Parse LINE webhook data into normalized message.

        Args:
            webhook_data: LINE webhook payload

        Returns:
            Normalized IncomingMessage or None if parsing fails
        """
        try:
            events = webhook_data.get("events", [])
            if not events:
                return None

            # Handle first message event (LINE typically sends one event per webhook)
            event = events[0]

            # Only handle message events for now
            if event.get("type") != "message":
                return None

            message = event.get("message", {})
            source = event.get("source", {})

            # Extract user ID
            platform_user_id = source.get("userId")
            if not platform_user_id:
                return None

            # Generate normalized IDs
            user_id = self.generate_user_id(platform_user_id)
            message_id = self.generate_message_id(message.get("id", ""))

            # Determine message type and content
            message_type = MessageType.TEXT  # Default to text
            text_content = None

            if message.get("type") == "text":
                message_type = MessageType.TEXT
                text_content = message.get("text")
            elif message.get("type") == "image":
                message_type = MessageType.IMAGE
            elif message.get("type") == "video":
                message_type = MessageType.VIDEO
            elif message.get("type") == "audio":
                message_type = MessageType.AUDIO
            elif message.get("type") == "file":
                message_type = MessageType.FILE
            elif message.get("type") == "location":
                message_type = MessageType.LOCATION
            elif message.get("type") == "sticker":
                message_type = MessageType.STICKER
                text_content = (
                    f"[Sticker: {message.get('packageId')}/{message.get('stickerId')}]"
                )

            return IncomingMessage(
                message_id=message_id,
                user_id=user_id,
                platform=self.platform.value,
                message_type=message_type,
                timestamp=datetime.now(),
                text=text_content,
                raw_data=webhook_data,
                media=None,
                location=None,
                quick_reply_payload=None,
            )

        except Exception as e:
            print(f"Error parsing LINE webhook: {e}")
            return None

    async def format_outgoing(
        self, message: OutgoingMessage, user: User
    ) -> dict[str, Any]:
        """
        Format normalized message into LINE reply format.

        Args:
            message: Normalized outgoing message
            user: Target user

        Returns:
            LINE-formatted message data
        """
        # For now, only handle text messages
        if message.message_type == MessageType.TEXT and message.text:
            return {"type": "text", "text": message.text}

        # Default fallback
        return {"type": "text", "text": "Message type not supported"}

    async def send_message(self, formatted_message: dict[str, Any], user: User) -> bool:
        """
        Send message to LINE user.

        Args:
            formatted_message: LINE-formatted message
            user: Target user

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Extract reply token from user's platform data
            reply_token = user.platform_data.get("reply_token")
            if not reply_token:
                print("No reply token found in user data")
                return False

            # Create LINE message object
            if formatted_message.get("type") == "text":
                line_message = TextMessage(
                    text=formatted_message["text"], quickReply=None, quoteToken=None
                )
            else:
                # Fallback to text message
                line_message = TextMessage(
                    text="Unsupported message type", quickReply=None, quoteToken=None
                )

            # Send reply
            request = ReplyMessageRequest(
                replyToken=reply_token, messages=[line_message]
            )  # type: ignore

            self.messaging_api.reply_message(request)
            return True

        except Exception as e:
            print(f"Error sending LINE message: {e}")
            return False

    async def get_user_profile(self, platform_user_id: str) -> User | None:
        """
        Get LINE user profile.

        Args:
            platform_user_id: LINE user ID

        Returns:
            User object with profile data or None if failed
        """
        try:
            # For now, create a basic user object
            # In production, you'd call LINE API to get profile
            user_id = self.generate_user_id(platform_user_id)

            return User(
                user_id=user_id,
                platform=self.platform,
                platform_user_id=platform_user_id,
                message_count=0,
                profile=UserProfile(
                    display_name="LINE User",
                    avatar_url=None,
                    language="en",
                    timezone=None,
                    status_message=None,
                ),
                platform_data={},
            )

        except Exception as e:
            print(f"Error getting LINE user profile: {e}")
            return None

    async def validate_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        """
        Validate LINE webhook signature.

        Args:
            headers: HTTP headers
            body: Request body

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            signature = headers.get("x-line-signature", "")
            if not signature:
                return False

            # Create hash using channel secret
            hash_value = hmac.new(
                self.line_config.channel_secret.encode("utf-8"), body, hashlib.sha256
            ).digest()

            # LINE sends signature in base64 format, not hex with sha256 prefix
            expected_signature = base64.b64encode(hash_value).decode("utf-8")

            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            print(f"Error validating LINE webhook: {e}")
            return False

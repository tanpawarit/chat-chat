"""
Central bot gateway for handling normalized messages from all platforms.
"""

from typing import Any

from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.user import User


class BotGateway:
    """Central gateway for processing messages from all platforms."""

    def __init__(self):
        """Initialize the bot gateway."""
        pass

    async def handle_message(
        self, message: IncomingMessage, user: User
    ) -> OutgoingMessage:
        """
        Handle incoming message and return response.

        Args:
            message: Normalized incoming message
            user: User who sent the message

        Returns:
            Normalized outgoing message response
        """
        # Print message details for debugging
        print("=" * 50)
        print("=> INCOMING MESSAGE")
        print("=" * 50)
        print(f"Platform: {message.platform}")
        print(f"User ID: {message.user_id}")
        print(f"Message Type: {message.message_type.value}")
        print(f"Text: {message.text}")
        print(f"Timestamp: {message.timestamp}")
        print("=" * 50)

        # Print user details
        print("=> USER INFO")
        print("=" * 50)
        print(
            f"Display Name: {user.profile.display_name if user.profile else 'Unknown'}"
        )
        print(f"Platform User ID: {user.platform_user_id}")
        print(f"Message Count: {user.message_count}")
        print("=" * 50)

        # Check if this is a size/length limit warning message
        if (
            message.message_type == MessageType.TEXT
            and message.text
            and (
                message.text.startswith("ข้อความของคุณยาวเกินไป")
                or message.text.startswith("ไฟล์ของคุณใหญ่เกินไป")
                or message.text.startswith("รูปภาพของคุณใหญ่เกินไป")
                or message.text.startswith("วิดีโอของคุณใหญ่เกินไป")
                or message.text.startswith("ไฟล์เสียงของคุณใหญ่เกินไป")
            )
        ):
            # Return the warning message as-is (no echo)
            response_text = message.text
        # Simple echo response for normal messages
        elif message.message_type == MessageType.TEXT and message.text:
            response_text = f"Echo: {message.text}"
        elif message.message_type == MessageType.STICKER:
            response_text = "I received a sticker! 😊"
        elif message.message_type == MessageType.IMAGE:
            response_text = "I received an image! 📷"
        elif message.message_type == MessageType.VIDEO:
            response_text = "I received a video! 🎥"
        elif message.message_type == MessageType.AUDIO:
            response_text = "I received an audio message! 🎵"
        elif message.message_type == MessageType.LOCATION:
            response_text = "I received a location! 📍"
        else:
            response_text = "I received a message, but I'm not sure how to respond to this type yet."

        # Create response message
        response = OutgoingMessage(
            message_type=MessageType.TEXT,
            text=response_text,
            media=None,
            location=None,
            quick_replies=None,
        )

        print("=> OUTGOING MESSAGE")
        print("=" * 50)
        print(f"Response: {response_text}")
        print("=" * 50)

        return response

    def get_status(self) -> dict[str, Any]:
        """
        Get gateway status information.

        Returns:
            Dictionary containing gateway status
        """
        return {
            "status": "active",
            "version": "1.0.0",
            "features": ["text_messaging", "media_detection", "echo_responses"],
        }

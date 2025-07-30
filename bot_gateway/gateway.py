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
        self, message: IncomingMessage, user: User, store=None
    ) -> OutgoingMessage:
        """
        Handle incoming message and return response.

        Args:
            message: Normalized incoming message
            user: User who sent the message
            store: Store context (optional)

        Returns:
            Normalized outgoing message response
        """
        # Print message details for debugging (enhanced with store info)
        print("=" * 50)
        print("=> INCOMING MESSAGE")
        print("=" * 50)
        print(f"Platform: {message.platform}")
        print(f"User ID: {message.user_id}")
        print(f"Store ID: {user.store_id if user.store_id else 'N/A'}")
        print(f"Customer ID: {user.customer_id if user.customer_id else 'N/A'}")
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
        if store:
            print(f"Store Name: {store.name}")
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
        # Store-specific responses
        elif message.message_type == MessageType.TEXT and message.text:
            store_name = store.name if store else "Chat Bot"
            response_text = (
                f"สวัสดีครับ/ค่ะ จาก {store_name}! ท่านส่งข้อความว่า: {message.text}"
            )
        elif message.message_type == MessageType.STICKER:
            store_name = store.name if store else "Chat Bot"
            response_text = f"ได้รับสติกเกอร์จาก {store_name} แล้วครับ/ค่ะ! 😊"
        elif message.message_type == MessageType.IMAGE:
            store_name = store.name if store else "Chat Bot"
            response_text = f"ได้รับรูปภาพจาก {store_name} แล้วครับ/ค่ะ! 📷"
        elif message.message_type == MessageType.VIDEO:
            store_name = store.name if store else "Chat Bot"
            response_text = f"ได้รับวิดีโอจาก {store_name} แล้วครับ/ค่ะ! 🎥"
        elif message.message_type == MessageType.AUDIO:
            store_name = store.name if store else "Chat Bot"
            response_text = f"ได้รับข้อความเสียงจาก {store_name} แล้วครับ/ค่ะ! 🎵"
        elif message.message_type == MessageType.LOCATION:
            store_name = store.name if store else "Chat Bot"
            response_text = f"ได้รับตำแหน่งที่ตั้งจาก {store_name} แล้วครับ/ค่ะ! 📍"
        else:
            response_text = "ได้รับข้อความแล้วครับ/ค่ะ แต่ยังไม่แน่ใจว่าจะตอบกลับอย่างไรดี"

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

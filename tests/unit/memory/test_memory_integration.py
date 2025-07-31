"""
Test memory system integration with bot gateway.
Simulates real chatbot flow with memory persistence.
"""

import asyncio
import tempfile

import yaml

from bot_gateway.gateway import BotGateway
from memory.memory_manager import MemoryManagerFactory
from models.message import IncomingMessage, MessageType
from models.platform import PlatformType
from models.store import Store
from models.user import User


async def load_config():
    """Load configuration from config.yaml"""
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def test_bot_gateway_with_memory():
    """Test bot gateway integration with memory system."""
    print("🧪 Testing Bot Gateway + Memory Integration...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Update config to use temp directory
        config_data["memory"]["lm_base_path"] = temp_dir

        # Create memory manager
        memory_manager = await MemoryManagerFactory.create_from_config(config_data)

        # Create bot gateway with memory
        bot_gateway = BotGateway()
        bot_gateway.memory_manager = memory_manager

        try:
            # Simulate customer interaction
            store = Store(store_id="cafe_001", name="ร้านกาแฟดีดี", active=True)

            user = User(
                user_id="line_user123",
                platform=PlatformType.LINE,
                platform_user_id="U123456789",
            )

            print("\n1. First conversation - Customer greeting...")

            # First message: Greeting
            message1 = IncomingMessage(
                message_id="msg_001",
                user_id=user.user_id,
                platform=PlatformType.LINE.value,
                message_type=MessageType.TEXT,
                text="สวัสดีครับ",
            )

            response1 = await bot_gateway.handle_message(message1, user, store)
            print(f"Bot: {response1.text}")

            # Second message: Order inquiry
            message2 = IncomingMessage(
                message_id="msg_002",
                user_id=user.user_id,
                platform=PlatformType.LINE.value,
                message_type=MessageType.TEXT,
                text="มีกาแฟอะไรบ้างครับ",
            )

            response2 = await bot_gateway.handle_message(message2, user, store)
            print(f"Bot: {response2.text}")

            # Third message: Order
            message3 = IncomingMessage(
                message_id="msg_003",
                user_id=user.user_id,
                platform=PlatformType.LINE.value,
                message_type=MessageType.TEXT,
                text="ขอ Latte 1 แก้วครับ",
            )

            response3 = await bot_gateway.handle_message(message3, user, store)
            print(f"Bot: {response3.text}")

            print("✅ Conversation completed")

            print("\n2. Checking memory persistence...")

            # Check that conversation is stored in memory
            context = await memory_manager.get_context_for_llm(
                store.store_id, user.user_id
            )

            assert len(context["recent_messages"]) == 6  # 3 user + 3 bot messages
            print(f"✅ {len(context['recent_messages'])} messages stored in memory")

            # Print conversation history
            print("\n📊 Conversation History:")
            for i, msg in enumerate(context["recent_messages"], 1):
                print(f"  {i}. [{msg['role']}]: {msg['message']}")

            print("\n3. Testing memory retrieval in new session...")

            # Simulate same user returning later
            message4 = IncomingMessage(
                message_id="msg_004",
                user_id=user.user_id,
                platform=PlatformType.LINE.value,
                message_type=MessageType.TEXT,
                text="กลับมาอีกแล้วครับ",
            )

            # Should have access to previous conversation
            response4 = await bot_gateway.handle_message(message4, user, store)
            print(f"Bot: {response4.text}")

            # Check updated memory
            updated_context = await memory_manager.get_context_for_llm(
                store.store_id, user.user_id
            )

            assert (
                len(updated_context["recent_messages"]) == 8
            )  # 4 user + 4 bot messages
            print("✅ Memory continuity maintained across sessions")

        finally:
            await memory_manager.close()

    print("\n🎉 Bot Gateway + Memory integration test completed!")


async def test_multi_customer_scenarios():
    """Test multiple customers with isolated memory."""
    print("\n🧪 Testing multi-customer memory isolation...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        config_data["memory"]["lm_base_path"] = temp_dir

        memory_manager = await MemoryManagerFactory.create_from_config(config_data)
        bot_gateway = BotGateway()
        bot_gateway.memory_manager = memory_manager

        try:
            store = Store(store_id="restaurant_001", name="ร้านอาหารดี", active=True)

            # Customer A
            user_a = User(
                user_id="customer_a", display_name="คุณอานนท์", platform=PlatformType.LINE
            )

            # Customer B
            user_b = User(
                user_id="customer_b", display_name="คุณบุศรา", platform=PlatformType.LINE
            )

            print("\n1. Customer A orders food...")
            msg_a1 = IncomingMessage(
                message_id="a1",
                user=user_a,
                store=store,
                message_type=MessageType.TEXT,
                content="ขอข้าวผัดกุ้งครับ",
                platform=PlatformType.LINE,
                timestamp=None,
            )
            response_a1 = await bot_gateway.handle_message(msg_a1)
            print(f"Bot to A: {response_a1.content}")

            print("\n2. Customer B orders drinks...")
            msg_b1 = IncomingMessage(
                message_id="b1",
                user=user_b,
                store=store,
                message_type=MessageType.TEXT,
                content="ขอน้ำส้มคั้น 2 แก้วค่ะ",
                platform=PlatformType.LINE,
                timestamp=None,
            )
            response_b1 = await bot_gateway.handle_message(msg_b1)
            print(f"Bot to B: {response_b1.content}")

            print("\n3. Customer A continues order...")
            msg_a2 = IncomingMessage(
                message_id="a2",
                user=user_a,
                store=store,
                message_type=MessageType.TEXT,
                content="เพิ่มต้มยำกุ้งด้วยครับ",
                platform=PlatformType.LINE,
                timestamp=None,
            )
            response_a2 = await bot_gateway.handle_message(msg_a2)
            print(f"Bot to A: {response_a2.content}")

            # Check memory isolation
            print("\n4. Checking memory isolation...")

            context_a = await memory_manager.get_context_for_llm(
                store.store_id, user_a.user_id
            )
            context_b = await memory_manager.get_context_for_llm(
                store.store_id, user_b.user_id
            )

            # Customer A should have 4 messages (2 user + 2 bot)
            assert len(context_a["recent_messages"]) == 4
            assert any(
                "ข้าวผัดกุ้ง" in msg["message"] for msg in context_a["recent_messages"]
            )
            assert any(
                "ต้มยำกุ้ง" in msg["message"] for msg in context_a["recent_messages"]
            )

            # Customer B should have 2 messages (1 user + 1 bot)
            assert len(context_b["recent_messages"]) == 2
            assert any(
                "น้ำส้มคั้น" in msg["message"] for msg in context_b["recent_messages"]
            )

            # No cross-contamination
            assert not any(
                "น้ำส้มคั้น" in msg["message"] for msg in context_a["recent_messages"]
            )
            assert not any(
                "ข้าวผัดกุ้ง" in msg["message"] for msg in context_b["recent_messages"]
            )

            print("✅ Memory isolation between customers working correctly")

            print(
                f"\n📊 Customer A History ({len(context_a['recent_messages'])} messages):"
            )
            for msg in context_a["recent_messages"]:
                print(f"  [{msg['role']}]: {msg['message']}")

            print(
                f"\n📊 Customer B History ({len(context_b['recent_messages'])} messages):"
            )
            for msg in context_b["recent_messages"]:
                print(f"  [{msg['role']}]: {msg['message']}")

        finally:
            await memory_manager.close()

    print("\n🎉 Multi-customer isolation test completed!")


async def main():
    """Run integration tests."""
    print("🚀 Starting Memory Integration Tests\n")

    try:
        await test_bot_gateway_with_memory()
        await test_multi_customer_scenarios()

        print("\n🎉 All memory integration tests passed!")
        print("\n📊 Integration Test Summary:")
        print("✅ Bot Gateway + Memory Manager integration")
        print("✅ Conversation persistence across messages")
        print("✅ Memory continuity in new sessions")
        print("✅ Multi-customer memory isolation")
        print("✅ Real-world chatbot flow simulation")

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

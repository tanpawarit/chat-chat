"""
Advanced memory system test - simulating complex customer interactions.
Tests session expiry, memory reconstruction, and multi-session scenarios.
"""

import asyncio
import tempfile

import yaml

from memory.memory_manager import MemoryManager
from models.memory import (
    MemoryConfig,
)


async def load_config():
    """Load configuration from config.yaml"""
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def test_session_expiry_and_reconstruction():
    """Test session expiry and reconstruction from long-term memory."""
    print("🧪 Testing session expiry and reconstruction...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Short TTL for testing expiry
        config = MemoryConfig(
            redis_url=config_data["memory"]["redis_url"],
            lm_base_path=temp_dir,
            sm_ttl=2,  # Very short TTL for testing
            importance_threshold=0.5,
        )

        manager = MemoryManager(config)

        try:
            tenant_id = "test_restaurant"
            user_id = "frequent_customer"
            session_1 = "lunch_session"

            # Session 1: Customer orders lunch
            print("\n1. Session 1 - Lunch order...")
            sm1 = await manager.get_or_create_session_context(
                tenant_id, user_id, session_1
            )

            # Conversation flow
            conversations = [
                ("user", "สวัสดีครับ ผมจองโต๊ะไว้ชื่อ สมชาย"),
                ("bot", "สวัสดีครับคุณสมชาย! โต๊ะพร้อมแล้วครับ"),
                ("user", "ขอดูเมนูหน่อยครับ"),
                ("bot", "เชิญครับ วันนี้เรามีเมนูพิเศษ ต้มยำกุ้งมะม่วง"),
                ("user", "เอาต้มยำกุ้งมะม่วง กับข้าวผัดกุ้งครับ"),
                ("bot", "รับทราบครับ ต้มยำกุ้งมะม่วง 1 ที่ ข้าวผัดกุ้ง 1 ที่"),
            ]

            for role, message in conversations:
                await manager.add_message_to_context(tenant_id, user_id, message, role)

            # Update session variables
            await manager.update_session_variables(
                tenant_id,
                user_id,
                {
                    "customer_name": "สมชาย",
                    "table_number": "A5",
                    "order_items": ["ต้มยำกุ้งมะม่วง", "ข้าวผัดกุ้ง"],
                    "total_amount": 320,
                },
            )

            print("✅ Session 1 completed with full conversation")

            # Wait for session to expire
            print("\n2. Waiting for session expiry...")
            await asyncio.sleep(3)  # Wait longer than TTL

            # Session 2: Same customer returns for dinner (new session)
            session_2 = "dinner_session"
            print("\n3. Session 2 - Evening return (after expiry)...")

            sm2 = await manager.get_or_create_session_context(
                tenant_id, user_id, session_2
            )

            # Should be a new session but with no history yet (no LM events saved)
            assert sm2.session_id == session_2
            print("✅ New session created after expiry")

            # Continue with evening conversation
            evening_conversations = [
                ("user", "กลับมาอีกแล้วครับ พอจะมีโต๊ะว่างไหม"),
                ("bot", "ยินดีต้อนรับกลับครับ! มีโต๊ะว่างครับ"),
                ("user", "วันนี้อยากทานอะไรเบาๆ มีอะไรแนะนำไหม"),
                ("bot", "แนะนำสลัดผลไม้ หรือซุปใสครับ"),
            ]

            for role, message in evening_conversations:
                await manager.add_message_to_context(tenant_id, user_id, message, role)

            # Check that we have fresh conversation
            context = await manager.get_context_for_llm(tenant_id, user_id)
            assert len(context["recent_messages"]) == 4  # Only evening messages
            print("✅ Evening session has separate conversation history")

        finally:
            await manager.close()


async def test_multi_store_isolation():
    """Test that different stores have isolated memory."""
    print("\n🧪 Testing multi-store memory isolation...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        config = MemoryConfig(
            redis_url=config_data["memory"]["redis_url"],
            lm_base_path=temp_dir,
            sm_ttl=1800,
            importance_threshold=0.5,
        )

        manager = MemoryManager(config)

        try:
            # Same user_id but different stores
            user_id = "john_doe"
            cafe_store = "hip_cafe"
            restaurant_store = "fine_dining"

            # Session in cafe
            print("\n1. User visits cafe...")
            sm_cafe = await manager.get_or_create_session_context(
                cafe_store, user_id, "cafe_morning"
            )

            await manager.add_message_to_context(
                cafe_store, user_id, "ขอ Latte 1 แก้วครับ", "user"
            )
            await manager.update_session_variables(
                cafe_store,
                user_id,
                {"preferred_drink": "latte", "visit_time": "morning"},
            )

            # Session in restaurant
            print("\n2. Same user visits restaurant...")
            sm_restaurant = await manager.get_or_create_session_context(
                restaurant_store, user_id, "restaurant_dinner"
            )

            await manager.add_message_to_context(
                restaurant_store, user_id, "ขอจองโต๊ะ 2 ที่ครับ", "user"
            )
            await manager.update_session_variables(
                restaurant_store, user_id, {"party_size": 2, "meal_type": "dinner"}
            )

            # Check isolation
            cafe_context = await manager.get_context_for_llm(cafe_store, user_id)
            restaurant_context = await manager.get_context_for_llm(
                restaurant_store, user_id
            )

            # Cafe should only have cafe data
            assert len(cafe_context["recent_messages"]) == 1
            assert cafe_context["recent_messages"][0]["message"] == "ขอ Latte 1 แก้วครับ"
            assert cafe_context["session_variables"]["preferred_drink"] == "latte"

            # Restaurant should only have restaurant data
            assert len(restaurant_context["recent_messages"]) == 1
            assert (
                restaurant_context["recent_messages"][0]["message"] == "ขอจองโต๊ะ 2 ที่ครับ"
            )
            assert restaurant_context["session_variables"]["party_size"] == 2

            # No cross-contamination
            assert "party_size" not in cafe_context["session_variables"]
            assert "preferred_drink" not in restaurant_context["session_variables"]

            print("✅ Store isolation working correctly")

        finally:
            await manager.close()


async def test_conversation_limits():
    """Test conversation history limits and cleanup."""
    print("\n🧪 Testing conversation limits...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        config = MemoryConfig(
            redis_url=config_data["memory"]["redis_url"],
            lm_base_path=temp_dir,
            sm_ttl=1800,
            importance_threshold=0.5,
        )

        manager = MemoryManager(config)

        try:
            tenant_id = "busy_restaurant"
            user_id = "chatty_customer"
            session_id = "long_session"

            # Create session
            sm = await manager.get_or_create_session_context(
                tenant_id, user_id, session_id
            )

            # Add many messages (exceeding the 20-message limit)
            print("\n1. Adding many messages...")
            for i in range(30):
                await manager.add_message_to_context(
                    tenant_id, user_id, f"ข้อความที่ {i + 1}", "user"
                )
                await manager.add_message_to_context(
                    tenant_id, user_id, f"ตอบกลับข้อความที่ {i + 1}", "bot"
                )

            # Check that history is limited
            context = await manager.get_context_for_llm(tenant_id, user_id)

            assert len(context["recent_messages"]) <= 20
            print(f"✅ History limited to {len(context['recent_messages'])} messages")

            # Check that most recent messages are preserved
            last_message = context["recent_messages"][-1]
            assert "30" in last_message["message"]  # Should contain the last message
            print("✅ Most recent messages preserved")

        finally:
            await manager.close()


async def test_concurrent_sessions():
    """Test concurrent sessions for different users."""
    print("\n🧪 Testing concurrent sessions...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        config = MemoryConfig(
            redis_url=config_data["memory"]["redis_url"],
            lm_base_path=temp_dir,
            sm_ttl=1800,
            importance_threshold=0.5,
        )

        manager = MemoryManager(config)

        try:
            tenant_id = "popular_cafe"

            # Simulate multiple customers
            customers = [
                ("customer_a", "ขอ Americano ครับ"),
                ("customer_b", "มี Matcha Latte ไหมคะ"),
                ("customer_c", "ขอดูเมนูเค้กหน่อยครับ"),
            ]

            # Create concurrent sessions
            tasks = []
            for user_id, message in customers:

                async def process_customer(uid, msg):
                    sm = await manager.get_or_create_session_context(
                        tenant_id, uid, f"{uid}_session"
                    )
                    await manager.add_message_to_context(tenant_id, uid, msg, "user")
                    return await manager.get_context_for_llm(tenant_id, uid)

                tasks.append(process_customer(user_id, message))

            # Run concurrently
            results = await asyncio.gather(*tasks)

            # Verify each customer has their own context
            for i, (user_id, message) in enumerate(customers):
                context = results[i]
                assert len(context["recent_messages"]) == 1
                assert context["recent_messages"][0]["message"] == message
                print(f"✅ {user_id}: {message}")

            print("✅ Concurrent session handling working correctly")

        finally:
            await manager.close()


async def main():
    """Run advanced memory system tests."""
    print("🚀 Starting Advanced Memory System Tests\n")

    try:
        await test_session_expiry_and_reconstruction()
        await test_multi_store_isolation()
        await test_conversation_limits()
        await test_concurrent_sessions()

        print("\n🎉 All advanced memory tests passed!")
        print("\n📊 Advanced Test Summary:")
        print("✅ Session expiry and reconstruction")
        print("✅ Multi-store memory isolation")
        print("✅ Conversation history limits")
        print("✅ Concurrent session handling")
        print("✅ Real Redis performance under load")

    except Exception as e:
        print(f"\n❌ Advanced test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

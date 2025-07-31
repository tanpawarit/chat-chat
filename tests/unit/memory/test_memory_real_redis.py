"""
Test script for MemoryManager with real Redis from config.yaml
Tests the complete memory workflow with actual Redis connection.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from memory.lm_json_store import LongTermMemoryStore
from memory.memory_manager import MemoryManager

# Import our components
from models.memory import (
    EventType,
    LongTermMemory,
    MemoryConfig,
    MemoryEvent,
)


async def load_config():
    """Load configuration from config.yaml"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found")

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def test_redis_connection():
    """Test Redis connection from config."""
    print("🧪 Testing Redis connection...")

    config_data = await load_config()
    redis_url = config_data["memory"]["redis_url"]

    # Create memory config
    config = MemoryConfig(
        redis_url=redis_url,
        lm_base_path=config_data["memory"]["lm_base_path"],
        sm_ttl=config_data["memory"]["sm_ttl"],
        importance_threshold=config_data["memory"]["importance_threshold"],
    )

    # Test connection
    manager = MemoryManager(config)

    try:
        # Try a simple Redis operation
        await manager.redis.ping()
        print("✅ Redis connection successful")
        return manager, config
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        raise
    finally:
        # Don't close yet, return for further tests
        pass


async def test_real_memory_workflow():
    """Test the complete memory workflow with real Redis."""
    print("\n🧪 Testing real memory workflow...")

    manager, config = await test_redis_connection()

    try:
        # Test data
        tenant_id = "test_cafe"
        user_id = f"customer_{datetime.now().strftime('%H%M%S')}"  # Unique per test
        session_id = "session_real_001"

        print(f"Using test user: {user_id}")

        # Test 1: Create new session context
        print("\n1. Creating new session context...")
        sm = await manager.get_or_create_session_context(tenant_id, user_id, session_id)

        assert sm is not None
        assert sm.tenant_id == tenant_id
        assert sm.user_id == user_id
        print("✅ Session context created")

        # Test 2: Add messages
        print("\n2. Adding messages to context...")
        sm1 = await manager.add_message_to_context(
            tenant_id, user_id, "สวัสดีครับ ผมอยากสั่งกาแฟ", "user"
        )
        assert sm1 is not None
        assert len(sm1.history) == 1
        print("✅ User message added")

        sm2 = await manager.add_message_to_context(
            tenant_id, user_id, "สวัสดีครับ! เรามีกาแฟหลายชนิดเลยครับ อยากได้แบบไหนดีครับ", "bot"
        )
        assert len(sm2.history) == 2
        print("✅ Bot response added")

        # Test 3: Update session variables
        print("\n3. Updating session variables...")
        success = await manager.update_session_variables(
            tenant_id,
            user_id,
            {"language": "th", "intent": "order_coffee", "customer_mood": "friendly"},
        )
        assert success is True
        print("✅ Session variables updated")

        # Test 4: Get LLM context
        print("\n4. Getting LLM context...")
        context = await manager.get_context_for_llm(tenant_id, user_id)

        assert "recent_messages" in context
        assert "session_variables" in context
        assert len(context["recent_messages"]) == 2
        assert context["session_variables"]["language"] == "th"
        assert context["session_variables"]["intent"] == "order_coffee"
        print("✅ LLM context retrieved")

        # Test 5: Session persistence (reload from Redis)
        print("\n5. Testing session persistence...")
        sm3 = await manager.get_or_create_session_context(
            tenant_id, user_id, session_id
        )

        assert sm3 is not None
        assert len(sm3.history) == 2
        assert sm3.variables["language"] == "th"
        assert sm3.variables["intent"] == "order_coffee"
        print("✅ Session persisted in Redis")

        # Test 6: More conversation
        print("\n6. Continuing conversation...")
        await manager.add_message_to_context(
            tenant_id, user_id, "ขอ Americano ร้อน 1 แก้วครับ", "user"
        )
        await manager.add_message_to_context(
            tenant_id, user_id, "รับทราบครับ Americano ร้อน 1 แก้ว ราคา 65 บาทครับ", "bot"
        )

        # Check final state
        final_context = await manager.get_context_for_llm(tenant_id, user_id)
        assert len(final_context["recent_messages"]) == 4
        print("✅ Extended conversation stored")

        print("\n📊 Final conversation history:")
        for i, msg in enumerate(final_context["recent_messages"], 1):
            print(f"  {i}. [{msg['role']}]: {msg['message']}")

        print("\n📊 Session variables:")
        for k, v in final_context["session_variables"].items():
            print(f"  {k}: {v}")

    finally:
        await manager.close()
        print("\n🎉 Real Redis memory workflow test completed!")


async def test_memory_with_longterm():
    """Test memory system with long-term memory integration."""
    print("\n🧪 Testing memory with long-term integration...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create config with temp directory
        config = MemoryConfig(
            redis_url=config_data["memory"]["redis_url"],
            lm_base_path=temp_dir,  # Use temp dir for testing
            sm_ttl=config_data["memory"]["sm_ttl"],
            importance_threshold=0.6,  # Lower threshold for testing
        )

        manager = MemoryManager(config)

        try:
            # Pre-populate some long-term memory
            lm_store = LongTermMemoryStore(config)
            lm = LongTermMemory(
                tenant_id="cafe_premium",
                user_id="vip_customer_001",
                attributes={
                    "language": "th",
                    "membership": "gold",
                    "preferences": ["americano", "hot_drinks"],
                },
                history_summary="ลูกค้า VIP ที่ชอบสั่ง Americano ร้อน เป็นคนสุภาพและมักให้ทิป",
            )

            # Add historical events
            historical_events = [
                MemoryEvent(
                    event_type=EventType.TRANSACTION,
                    payload={
                        "order": "Americano Hot",
                        "amount": 65,
                        "tip": 10,
                        "payment": "credit_card",
                    },
                    importance_score=0.8,
                ),
                MemoryEvent(
                    event_type=EventType.FEEDBACK,
                    payload={
                        "rating": 5,
                        "comment": "กาแฟอร่อยมาก บริการดีครับ",
                        "sentiment": "very_positive",
                    },
                    importance_score=0.9,
                ),
            ]

            for event in historical_events:
                lm.add_event(event)

            await lm_store.save_memory(lm)
            print("✅ Long-term memory pre-populated")

            # Test: Create session context (should load from LM)
            print("\n1. Creating session with LM history...")
            sm = await manager.get_or_create_session_context(
                "cafe_premium", "vip_customer_001", "vip_session_001"
            )

            assert sm is not None
            assert sm.summary == "ลูกค้า VIP ที่ชอบสั่ง Americano ร้อน เป็นคนสุภาพและมักให้ทิป"
            assert sm.variables["user_preferences"]["membership"] == "gold"
            assert sm.variables["has_history"] is True
            print("✅ Session context created with LM history")

            # Test: Get enriched LLM context
            print("\n2. Getting enriched LLM context...")
            context = await manager.get_context_for_llm(
                "cafe_premium", "vip_customer_001"
            )

            assert "user_attributes" in context
            assert "history_summary" in context
            assert "important_events" in context
            assert context["user_attributes"]["membership"] == "gold"
            assert len(context["important_events"]) == 2
            print("✅ Enriched LLM context with historical data")

            print("\n📊 User Profile:")
            print(f"  Membership: {context['user_attributes']['membership']}")
            print(f"  Preferences: {context['user_attributes']['preferences']}")
            print(f"  History Summary: {context['history_summary']}")

            print("\n📊 Important Events:")
            for event in context["important_events"]:
                print(
                    f"  - {event['type']}: {event['payload']} (score: {event['importance']})"
                )

        finally:
            await manager.close()
            print("\n🎉 Long-term memory integration test completed!")


async def main():
    """Run all memory tests with real Redis."""
    print("🚀 Starting Real Redis Memory System Tests\n")

    try:
        await test_real_memory_workflow()
        await test_memory_with_longterm()

        print("\n🎉 All real Redis memory tests passed!")
        print("\n📊 Test Summary:")
        print("✅ Real Redis connection and operations")
        print("✅ Session context creation and persistence")
        print("✅ Message addition and conversation flow")
        print("✅ Session variables management")
        print("✅ LLM context generation")
        print("✅ Long-term memory integration")
        print("✅ Historical data enrichment")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

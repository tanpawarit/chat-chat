"""
Simple test script for memory system integration.
Tests basic functionality without external dependencies.
"""

import asyncio
import tempfile
from pathlib import Path

from memory.lm_json_store import LongTermMemoryStore
from models.memory import (
    EventType,
    LongTermMemory,
    MemoryConfig,
    MemoryEvent,
    ShortTermMemory,
)


async def test_memory_models():
    """Test basic memory model creation and validation."""
    print("🧪 Testing memory models...")

    # Test EventType enum
    assert EventType.INQUIRY.value == "INQUIRY"
    assert EventType.FEEDBACK.value == "FEEDBACK"
    print("✅ EventType enum works")

    # Test MemoryEvent creation
    event = MemoryEvent(
        event_type=EventType.INQUIRY,
        payload={"question": "Test question", "category": "general"},
        importance_score=0.7,
    )
    assert event.event_type == EventType.INQUIRY
    assert event.importance_score == 0.7
    print("✅ MemoryEvent creation works")

    # Test ShortTermMemory creation
    sm = ShortTermMemory(
        tenant_id="test_store",
        user_id="test_user",
        session_id="test_session",
        summary="",
        state="awaiting_input",
        last_intent=None,
        expires_at=None
    )
    assert sm.tenant_id == "test_store"
    assert sm.user_id == "test_user"
    assert len(sm.history) == 0
    print("✅ ShortTermMemory creation works")

    # Test LongTermMemory creation
    lm = LongTermMemory(tenant_id="test_store", user_id="test_user")
    lm.add_event(event)
    assert len(lm.events) == 1
    assert lm.events[0].event_type == EventType.INQUIRY
    print("✅ LongTermMemory creation and event addition works")


async def test_json_store():
    """Test JSON-based long-term memory storage."""
    print("\n🧪 Testing JSON storage...")

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        config = MemoryConfig(
            redis_url="redis://localhost:6379/0",  # Not used in this test
            lm_base_path=temp_dir,
            max_events_per_user=100,
            importance_threshold=0.5,
        )

        store = LongTermMemoryStore(config)

        # Test storing and loading memory
        lm = LongTermMemory(
            tenant_id="test_tenant",
            user_id="test_user",
            attributes={"language": "th", "segment": "VIP"},
        )

        # Add some test events
        events = [
            MemoryEvent(
                event_type=EventType.INQUIRY,
                payload={"question": "ราคาสินค้า", "category": "pricing"},
                importance_score=0.8,
            ),
            MemoryEvent(
                event_type=EventType.FEEDBACK,
                payload={"sentiment": "positive", "message": "ดีมาก"},
                importance_score=0.6,
            ),
            MemoryEvent(
                event_type=EventType.COMPLAINT,
                payload={"issue": "สินค้าชำรุด", "severity": "high"},
                importance_score=0.9,
            ),
        ]

        for event in events:
            lm.add_event(event)

        # Test save
        success = await store.save_memory(lm)
        assert success, "Failed to save memory"
        print("✅ Memory save works")

        # Test load
        loaded_lm = await store.load_memory("test_tenant", "test_user")
        assert loaded_lm is not None, "Failed to load memory"
        assert loaded_lm.tenant_id == "test_tenant"
        assert loaded_lm.user_id == "test_user"
        assert len(loaded_lm.events) == 3
        print("✅ Memory load works")

        # Test important events filtering
        important_events = loaded_lm.get_important_events(min_score=0.7)
        assert len(important_events) == 2  # INQUIRY (0.8) and COMPLAINT (0.9)
        print("✅ Important events filtering works")

        # Test recent events
        recent_events = loaded_lm.get_recent_events(limit=2)
        assert len(recent_events) == 2
        print("✅ Recent events retrieval works")

        # Test adding individual event
        new_event = MemoryEvent(
            event_type=EventType.TRANSACTION,
            payload={"amount": 1500, "product": "coffee"},
            importance_score=0.9,
        )

        success = await store.add_event("test_tenant", "test_user", new_event)
        assert success, "Failed to add individual event"

        # Verify event was added
        updated_lm = await store.load_memory("test_tenant", "test_user")
        assert len(updated_lm.events) == 4
        print("✅ Individual event addition works")

        # Test file structure
        tenant_dir = Path(temp_dir) / "test_tenant"
        user_file = tenant_dir / "test_user.json"
        assert tenant_dir.exists(), "Tenant directory not created"
        assert user_file.exists(), "User file not created"
        print("✅ File structure creation works")


async def test_memory_config():
    """Test memory configuration."""
    print("\n🧪 Testing memory configuration...")

    config = MemoryConfig(
        redis_url="redis://localhost:6379/0",
        lm_base_path="data/longterm",
        sm_ttl=1800,
        max_events_per_user=1000,
        importance_threshold=0.5,
    )

    assert config.redis_url == "redis://localhost:6379/0"
    assert config.lm_base_path == "data/longterm"
    assert config.sm_ttl == 1800
    assert config.importance_threshold == 0.5
    print("✅ MemoryConfig creation works")


async def test_business_agnostic_design():
    """Test that the system works for different business scenarios."""
    print("\n🧪 Testing business-agnostic design...")

    # E-commerce scenario
    ecommerce_events = [
        MemoryEvent(
            event_type=EventType.INQUIRY,
            payload={"question": "Product availability", "product_id": "PROD123"},
            importance_score=0.6,
        ),
        MemoryEvent(
            event_type=EventType.TRANSACTION,
            payload={"order_id": "ORD456", "amount": 2500, "status": "completed"},
            importance_score=0.9,
        ),
    ]

    # Restaurant scenario
    restaurant_events = [
        MemoryEvent(
            event_type=EventType.REQUEST,
            payload={
                "request_type": "reservation",
                "party_size": 4,
                "date": "2025-08-01",
            },
            importance_score=0.8,
        ),
        MemoryEvent(
            event_type=EventType.FEEDBACK,
            payload={"rating": 5, "comment": "Excellent service", "dish": "Pad Thai"},
            importance_score=0.7,
        ),
    ]

    # Education scenario
    education_events = [
        MemoryEvent(
            event_type=EventType.INQUIRY,
            payload={"course": "Python101", "question": "Prerequisites required?"},
            importance_score=0.5,
        ),
        MemoryEvent(
            event_type=EventType.SUPPORT,
            payload={"issue": "Login problem", "urgency": "medium"},
            importance_score=0.6,
        ),
    ]

    # Test that all scenarios work with the same system
    scenarios = [
        ("ecommerce", ecommerce_events),
        ("restaurant", restaurant_events),
        ("education", education_events),
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        config = MemoryConfig(
            redis_url="redis://localhost:6379/0",
            lm_base_path=temp_dir,
            importance_threshold=0.5,
        )
        store = LongTermMemoryStore(config)

        for business_type, events in scenarios:
            lm = LongTermMemory(
                tenant_id=f"{business_type}_store",
                user_id="customer123",
                attributes={"business_type": business_type},
            )

            for event in events:
                lm.add_event(event)

            # Save and verify
            success = await store.save_memory(lm)
            assert success, f"Failed to save {business_type} memory"

            loaded_lm = await store.load_memory(f"{business_type}_store", "customer123")
            assert loaded_lm is not None, f"Failed to load {business_type} memory"
            assert len(loaded_lm.events) == len(events)

        print("✅ Multi-business scenario support works")


async def main():
    """Run all tests."""
    print("🚀 Starting Memory System Tests\n")

    try:
        await test_memory_models()
        await test_json_store()
        await test_memory_config()
        await test_business_agnostic_design()

        print("\n🎉 All tests passed! Memory system is working correctly.")
        print("\n📊 Test Summary:")
        print("✅ Memory models creation and validation")
        print("✅ JSON-based long-term memory storage")
        print("✅ Event filtering and retrieval")
        print("✅ File structure management")
        print("✅ Configuration handling")
        print("✅ Business-agnostic design verification")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

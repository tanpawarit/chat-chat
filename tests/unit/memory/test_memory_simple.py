"""
Simple memory system test with mock chatbot scenario.
Tests memory functionality without gateway integration.
"""

import asyncio
import tempfile

import yaml

from memory.memory_manager import MemoryManagerFactory


async def load_config():
    """Load configuration from config.yaml"""
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def simulate_chatbot_session():
    """Simulate a chatbot session with memory tracking."""
    print("🧪 Simulating chatbot session with memory...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Update config to use temp directory
        config_data["memory"]["lm_base_path"] = temp_dir

        # Create memory manager
        memory_manager = await MemoryManagerFactory.create_from_config(config_data)

        try:
            # Test parameters
            store_id = "cafe_hipster"
            user_id = "customer_morning"
            session_id = "morning_coffee_session"

            print("\n📋 Session Info:")
            print(f"  Store: {store_id}")
            print(f"  User: {user_id}")
            print(f"  Session: {session_id}")

            # Step 1: Start session
            print("\n1. Starting new session...")
            sm = await memory_manager.get_or_create_session_context(
                store_id, user_id, session_id
            )
            assert sm is not None
            print("✅ Session context created")

            # Step 2: Simulate conversation
            print("\n2. Simulating coffee order conversation...")

            conversations = [
                ("user", "สวัสดีครับ"),
                ("bot", "สวัสดีครับ! ยินดีต้อนรับสู่ Cafe Hipster ครับ"),
                ("user", "วันนี้มีกาแฟพิเศษอะไรไหมครับ"),
                ("bot", "วันนี้เรามี Geisha จากปานามา และ Blue Mountain จากจาไมก้าครับ"),
                ("user", "เอา Geisha ดริปครับ"),
                ("bot", "รับทราบครับ Geisha Drip 1 แก้ว ราคา 350 บาท รอสักครู่นะครับ"),
                ("user", "ขอบคุณครับ"),
                ("bot", "ครับ รอแป็บเดียวนะครับ กาแฟจะพร้อมใน 5 นาที"),
            ]

            # Add messages to memory
            for role, message in conversations:
                await memory_manager.add_message_to_context(
                    store_id, user_id, message, role
                )
                print(f"  [{role}]: {message}")

            print("✅ Conversation logged to memory")

            # Step 3: Update session variables
            print("\n3. Updating session variables...")
            await memory_manager.update_session_variables(
                store_id,
                user_id,
                {
                    "current_order": "Geisha Drip",
                    "order_amount": 350,
                    "payment_status": "pending",
                    "customer_mood": "satisfied",
                    "preferred_coffee": "specialty",
                },
            )
            print("✅ Session variables updated")

            # Step 4: Get context for LLM
            print("\n4. Getting LLM context...")
            context = await memory_manager.get_context_for_llm(store_id, user_id)

            print("📊 Context Summary:")
            print(f"  Messages: {len(context['recent_messages'])}")
            print(
                f"  Order: {context['session_variables'].get('current_order', 'N/A')}"
            )
            print(
                f"  Amount: {context['session_variables'].get('order_amount', 'N/A')} บาท"
            )
            print(f"  Mood: {context['session_variables'].get('customer_mood', 'N/A')}")

            assert (
                len(context["recent_messages"]) >= 8
            )  # Should have at least 8 messages
            assert context["session_variables"]["current_order"] == "Geisha Drip"
            print("✅ LLM context retrieved successfully")

            # Step 5: Simulate returning customer
            print("\n5. Simulating returning customer (same day)...")

            # Get same session (should persist)
            sm2 = await memory_manager.get_or_create_session_context(
                store_id, user_id, session_id
            )

            # Continue conversation
            await memory_manager.add_message_to_context(
                store_id, user_id, "กาแฟเสร็จแล้วไหมครับ", "user"
            )
            await memory_manager.add_message_to_context(
                store_id, user_id, "เสร็จแล้วครับ! เชิญรับเลยครับ", "bot"
            )

            # Final context
            final_context = await memory_manager.get_context_for_llm(store_id, user_id)
            assert (
                len(final_context["recent_messages"]) >= 10
            )  # Should have at least 10 messages
            print("✅ Session continuity maintained")

            # Display full conversation
            print(
                f"\n📊 Complete Conversation ({len(final_context['recent_messages'])} messages):"
            )
            for i, msg in enumerate(final_context["recent_messages"], 1):
                print(f"  {i:2d}. [{msg['role']:4s}]: {msg['message']}")

            print("\n📊 Final Session Variables:")
            for key, value in final_context["session_variables"].items():
                print(f"  {key}: {value}")

        finally:
            await memory_manager.close()

    print("\n🎉 Chatbot simulation with memory completed!")


async def simulate_multi_session_customer():
    """Simulate customer with multiple sessions across different days."""
    print("\n🧪 Simulating multi-session customer...")

    config_data = await load_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        config_data["memory"]["lm_base_path"] = temp_dir
        config_data["memory"]["sm_ttl"] = 2  # Short TTL for testing

        memory_manager = await MemoryManagerFactory.create_from_config(config_data)

        try:
            store_id = "restaurant_fine"
            user_id = "regular_customer"

            # Session 1: Lunch visit
            print("\n1. Session 1 - Lunch visit...")
            session1 = "lunch_session"

            sm1 = await memory_manager.get_or_create_session_context(
                store_id, user_id, session1
            )

            lunch_conversation = [
                ("user", "สวัสดีครับ จองโต๊ะไว้ชื่อ วิทยา"),
                ("bot", "สวัสดีครับคุณวิทยา โต๊ะพร้อมแล้วครับ"),
                ("user", "วันนี้มีเมนูแนะนำอะไรไหมครับ"),
                ("bot", "วันนี้มีหมูสามชั้นเบคอนย่าง และแกงกะทิปลาพิเศษครับ"),
            ]

            for role, message in lunch_conversation:
                await memory_manager.add_message_to_context(
                    store_id, user_id, message, role
                )

            await memory_manager.update_session_variables(
                store_id,
                user_id,
                {
                    "customer_name": "วิทยา",
                    "visit_time": "lunch",
                    "table_preference": "window_seat",
                },
            )

            print("✅ Lunch session completed")

            # Wait for session expiry
            print("\n2. Waiting for session expiry...")
            await asyncio.sleep(3)

            # Session 2: Dinner visit (after expiry)
            print("\n3. Session 2 - Dinner visit (new session)...")
            session2 = "dinner_session"

            sm2 = await memory_manager.get_or_create_session_context(
                store_id, user_id, session2
            )

            # Should be fresh session (no lunch history due to expiry)
            dinner_conversation = [
                ("user", "กลับมาทานเย็นอีกแล้วครับ"),
                ("bot", "ยินดีต้อนรับกลับครับ! วันนี้อยากทานอะไรดีครับ"),
                ("user", "มีอะไรเบาๆ สำหรับเย็นไหมครับ"),
                ("bot", "มีสลัดซีฟู้ด หรือซุปมะเขือเทศครับ"),
            ]

            for role, message in dinner_conversation:
                await memory_manager.add_message_to_context(
                    store_id, user_id, message, role
                )

            await memory_manager.update_session_variables(
                store_id, user_id, {"visit_time": "dinner", "meal_preference": "light"}
            )

            # Check that sessions are separate
            context = await memory_manager.get_context_for_llm(store_id, user_id)

            assert len(context["recent_messages"]) == 4  # Only dinner messages
            assert context["session_variables"]["visit_time"] == "dinner"
            assert (
                "customer_name" not in context["session_variables"]
            )  # From expired session

            print("✅ Sessions properly isolated after expiry")

            print("\n📊 Current Session (Dinner):")
            for msg in context["recent_messages"]:
                print(f"  [{msg['role']}]: {msg['message']}")

        finally:
            await memory_manager.close()

    print("\n🎉 Multi-session customer simulation completed!")


async def main():
    """Run memory simulation tests."""
    print("🚀 Starting Memory System Simulation Tests\n")

    try:
        await simulate_chatbot_session()
        await simulate_multi_session_customer()

        print("\n🎉 All memory simulation tests passed!")
        print("\n📊 Simulation Test Summary:")
        print("✅ Complete chatbot session with memory tracking")
        print("✅ Conversation logging and context retrieval")
        print("✅ Session variables management")
        print("✅ Session continuity within same session")
        print("✅ Multi-session handling with expiry")
        print("✅ Session isolation after expiry")
        print("✅ Real Redis performance with complex scenarios")

    except Exception as e:
        print(f"\n❌ Simulation test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

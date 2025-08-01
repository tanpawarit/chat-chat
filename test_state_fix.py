#!/usr/bin/env python3
"""
Test script to verify state transitions are working correctly.
"""

import asyncio
import logging
from datetime import datetime
from memory.memory_manager import MemoryManager
from memory.memory_manager import MemoryManagerFactory

logging.basicConfig(level=logging.INFO)

async def test_state_transitions():
    """Test the state transition flow."""
    
    # Mock configuration
    config_dict = {
        "openrouter": {"api_key": "test-key"},
        "memory": {
            "redis_url": "redis://localhost:6379",
            "lm_base_path": "data/test_longterm",
            "sm_ttl": 1800,
            "importance_threshold": 0.3
        }
    }
    
    try:
        # Create memory manager
        memory_manager = await MemoryManagerFactory.create_from_config(config_dict)
        
        tenant_id = "test_store"
        user_id = "test_user"
        session_id = "test_session"
        
        print("=== Testing State Transitions ===")
        
        # Step 1: Create fresh session
        sm = await memory_manager.get_or_create_session_context(
            tenant_id, user_id, session_id
        )
        print(f"1. Initial state: {sm.state}")
        
        # Step 2: Add user message (should set processing_request)
        sm = await memory_manager.add_message_to_context(
            tenant_id, user_id, "Hello, I need help", "user"
        )
        print(f"2. After user message: {sm.state}")
        
        # Step 3: Manually set to completed (simulating gateway behavior)
        success = await memory_manager.update_session_state(
            tenant_id, user_id, "completed"
        )
        print(f"3. After setting completed: {success}")
        
        # Step 4: Verify final state
        sm = await memory_manager._load_sm(tenant_id, user_id)
        print(f"4. Final state: {sm.state}")
        
        # Step 5: Test error state
        success = await memory_manager.update_session_state(
            tenant_id, user_id, "error", {"error": "test error"}
        )
        sm = await memory_manager._load_sm(tenant_id, user_id)
        print(f"5. After error state: {sm.state}")
        
        await memory_manager.close()
        print("✅ State transition test completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_state_transitions())
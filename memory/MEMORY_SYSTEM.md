# Memory System Architecture & Flow

## Overview

The chat-chat memory system implements a dual-layer memory architecture designed for multi-tenant chatbot applications. It combines **Short-term Memory (SM)** for active conversation context and **Long-term Memory (LM)** for persistent user attributes and important events.

## Architecture Components

### Core Components

1. **MemoryManager** (`memory_manager.py`)
   - Central orchestrator for SM and LM operations
   - Handles memory lifecycle and data flow
   - Implements expiry-based memory reconstruction

2. **EventProcessor** (`event_processor.py`)
   - LLM-powered message analysis and classification
   - Importance scoring (0.0-1.0) for event filtering
   - Fallback mechanisms for robust operation

3. **LongTermMemoryStore** (`lm_json_store.py`)
   - JSON file-based persistent storage for LM
   - Event retention and cleanup policies
   - User attribute management

4. **Memory Models** (`models/memory.py`)
   - Pydantic models for type safety and validation
   - Domain-agnostic event structures
   - Multi-tenant data organization

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Memory System Architecture"
        subgraph "Core Components"
            MM[MemoryManager<br/>Central Orchestrator]
            EP[EventProcessor<br/>LLM Analysis]
            LMS[LongTermMemoryStore<br/>JSON Persistence]
            Models[Memory Models<br/>Pydantic Schemas]
        end
        
        subgraph "Storage Layer"
            Redis[(Redis<br/>Short-term Memory<br/>TTL: 30min)]
            JSON[(JSON Files<br/>Long-term Memory<br/>Persistent)]
        end
        
        subgraph "External Services"
            OpenRouter[OpenRouter API<br/>GPT-4o-mini]
            BotGateway[Bot Gateway<br/>Message Handler]
        end
        
        MM --> Redis
        MM --> LMS
        LMS --> JSON
        MM --> EP
        EP --> OpenRouter
        BotGateway --> MM
        Models --> MM
        Models --> EP
        Models --> LMS
    end
```

## Memory System Flow

### 1. Session Context Retrieval Flow

```mermaid
flowchart TD
    Start([New User Message]) --> GetContext[get_or_create_session_context]
    GetContext --> CheckSM{SM exists in Redis?}
    
    CheckSM -->|Yes| CheckExpiry{SM expired?}
    CheckExpiry -->|No| ReturnSM[Return existing SM]
    CheckExpiry -->|Yes| LoadLM[Load LM from JSON]
    
    CheckSM -->|No| LoadLM
    LoadLM --> LMExists{LM file exists?}
    
    LMExists -->|Yes| CreateFromLM[Create SM from LM<br/>- Copy summary<br/>- Set attributes<br/>- Apply preferences]
    LMExists -->|No| CreateEmpty[Create empty SM]
    
    CreateFromLM --> SaveSM[Save SM to Redis<br/>with TTL]
    CreateEmpty --> SaveSM
    SaveSM --> ReturnSM
    
    ReturnSM --> End([SM Ready])
    
    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style CheckSM fill:#fff3e0
    style CheckExpiry fill:#fff3e0
    style LMExists fill:#fff3e0
```

### 2. Message Processing Flow

```mermaid
flowchart TD
    Start([User Message]) --> AddToSM[Add message to SM history]
    AddToSM --> LimitHistory[Limit history to 20 messages]
    LimitHistory --> UserMsg{Message role = 'user'?}
    
    UserMsg -->|Yes| ProcessLLM[EventProcessor.analyze_message]
    UserMsg -->|No| SaveSM[Save updated SM to Redis]
    
    ProcessLLM --> LLMCall[OpenRouter API Call<br/>- Classify event type<br/>- Calculate importance<br/>- Extract payload]
    
    LLMCall --> LLMSuccess{LLM Success?}
    LLMSuccess -->|No| Fallback[Fallback classification<br/>keyword-based rules]
    LLMSuccess -->|Yes| CreateEvent[Create MemoryEvent]
    Fallback --> CreateEvent
    
    CreateEvent --> CheckImportance{Importance ≥ threshold?}
    CheckImportance -->|Yes| SaveToLM[Save event to LM JSON]
    CheckImportance -->|No| SaveSM
    
    SaveToLM --> UpdateLM[Update LM attributes<br/>and summary]
    UpdateLM --> SaveSM
    SaveSM --> End([SM Updated])
    
    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style UserMsg fill:#fff3e0
    style LLMSuccess fill:#fff3e0
    style CheckImportance fill:#fff3e0
```

### 3. LLM Context Generation Flow

```mermaid
flowchart TD
    Start([Generate LLM Context]) --> LoadSM[Load SM from Redis]
    LoadSM --> SMExists{SM exists?}
    
    SMExists -->|No| Error[Return error context]
    SMExists -->|Yes| BuildContext[Build base context<br/>- Recent messages<br/>- Current state<br/>- Session variables]
    
    BuildContext --> IncludeSummary{Include summary?}
    IncludeSummary -->|Yes| AddSummary[Add conversation summary]
    IncludeSummary -->|No| LoadLM[Load LM from JSON]
    AddSummary --> LoadLM
    
    LoadLM --> LMExists{LM exists?}
    LMExists -->|Yes| AddLMData[Add LM data<br/>- User attributes<br/>- History summary<br/>- Important events]
    LMExists -->|No| Return[Return context]
    
    AddLMData --> ImportantEvents[Filter important events<br/>min_score ≥ 0.7]
    ImportantEvents --> AddEvents[Add last 5 important events]
    AddEvents --> Return
    Return --> End([Context Ready])
    
    Error --> End
    
    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style SMExists fill:#fff3e0
    style IncludeSummary fill:#fff3e0
    style LMExists fill:#fff3e0
```

### 4. Event Classification Flow

```mermaid
flowchart TD
    Start([Message Analysis]) --> PreparePrompt[Prepare LLM prompt<br/>- System instructions<br/>- Message content<br/>- Context data]
    
    PreparePrompt --> LLMCall[OpenRouter API Call<br/>GPT-4o-mini]
    LLMCall --> ParseResponse{Parse JSON response?}
    
    ParseResponse -->|Success| ExtractData[Extract:<br/>- Event type<br/>- Importance score<br/>- Payload data<br/>- Reasoning]
    
    ParseResponse -->|Failed| FallbackRules[Keyword-based fallback<br/>- Thai/English keywords<br/>- Basic classification<br/>- Default importance]
    
    FallbackRules --> CreateEvent[Create MemoryEvent]
    ExtractData --> EnhancePayload[Enhance payload<br/>- Original message<br/>- Language detection<br/>- Context metadata]
    
    EnhancePayload --> CreateEvent
    CreateEvent --> End([MemoryEvent Ready])
    
    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style ParseResponse fill:#fff3e0
```

### 5. Multi-Tenant Data Flow

```mermaid
flowchart LR
    subgraph "Tenant A (store_001)"
        TenantA[Messages] --> SMA[SM: store_001:user123]
        SMA --> RedisA[(Redis)]
        SMA --> LMA[LM: store_001/user123.json]
    end
    
    subgraph "Tenant B (store_002)"
        TenantB[Messages] --> SMB[SM: store_002:user456]
        SMB --> RedisB[(Redis)]
        SMB --> LMB[LM: store_002/user456.json]
    end
    
    subgraph "Storage Isolation"
        RedisA --> RedisStore[(Redis Server<br/>Isolated by key prefix)]
        RedisB --> RedisStore
        LMA --> FileSystemA[data/longterm/store_001/]
        LMB --> FileSystemB[data/longterm/store_002/]
    end
    
    style RedisStore fill:#ffcdd2
    style FileSystemA fill:#e8f5e8
    style FileSystemB fill:#e8f5e8
```

## Data Structures

### ShortTermMemory (Redis)

```python
{
    "tenant_id": "store_001",
    "user_id": "user123", 
    "session_id": "sess_20250730_001",
    "history": [
        {"role": "user", "message": "สวัสดีครับ"},
        {"role": "bot", "message": "สวัสดีค่ะ"}
    ],
    "summary": "User greeted, established communication",
    "state": "awaiting_input",
    "last_intent": "greeting",
    "variables": {
        "preferred_language": "th",
        "current_topic": "general"
    },
    "expires_at": "2025-07-30T12:00:00Z"
}
```

**TTL**: 30 minutes default (configurable)  
**Storage**: Redis with automatic expiry

### LongTermMemory (JSON Files)

```python
{
    "tenant_id": "store_001",
    "user_id": "user123",
    "events": [
        {
            "event_type": "INQUIRY",
            "payload": {
                "original_message": "ราคาสินค้านี้เท่าไหร่",
                "question_type": "pricing",
                "language": "th"
            },
            "importance_score": 0.8,
            "timestamp": "2025-07-30T10:30:00Z"
        }
    ],
    "attributes": {
        "preferred_language": "th",
        "customer_segment": "regular",
        "timezone": "Asia/Bangkok"
    },
    "history_summary": "Customer frequently asks about pricing"
}
```

**Persistence**: JSON files organized by tenant/user  
**Retention**: 365 days, 1000 events max per user

## Event Classification System

### Event Types (Domain-Agnostic)

| Type | Description | Examples |
|------|-------------|----------|
| `INQUIRY` | Questions, information requests | "ราคาเท่าไหร่?", "How does this work?" |
| `FEEDBACK` | Opinions, reviews, satisfaction | "ดีมาก", "Not satisfied with service" |
| `REQUEST` | Specific asks, assistance needs | "จองโต๊ะ", "Please help me with..." |
| `COMPLAINT` | Problems, issues, dissatisfaction | "สินค้าเสีย", "This doesn't work" |
| `TRANSACTION` | Purchase, payment, orders | "ซื้อ", "จ่ายเงิน", "Order #123" |
| `SUPPORT` | Help requests, guidance | "ช่วยได้ไหม", "I need assistance" |
| `INFORMATION` | Sharing details, providing data | "ที่อยู่คือ...", "My phone is..." |
| `GENERIC_EVENT` | General conversation | "สวัสดี", "Thank you" |

### Importance Scoring

| Score Range | Priority | Criteria | Action |
|-------------|----------|----------|---------|
| 0.9-1.0 | Critical | Transactions, urgent complaints | Always save to LM |
| 0.7-0.8 | Important | Specific requests, detailed feedback | Save to LM |
| 0.5-0.6 | Moderate | General support, basic inquiries | Save if above threshold |
| 0.3-0.4 | Low | Casual questions, general info | Usually filtered out |
| 0.1-0.2 | Minimal | Greetings, small talk | Filtered out |

## Configuration

### Memory Configuration

```python
MemoryConfig(
    redis_url="redis://localhost:6379/0",
    sm_ttl=1800,  # 30 minutes
    lm_base_path="data/longterm",
    max_events_per_user=1000,
    event_retention_days=365,
    importance_threshold=0.5  # Save events ≥ 0.5
)
```

### EventProcessor Configuration

```python
EventProcessor(
    api_key="your_openrouter_key",
    model="openai/gpt-4o-mini",  # Cost-optimized
    base_url="https://openrouter.ai/api/v1"
)
```

## Multi-Tenant Architecture

### Data Isolation

```
data/longterm/
├── tenant_001/
│   ├── user_001.json
│   ├── user_002.json
│   └── ...
├── tenant_002/
│   ├── user_001.json
│   └── ...
```

### Redis Key Structure

```
SM Keys: "sm:{tenant_id}:{user_id}"
Example: "sm:store_001:user123"
```

## API Usage Examples

### 1. Get Session Context

```python
memory_manager = MemoryManager(config)

# Get or create session context
sm = await memory_manager.get_or_create_session_context(
    tenant_id="store_001",
    user_id="user123", 
    session_id="sess_001"
)
```

### 2. Add Message

```python
# Add user message to context
sm = await memory_manager.add_message_to_context(
    tenant_id="store_001",
    user_id="user123",
    message="ราคาสินค้านี้เท่าไหร่ครับ",
    role="user",
    metadata={"platform": "line", "timestamp": "2025-07-30T10:30:00Z"}
)
```

### 3. Get LLM Context

```python
# Get formatted context for bot response
context = await memory_manager.get_context_for_llm(
    tenant_id="store_001",
    user_id="user123",
    include_summary=True,
    max_recent_messages=10
)

# Context includes:
# - recent_messages: Latest conversation
# - current_state: Session state
# - conversation_summary: LM summary
# - user_attributes: Persistent preferences
# - important_events: High-priority historical events
```

## Error Handling & Resilience

### Fallback Mechanisms

1. **LLM Failure**: Rule-based classification with keyword matching
2. **Redis Unavailable**: Create minimal SM for session continuity
3. **File I/O Errors**: Log errors, continue with available data
4. **Data Corruption**: Graceful degradation with empty structures

### Cleanup & Maintenance

```python
# Cleanup expired sessions
await memory_manager.cleanup_expired_sessions()

# Event retention (automatic during save)
# - Remove events older than retention_days
# - Keep only max_events_per_user most recent events
```

## Performance Considerations

### Optimization Strategies

1. **SM Caching**: Redis with TTL for fast access
2. **Lazy LM Loading**: Load LM only when SM expires
3. **Event Batching**: Process multiple events efficiently
4. **Async Operations**: Non-blocking I/O throughout
5. **JSON Optimization**: Atomic writes with temp files

### Scalability Features

- **Multi-tenant**: Isolated data per tenant
- **Horizontal Scale**: Redis clustering support
- **Storage Efficiency**: JSON compression options
- **Memory Limits**: Configurable event limits per user

## Integration Points

### Bot Gateway Integration Flow

```mermaid
sequenceDiagram
    participant User as User/Platform
    participant BG as Bot Gateway
    participant MM as MemoryManager
    participant EP as EventProcessor
    participant Redis as Redis (SM)
    participant LM as LongTermMemory
    participant LLM as LLM Service
    
    User->>BG: Send Message
    BG->>MM: get_or_create_session_context(tenant, user, session)
    
    MM->>Redis: Check SM exists & not expired
    alt SM Valid
        Redis-->>MM: Return existing SM
    else SM Invalid/Missing
        MM->>LM: Load LM from JSON
        MM->>MM: Create SM from LM context
        MM->>Redis: Save new SM with TTL
        Redis-->>MM: Confirm save
    end
    MM-->>BG: Return SM context
    
    BG->>MM: add_message_to_context(message, role="user")
    MM->>MM: Add to SM history
    MM->>EP: analyze_message(message, context)
    EP->>LLM: OpenRouter API call
    LLM-->>EP: Classification result
    EP-->>MM: MemoryEvent with importance
    
    alt Important Event (≥threshold)
        MM->>LM: Save event to JSON
        LM-->>MM: Confirm save
    end
    
    MM->>Redis: Update SM
    Redis-->>MM: Confirm update
    MM-->>BG: Updated SM
    
    BG->>MM: get_context_for_llm()
    MM->>Redis: Load current SM
    MM->>LM: Load LM attributes & events
    MM->>MM: Assemble rich context
    MM-->>BG: LLM context (history + attributes + events)
    
    BG->>LLM: generate_response(message, context)
    LLM-->>BG: Bot response
    
    BG->>MM: add_message_to_context(response, role="bot")
    MM->>Redis: Update SM with bot message
    MM-->>BG: Confirm update
    
    BG->>User: Send Bot Response
    
    Note over MM,LM: Automatic cleanup:<br/>- SM expires after TTL<br/>- LM events cleaned by retention policy
```

### Code Integration Example

```python
# In bot message handler
memory_manager = MemoryManagerFactory.create_from_config(config)

# Get context for incoming message
sm = await memory_manager.get_or_create_session_context(
    tenant_id=store.id,
    user_id=user.id,
    session_id=session.id
)

# Add user message
await memory_manager.add_message_to_context(
    tenant_id=store.id,
    user_id=user.id,
    message=incoming_message.text,
    role="user"
)

# Get context for LLM
llm_context = await memory_manager.get_context_for_llm(
    tenant_id=store.id,
    user_id=user.id
)

# Generate bot response with context
bot_response = await llm_service.generate_response(
    message=incoming_message.text,
    context=llm_context
)

# Add bot response to memory
await memory_manager.add_message_to_context(
    tenant_id=store.id,
    user_id=user.id,
    message=bot_response,
    role="bot"
)
```

## Future Enhancements

### Planned Features

1. **Memory Summarization**: Periodic LM summarization for efficiency
2. **Attribute Extraction**: Automatic user preference learning
3. **Cross-Session Analytics**: User behavior pattern analysis
4. **Memory Compression**: Efficient storage for large histories
5. **Real-time Updates**: WebSocket-based memory synchronization

### Advanced Capabilities

- **Semantic Search**: Vector-based event similarity search
- **User Clustering**: Similar user pattern identification
- **Predictive Context**: Proactive context preparation
- **Memory Migration**: Cross-platform user data portability
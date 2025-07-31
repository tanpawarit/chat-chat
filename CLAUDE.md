# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies with development extras
uv sync --extra dev

# Install all optional dependencies
uv sync --extra all

# Install production dependencies only
uv sync --extra production
```

### Running the Application
```bash
# Run the bot locally
uv run python main.py

# Run with specific host/port
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit           # Unit tests only
uv run pytest -m integration    # Integration tests only
uv run pytest -m "not slow"     # Skip slow tests

# Run with coverage
uv run pytest --cov=adapters --cov=models --cov=bot_gateway --cov-report=html
```

### Code Quality
```bash
# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run black .

# Type checking
uv run mypy .

# Run all quality checks
uv run ruff check . && uv run black . && uv run mypy .
```

## Architecture Overview

This is a **multi-store, multi-customer chatbot system** with a clean adapter architecture that normalizes messages across different platforms (LINE, Facebook, Telegram, etc.). The system supports multiple stores, where each store can have multiple customers, enabling scalable business-to-customer communication. 

### Core Architecture Pattern

**Adapter → Gateway → Processing → Response Flow**

1. **Platform Adapters** (`adapters/platforms/`): Convert platform-specific webhooks to normalized messages
2. **Bot Gateway** (`bot_gateway/gateway.py`): Central orchestration layer that processes normalized messages
3. **Models** (`models/`): Pydantic models for normalized data structures across platforms
4. **Configuration** (`config/`): YAML-based configuration with platform-specific settings

### Key Components

#### Platform Adapter System
- **Base Class**: `adapters/base/platform_base.py` - Abstract interface for all platforms
- **LINE Adapter**: `adapters/platforms/line_adapter.py` - LINE-specific implementation
- **Extensible**: Add new platforms by implementing the `PlatformAdapter` interface

#### Message Normalization
- **IncomingMessage**: Platform-agnostic representation of received messages
- **OutgoingMessage**: Platform-agnostic representation of responses
- **MessageType**: Enum for text, image, video, audio, sticker, location, etc.
- **User Model**: Normalized user representation with profile data
- **Store Model**: Store identification and configuration management
- **Customer Model**: Customer profile and relationship management per store

#### Gateway Processing
- **BotGateway**: Central message processor with multi-store routing capabilities
- **Store Context**: Automatic store identification and customer association
- **Message Routing**: Context-aware message processing per store-customer relationship
- **Extensible**: Replace echo logic with LLM integration, workflow graphs, or business logic

### Configuration System

#### Main Config (`config.yaml`)
- Platform-specific credentials and settings
- Feature capabilities per platform (supports_text, supports_images, etc.)
- Webhook paths and server configuration
- Store configuration and routing rules
- Multi-tenant isolation and security settings

#### Environment Support
- Development: Full reload, detailed logging
- Production: Gunicorn, monitoring, error tracking via Sentry

### Development Patterns

#### Adding New Platforms
1. Create new adapter in `adapters/platforms/`
2. Inherit from `PlatformAdapter`
3. Implement required methods: `parse_incoming()`, `format_outgoing()`, `send_message()`, etc.
4. Add platform enum to `models/platform.py`
5. Add webhook endpoint in `main.py`

#### Message Processing Flow
```python
Webhook → Adapter.parse_incoming() → Store.identify() → Customer.associate() → 
Gateway.handle_message() → Store.route_response() → Adapter.format_outgoing() → 
Adapter.send_message()
```

#### Testing Strategy
- **Unit Tests**: Individual adapter and model functionality
- **Integration Tests**: End-to-end webhook processing
- **Mock**: External API calls for reliable testing
- **Coverage**: Minimum 80% for core components

### Current Implementation Status
- ✅ LINE platform integration (complete webhook handling)
- ✅ Message normalization and user profile management
- ✅ FastAPI server with health checks and status endpoints
- ✅ Multi-store architecture foundation
- 🔄 Store identification and customer association (ready for implementation)
- 🔄 Gateway currently implements echo responses (ready for enhancement)
- 🔄 Session management and context persistence (infrastructure ready)

### Extension Points
- Complete store identification and customer association logic
- Implement multi-tenant data isolation and security
- Replace `BotGateway.handle_message()` with LLM/AI logic
- Add workflow graph processing (architecture outlined in README)
- Implement session persistence with Redis (`session/store_redis.py`)
- Add analytics and metrics collection per store (`analytics/` planned)
- Enhance user profile management with store context (`user/profile_service.py`)
- Add store management dashboard and admin interface
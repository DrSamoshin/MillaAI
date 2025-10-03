# Database Architecture Refactoring

## Overview

This document describes the refactoring of the database layer to use the Unit of Work pattern, eliminating multiple session issues and greenlet conflicts.

## Previous Architecture Issues

### Problems Identified
1. **Multiple Sessions**: Different components (API, Services, LLM Tools) created separate database sessions
2. **Greenlet Conflicts**: Async/sync context mixing caused `greenlet_spawn` errors
3. **Inconsistent Transaction Management**: Each component managed its own commits/rollbacks
4. **Tight Coupling**: Direct session dependencies throughout the codebase
5. **Mid-Transaction Commits**: LLM Tools called `commit()` during tool execution, breaking transaction isolation
6. **Missing Dependencies**: Services referenced non-existent attributes like `self.chat_repo`

### Code Smell Examples
```python
# Old problematic pattern
class ChatService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repo = MessageRepository(db_session)  # Another session instance
```

## New Architecture: Unit of Work Pattern

### Core Components

#### 1. UnitOfWork Class (`src/aimi/db/uow.py`)
Central coordinator for database operations:
```python
class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repositories: dict[str, Any] = {}

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def users(self) -> UserRepository:
        # Lazy repository initialization
```

#### 2. Session Management (`src/aimi/db/session.py`)
Enhanced with UoW support:
```python
@asynccontextmanager
async def get_unit_of_work() -> AsyncGenerator[UnitOfWork, None]:
    async with session_scope() as session:
        uow = UnitOfWork(session)
        yield uow

async def get_uow_dependency() -> AsyncGenerator[UnitOfWork, None]:
    # FastAPI dependency
```

### Transaction Management Strategy

#### HTTP Endpoints
- **One transaction per request**
- API layer owns transaction lifecycle
- Automatic rollback on exceptions

```python
async def api_endpoint(uow: UnitOfWork = Depends(get_uow_dependency)):
    try:
        # Business logic using uow
        result = await service.do_work(uow, ...)
        await uow.commit()  # Only API layer commits
        return result
    except Exception:
        await uow.rollback()  # Automatic via context manager
        raise
```

#### WebSocket + LLM Tools
- **Each tool operation = separate transaction**
- Tools manage their own commits for immediate persistence
- Enables partial success scenarios

```python
async def llm_tool_method(self):
    async with get_unit_of_work() as uow:
        entity = await uow.goals().create_goal(...)
        await uow.commit()  # Tool commits immediately
        return {"id": str(entity.id)}
```

## Migration Guide

### Layer-by-Layer Changes

#### 1. API Layer
**Before:**
```python
async def endpoint(
    session: AsyncSession = Depends(get_db_session)
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    await session.commit()
```

**After:**
```python
async def endpoint(
    uow: UnitOfWork = Depends(get_uow_dependency)
):
    user = await uow.users().get_by_id(user_id)
    await uow.commit()
```

#### 2. Services Layer
**Before:**
```python
class ChatService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def method(self):
        # Direct DB operations
```

**After:**
```python
class ChatService:
    def __init__(self, redis: Redis, llm_client: LLMClient):
        # No database dependency

    async def method(self, uow: UnitOfWork):
        # Operations through UoW
```

#### 3. LLM Tools Layer
**Before:**
```python
class GoalTools:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repo = GoalRepository(db_session)
```

**After:**
```python
class GoalTools:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_goal(self):
        async with get_unit_of_work() as uow:
            goal = await uow.goals().create_goal(...)
            await uow.commit()
```

## Critical Issues Resolved

### 1. Greenlet_spawn Error Fix
**Root Cause**: LLM Tools called `commit()` mid-transaction, then ChatService tried to use closed session.

**Solution**:
- Removed all `commit()` calls from LLM Tools
- Only WebSocket handler manages transaction lifecycle
- Fixed `self.chat_repo` AttributeError that caused context switching

**Before (Broken)**:
```python
# LLM Tool
goal = await self.uow.goals().create_goal(...)
await self.uow.commit()  # ← Closes session!

# ChatService (later)
await self._save_message(...)  # ← greenlet_spawn error!
```

**After (Fixed)**:
```python
# LLM Tool
goal = await self.uow.goals().create_goal(...)
# No commit - WebSocket handler will commit

# ChatService
await self._save_message(...)  # ← Works in same session
```

### 2. WebSocket Transaction Strategy
**Pattern**: One UoW per WebSocket message
```python
async with get_unit_of_work() as uow:
    result = await chat_service.send_message(uow=uow, ...)
# Automatic commit/rollback
```

**Flow**:
1. User message → save
2. LLM tool calls → execute (no commit)
3. LLM follow-up → generate
4. Assistant message → save
5. Auto-commit all changes

## Benefits Achieved

### 1. Eliminated Greenlet Issues
- Single session per logical operation
- Consistent async context throughout request lifecycle
- No more `greenlet_spawn` errors

### 2. Improved Transaction Control
- Clear ownership of transaction boundaries
- Atomic operations where needed
- Proper rollback handling

### 3. Better Separation of Concerns
- API layer: Transaction management
- Service layer: Business logic
- Repository layer: Data access
- Tools layer: LLM operations

### 4. Enhanced Testability
- Easy to mock UnitOfWork for testing
- Isolated transaction testing
- Cleaner dependency injection

## Performance Considerations

### Connection Pooling
- SQLAlchemy engine manages connection pool
- UoW creates sessions on-demand
- Automatic connection cleanup

### Transaction Boundaries
- **HTTP**: Short transactions (request-scoped)
- **WebSocket**: Per-message transactions
- **LLM Tools**: Per-operation transactions

## Testing Strategy

### Unit Tests
```python
async def test_service_method():
    uow = Mock(spec=UnitOfWork)
    uow.users().get_by_id.return_value = mock_user

    result = await service.method(uow, user_id)

    uow.commit.assert_called_once()
```

### Integration Tests
```python
async def test_endpoint_integration():
    async with get_unit_of_work() as uow:
        # Test with real UoW instance
        result = await endpoint_logic(uow)
        # uow auto-commits via context manager
```

## Implementation Notes

### Lazy Repository Loading
- Repositories instantiated on first access
- Cached for subsequent calls within same UoW
- Reduces memory overhead

### Error Handling
- Context manager handles automatic rollback
- Explicit rollback available when needed
- Proper exception propagation

### Backward Compatibility
- Old `get_db_session` removed completely
- All components updated to new pattern
- No mixed usage patterns remain

## Future Enhancements

1. **Read Replicas**: UoW could route reads to replica databases
2. **Distributed Transactions**: Support for cross-service transactions
3. **Event Sourcing**: UoW could emit domain events
4. **Caching Integration**: Repository-level caching through UoW

## Files Modified

### Core Infrastructure
- `src/aimi/db/uow.py` - New UnitOfWork implementation
- `src/aimi/db/session.py` - Enhanced session management

### API Layer
- `src/aimi/api/v1/deps.py` - Updated dependencies
- `src/aimi/api/v1/routers/*.py` - All endpoints updated

### Services Layer
- `src/aimi/services/chat.py` - Refactored to use UoW
- `src/aimi/services/conversation.py` - Updated constructor
- `src/aimi/services/deps.py` - Simplified dependencies

### LLM Tools Layer
- `src/aimi/llm/tools/registry.py` - Updated tool initialization
- `src/aimi/llm/tools/*.py` - All tools updated to UoW pattern

### Cleanup
- Removed unused imports and dependencies
- Deleted obsolete session management code
- Cleaned up repository instantiation patterns
# API Documentation

This directory contains documentation for all REST API endpoints.

## Endpoints Overview

### Authentication
- [`api_auth.md`](./api_auth.md) - Apple Sign In and token refresh

### User Management
- [`api_users.md`](./api_users.md) - User profile and statistics

### Chat System
- [`api_chats.md`](./api_chats.md) - Chat management and messaging (REST)
- [`api_chat_websocket.md`](./api_chat_websocket.md) - Real-time WebSocket chat

### Goal Management
- [`api_goals.md`](./api_goals.md) - Goals, tasks, and mental state tracking

### System
- [`api_admin.md`](./api_admin.md) - Admin endpoints
- [`api_error_handling.md`](./api_error_handling.md) - Error response format

## API Conventions

### Base URL
```
https://api.aimi.app/v1/
```

### Authentication
Most endpoints require Bearer token authentication:
```
Authorization: Bearer <access_token>
```

### Response Format
All successful responses use `SuccessResponse[T]` envelope:
```json
{
  "status": "success",
  "data": <response_data>
}
```

Error responses use `ErrorResponse` format:
```json
{
  "status": "error",
  "error": {
    "code": "error_code",
    "message": "Human readable message",
    "details": <optional_context>
  }
}
```

### Data Types
- **Timestamps**: ISO 8601 format with timezone (`2025-01-15T14:30:00+00:00`)
- **UUIDs**: String representation (`"550e8400-e29b-41d4-a716-446655440000"`)
- **Enums**: String values (`"active"`, `"pending"`, etc.)

## Schema Organization

API schemas are organized by domain:
- `auth.py` - Authentication and user payloads
- `user.py` - User statistics and profile
- `chat.py` - Chat and message schemas
- `goals.py` - Goal, task, and mental state schemas
- `response.py` - Standard response envelopes
- `health.py` - System health check

## Request/Response Examples

All endpoints include complete request/response examples with actual field names and data types. See individual endpoint documentation for details.

## Rate Limiting

- **WebSocket**: No explicit rate limiting
- **REST API**: Standard rate limiting applies (details TBD)

## Versioning

API is versioned with `/v1/` prefix. Breaking changes will increment the version number.
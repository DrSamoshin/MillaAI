# WebSocket Chat API - New Chat System

## Endpoints

### Individual Chat WebSocket
```
ws://127.0.0.1:8000/v1/ws/chat/{chat_id}
```

### REST API
```
POST /v1/chats/{chat_id}/send
```

## Chat ID

Each chat session requires a unique `chat_id` (UUID). You can:
- Generate new UUID for new chat
- Use existing chat_id to continue conversation

## Authentication

WebSocket requires Bearer token in `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token obtained via `/v1/auth/login` or `/v1/auth/apple-signin`.

## WebSocket Protocol

### Connection
1. Connect to `ws://127.0.0.1:8000/v1/ws/chat/{chat_id}` with Authorization header
2. Server accepts connection if token is valid
3. Chat marked as "active" for 30 seconds
4. Connection errors close with code 1008

### Sending Messages
Send JSON with message content and client ID:

```json
{
  "content": "Привет, как дела?",
  "client_msg_id": "uuid-generated-by-client"
}
```

### Receiving Responses

**Thinking indicator:**
```json
{
  "status": "thinking",
  "message": "Обрабатываю ваш запрос..."
}
```

**Successful response:**
```json
{
  "status": "success",
  "data": {
    "user_message": {
      "id": "uuid",
      "seq": 1,
      "role": "user",
      "content": "Привет, как дела?",
      "created_at": "2025-01-01T10:00:00Z"
    },
    "assistant_message": {
      "id": "uuid",
      "seq": 2,
      "role": "assistant",
      "content": "Привет! У меня все отлично...",
      "created_at": "2025-01-01T10:00:05Z"
    },
    "status": "delivered",
    "model": "gpt-4"
  }
}
```

**Error response:**
```json
{
  "status": "error",
  "error": {
    "code": "message_processing_failed",
    "message": "Failed to process message",
    "details": {"reason": "..."}
  }
}
```

## REST API

### Send Message
```http
POST /v1/chats/{chat_id}/send
Authorization: Bearer {token}
Content-Type: application/json

{
  "content": "Hello, world!",
  "client_msg_id": "optional-uuid"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_message": {...},
    "assistant_message": {...},
    "status": "delivered",
    "model": "gpt-4"
  }
}
```

## Features

### Message Storage
- Each message has monotonic `seq` within chat
- Last 100 messages cached in Redis
- Full history stored in PostgreSQL

### Activity Tracking
- WebSocket connection = active chat
- 30-second TTL for activity flag
- Push notifications sent to inactive chats

### Idempotency
- `client_msg_id` prevents duplicate messages
- Same UUID returns existing message

### Context Building
- Uses last 100 messages from Redis cache
- Falls back to PostgreSQL if cache miss
- Vector search integration (future feature)

## Error Handling

1. **1008 Policy Violation** - authentication issues
2. **1001 Going Away** - server shutdown
3. **Network errors** - connection problems

## CLI Usage

```bash
python cli/chat.py
# Enter token: your-jwt-token
# Choose: 1=existing chat, 2=new chat
# Chat with AI through terminal
```

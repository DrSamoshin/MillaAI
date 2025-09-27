# Chat Endpoints

## Create new chat
- **Method**: `POST`
- **Path**: `/v1/chats/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request** (`CreateChatRequest`):

```json
{
  "title": "My Learning Chat",
  "model": "gpt-4",
  "settings": {
    "temperature": 0.7,
    "system_prompt": "You are a helpful learning assistant"
  }
}
```

- **Response** (`SuccessResponse[CreateChatResponse]`):

```json
{
  "status": "success",
  "data": {
    "chat_id": "uuid",
    "title": "My Learning Chat",
    "model": "gpt-4",
    "settings": {
      "temperature": 0.7,
      "system_prompt": "You are a helpful learning assistant"
    }
  }
}
```

## List user chats
- **Method**: `GET`
- **Path**: `/v1/chats/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse[ChatListResponse]`):

```json
{
  "status": "success",
  "data": {
    "chats": [
      {
        "chat_id": "uuid",
        "title": "My Learning Chat",
        "model": "gpt-4",
        "settings": {
          "temperature": 0.7
        },
        "last_seq": 5,
        "last_active_at": "2025-01-15T14:30:00+00:00",
        "created_at": "2025-01-01T00:00:00+00:00"
      }
    ],
    "total": 1
  }
}
```

## Delete chat
- **Method**: `DELETE`
- **Path**: `/v1/chats/{chat_id}`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse[dict]`):

```json
{
  "status": "success",
  "data": {
    "deleted": true,
    "chat_id": "uuid"
  }
}
```

## Get chat messages
- **Method**: `GET`
- **Path**: `/v1/chats/{chat_id}/messages`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `limit` (optional): Number of messages to return (1-100, default: 50)
  - `offset` (optional): Number of messages to skip (default: 0)
- **Response** (`SuccessResponse[MessageHistoryResponse]`):

```json
{
  "status": "success",
  "data": {
    "messages": [
      {
        "id": "uuid",
        "seq": 1,
        "role": "user",
        "content": "Привет, как дела?",
        "created_at": "2025-01-15T14:30:00+00:00",
        "truncated": false,
        "from_summary": false
      },
      {
        "id": "uuid2",
        "seq": 2,
        "role": "assistant",
        "content": "Привет! Все отлично, готов помочь с обучением.",
        "created_at": "2025-01-15T14:30:05+00:00",
        "truncated": false,
        "from_summary": false
      }
    ],
    "total": 2,
    "has_more": false
  }
}
```

## Send message (REST)
- **Method**: `POST`
- **Path**: `/v1/chats/{chat_id}/send`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request** (`SendMessageRequest`):

```json
{
  "content": "Расскажи про Python",
  "client_msg_id": "client-generated-uuid"
}
```

- **Response** (`SuccessResponse[SendMessageResponse]`):

```json
{
  "status": "success",
  "data": {
    "user_message": {
      "id": "uuid",
      "seq": 3,
      "role": "user",
      "content": "Расскажи про Python",
      "created_at": "2025-01-15T14:35:00+00:00"
    },
    "assistant_message": {
      "id": "uuid2",
      "seq": 4,
      "role": "assistant",
      "content": "Python - это высокоуровневый язык программирования...",
      "created_at": "2025-01-15T14:35:02+00:00"
    },
    "status": "completed",
    "model": "gpt-4"
  }
}
```

## WebSocket Real-time Chat
- **URL**: `ws://localhost:8000/v1/ws/chat/{chat_id}`
- **Headers**: `Authorization: Bearer <access_token>`

### Send message via WebSocket:
```json
{
  "content": "Привет!",
  "client_msg_id": "optional-client-id"
}
```

### Receive responses:
```json
{
  "status": "thinking",
  "message": "Обрабатываю ваш запрос..."
}
```

```json
{
  "status": "success",
  "data": {
    "user_message": {...},
    "assistant_message": {...},
    "status": "completed",
    "model": "gpt-4"
  }
}
```

### Error response:
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

## Field Descriptions

### Chat Fields
- `last_seq`: Sequence number of the last message in chat
- `last_active_at`: Timestamp of last activity in chat
- `settings`: Chat configuration (temperature, system prompt, etc.)

### Message Fields
- `seq`: Sequential message number within chat
- `role`: Message sender (`user`, `assistant`, `system`)
- `truncated`: Whether message was truncated due to length
- `from_summary`: Whether message was generated from chat summary

## Notes

- Chats are automatically created when sending first message
- Messages are ordered by `seq` field within each chat
- WebSocket connections track activity and mark chats as active
- All timestamps are in ISO 8601 format with timezone
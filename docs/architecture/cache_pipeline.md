# Chat Cache Pipeline - New Multi-Chat System

## Redis Structure
```redis
chat:{chat_id}:messages    # Sorted Set by seq (last 100 messages)
chat:{chat_id}:meta        # Hash: max_seq, last_active_at, message_count
```

## WebSocket Activity Tracking
```python
# In-memory tracking via ConnectionManager
active_connections: dict[UUID, WebSocket] = {
    chat_id_1: websocket_1,
    chat_id_2: websocket_2,
    ...
}
```

## Message Format in Redis
```json
{
  "id": "uuid",
  "seq": 42,
  "role": "user|assistant|system",
  "content": "message text",
  "created_at": "2025-01-01T10:00:00Z",
  "truncated": false,
  "from_summary": false
}
```

## Chat Lifecycle

### 1. Message Storage
- **User sends message** → save to PostgreSQL with next `seq`
- **Add to Redis:** `ZADD chat:{chat_id}:messages {seq} {message_json}`
- **Trim cache:** `ZREMRANGEBYRANK chat:{chat_id}:messages 0 -101` (keep last 100)
- **Update metadata:** `HSET chat:{chat_id}:meta max_seq {seq} last_active_at {timestamp}`

### 2. Context Building
- **Primary source:** `ZRANGE chat:{chat_id}:messages 0 -1` (Redis sorted set)
- **Cache miss fallback:** Load last 100 messages from PostgreSQL by `(chat_id, seq)`
- **Format for LLM:** Convert to ChatMessage array with system prompt

### 3. Activity Tracking
- **WebSocket connect:** `connection_manager.connect(chat_id, websocket)`
- **Activity check:** `connection_manager.is_active(chat_id)` (in-memory lookup)
- **WebSocket disconnect:** `connection_manager.disconnect(chat_id)`
- **Push logic:** Send notification if no active WebSocket connection

## Background Processing (Future)

### Summary Generation (Every 100 messages)
1. **Trigger:** When `last_seq % 100 == 0`
2. **Process:** Take messages 1-100, generate summary via LLM
3. **Store:** Save in `summaries` table with embedding vector
4. **Archive:** Optionally move old messages to archive table

### Vector Search Integration
1. **Query embedding:** Generate vector for current user message
2. **Search:** Find similar summaries with cosine similarity > 0.7
3. **Context injection:** Add relevant summaries to LLM prompt
4. **Trigger conditions:**
   - Current context < 70% of token limit
   - Message contains past reference keywords ("как мы говорили", "помнишь")

## Benefits
- **Performance:** Sub-millisecond message retrieval from Redis
- **Scalability:** Per-chat caching scales with users
- **Memory efficiency:** Automatic 100-message limit per chat
- **Real-time activity:** Instant WebSocket connection tracking (no TTL delays)
- **Accuracy:** Precise active/inactive detection based on actual connections
- **Simplicity:** No Redis TTL management required
- **Ordered messages:** Sorted set guarantees chronological order

# Cache / Session Pipeline

## Session storage (Redis)
- `session:{user_id}` – JSON list (до 30 сообщений).
- `session_meta:{user_id}` – информация о статусе, последней активности, незавершённых действиях (например, "ожидаем подтверждение задачи").
- TTL: 10 минут после последней активности (или напоминания) + дополнительные условия (команда «пока», лимит 30 сообщений).

## Message format
```json
{
  "message_id": "UUID",
  "role": "user" | "assistant",
  "text": "...",
  "metadata": {
    "tags": [...],
    "pending_action": false,
    ...
  },
  "occurred_at": "timestamp_iso",
  "read": true | false
}
```

## Session lifecycle
1. При первом сообщении создаётся `session:{user_id}` (пустой список), в `session_meta` сохраняем `started_at`, `last_active_at`.
2. Каждый новый message → append в кеш и записывается в `chat_messages` (Postgres).
3. Если сообщение ассистента – фиксируем `read=false`. Когда пользователь отвечает → предыдущие ассистентские сообщения помечаем `read=true`.
4. Метаданные (`pending_action`) используются, чтобы при следующей сессии поднять “не закрытые” вопросы.

## End of session triggers
- явное «пока/bye»;
- достигнут лимит 30 сообщений;
- не было активности 10 минут (включая напоминания);
- системное событие (scheduler напоминаний) требует тайм-аута.

## Background worker (summary)
1. Забирает кеш ⇒ формирует summary (LLM или правило).
2. Сохраняет свёртку в Postgres (`session_summary`, `chat_messages`, `user_state`).
3. Создаёт embedding ⇒ `memory_vectors` (ставит `is_active=true`), старые записи → `is_active=false` при необходимости.
4. Обновляет граф (зелёные цели, связи контекст–событие).
5. Кеш очищается (`DEL session:{user_id}`, `session_meta`), но информация остаётся в user_state/векторах.

## Orchestrator startup flow
- Загружает `user_state` (последняя свёртка, активные цели).
- Берёт актуальные `events`/`tasks`, pending-флаги из `session_meta`.
- Подмешивает vector search (по `memory_vectors`) в промпт.

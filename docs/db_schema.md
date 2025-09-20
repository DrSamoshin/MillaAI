# Схема БД Aimi (черновик)

## users
- `id UUID PRIMARY KEY`
- `email TEXT` (optional)
- `display_name TEXT`
- `timezone TEXT`
- `locale TEXT`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`
- `profile JSONB` (статичные поля: профессия, предпочтения и т.д.)

## user_state
- `user_id UUID PRIMARY KEY REFERENCES users(id)`
- `last_summary TEXT` (последняя свертка о пользователе)
- `focus_goals JSONB` (активные цели, веса)
- `traits JSONB` (предпочтения, стиль общения)
- `recent_mood JSONB` (обобщенное состояние)
- `updated_at TIMESTAMPTZ`

## goals
- `id UUID PRIMARY KEY`
- `user_id UUID REFERENCES users(id)`
- `title TEXT`
- `description TEXT`
- `status TEXT` (`active`, `paused`, `completed`, `archived`)
- `target_date DATE NULL`
- `priority SMALLINT`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`
- `metadata JSONB`

## habits
- `id UUID PRIMARY KEY`
- `user_id UUID REFERENCES users(id)`
- `goal_id UUID REFERENCES goals(id)`
- `name TEXT`
- `frequency TEXT` (cron/rrule)
- `intensity SMALLINT`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`
- `metadata JSONB`

## chat_messages
- `id UUID PRIMARY KEY`
- `user_id UUID REFERENCES users(id)`
- `role TEXT` (`user`, `assistant`)
- `text TEXT`
- `occurred_at TIMESTAMPTZ`
- `session_id UUID` (group messages в рамках сессии)
- `metadata JSONB` (теги, sentiment, linked_task_id, etc.)
- `created_at TIMESTAMPTZ`

## events
- `id UUID PRIMARY KEY`
- `user_id UUID REFERENCES users(id)`
- `goal_id UUID REFERENCES goals(id) NULL`
- `type TEXT` (`task`, `event`, `follow_up`, ...)
- `title TEXT`
- `description TEXT`
- `status TEXT` (`planned`, `pending_confirmation`, `awaiting_feedback`, `completed`, `cancelled`)
- `start_at TIMESTAMPTZ NULL`
- `end_at TIMESTAMPTZ NULL`
- `due_at TIMESTAMPTZ NULL` (для задач)
- `priority SMALLINT`
- `repeat_rule TEXT NULL` (rrule/cron)
- `source TEXT` (`user`, `assistant`, `external`)
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`
- `metadata JSONB`

## reminder_queue
- `id BIGSERIAL PRIMARY KEY`
- `event_id UUID REFERENCES events(id)`
- `trigger_at TIMESTAMPTZ`
- `channel TEXT` (`push`, `email`, `assistant_message`)
- `status TEXT` (`scheduled`, `sent`, `skipped`, `failed`)
- `payload JSONB`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

## reminder_logs
- `id BIGSERIAL PRIMARY KEY`
- `queue_id BIGINT REFERENCES reminder_queue(id)`
- `sent_at TIMESTAMPTZ`
- `status TEXT`
- `response JSONB`

## session_summary
- `id UUID PRIMARY KEY`
- `user_id UUID REFERENCES users(id)`
- `session_id UUID`
- `summary TEXT`
- `facts JSONB` (Key-value facts extracted)
- `created_at TIMESTAMPTZ`

## memory_vectors
- `id UUID PRIMARY KEY`
- `user_id UUID REFERENCES users(id)`
- `entity_type TEXT` (`goal`, `event`, `experience`, `summary`)
- `entity_id UUID NULL`
- `content TEXT`
- `embedding VECTOR` (PGVector) или `vector(1536)`
- `metadata JSONB`
- `is_active BOOLEAN DEFAULT true`
- `created_at TIMESTAMPTZ`

## task_history / event_history (опционально)
- `id BIGSERIAL PRIMARY KEY`
- `entity_id UUID`
- `entity_type TEXT` (`task`, `event`)
- `from_status TEXT`
- `to_status TEXT`
- `changed_at TIMESTAMPTZ`
- `metadata JSONB`

### Вспомогательные таблицы (при необходимости)
- `user_settings`, `integrations`, `external_calendar_tokens`
- `session_cache` (если хотим хранить кеш сессий в базе)

### Индексы и связи
- Основные индексы:
  - `chat_messages` по (`user_id`, `session_id`, `occurred_at DESC`)
  - `events` по (`user_id`, `status`, `start_at / due_at`)
  - `reminder_queue` по (`trigger_at`, `status`)
  - `memory_vectors` по `user_id` и векторный индекс (ivfflat/hnsw)

### Потоки данных
1. Сообщения → `chat_messages` (+ кеш).
2. При завершении сессии → `session_summary` + `memory_vectors`.
3. Создание целей/задач/событий → таблица `events` и связи `goal_id`/`metadata`.
4. Планирование напоминаний → `reminder_queue` → воркер → `reminder_logs`.

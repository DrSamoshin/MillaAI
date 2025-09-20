# Aimi Roadmap (backend)

## Stage 0 — Project bootstrap
- Clean repo, adopt new naming (`aimi`).
- Prepare local stack: Postgres + Redis via docker-compose.
- Set up `uv`, pre-commit, CI skeleton (ruff, mypy, pytest).

## Stage 1 — Data layer
- Describe SQLAlchemy/SQLModel models: `users`, `user_state`, `chat_messages`, `goals`, `habits`, `events`, `reminder_queue`, `reminder_logs`, `session_summary`, `memory_vectors`.
- Create Alembic migrations + fixtures.
- Implement repositories (`EventRepository`, `UserStateRepository`, `ReminderRepository`).

## Stage 2 — Session cache service
- Integrate Redis, define schema (`session:{user_id}` list, `session_meta:{user_id}` flags).
- Implement сервис: append message, mark assistant messages read, detect timeout/limits.
- Unit tests на кеш (ttl, лимит 30 сообщений, очистка).

## Stage 3 — API skeleton & conversation service
- FastAPI endpoints: `GET /health`, `POST /chat/send`, WebSocket `/ws/chat` (пока без LLM).
- ConversationService: сохраняет сообщение (кеш+БД), возвращает заглушку-ответ.
- httpx/WS тесты на happy-path и ошибки.

## Stage 4 — Summary & user_state
- Фоновый воркер (Celery/async): завершение сессии по таймауту/команда.
- Реализовать генерацию summary (пока rule-based), обновить `user_state`, добавить запись в `session_summary`.
- Очистка кеша после свёртки, проверка тестами.

## Stage 5 — Embeddings & vector search
- Добавить PGVector таблицу `memory_vectors`.
- Реализовать `EmbeddingService` (пока stub, позже OpenAI/Voyage).
- Интеграция с summary воркером: создавать embeddings, помечать `is_active`.
- Написать unit/integration тесты (`store_embedding`, `search` с фиктивными векторами).

## Stage 6 — Graph snapshot
- Пока без Neo4j: описать таблицы/представления для узлов и рёбер в Postgres.
- Воркер обновляет `goal_state`, `habit_state`, `context_links` на основе summary.
- Оркестратор читает эти данные при старте сессии.

## Stage 7 — Notification pipeline
- Планировщик напоминаний: генерация записей в `reminder_queue` (T-24h, T-2h, ...).
- Воркер отправки: mock-канал (запись в лог/чат), логирование в `reminder_logs`.
- Тесты на периодический запуск (freezegun, Celery beat stub).

## Stage 8 — Оркестратор + LLM интеграция
- `ContextBuilder`: имя пользователя, активные цели, ближайшие события, top-K из вектора.
- OpenAI (или иной) ChatClient: промпты, guardrails, модерация.
- Интеграционные тесты с mock LLM (проверка создания задач/событий).

## Stage 9 — Observability & tooling
- Логирование (structlog), трассировки (OTel), бизнес-метрики.
- health-checks, readiness, проверка graceful shutdown.

## Stage 10 — Клиентские интеграции
- REST endpoints для задач/целей/событий (CRUD).
- WS-уведомления / push-канал.
- Подготовка API для iOS.

Каждый этап закрывается PR-ом с документацией и тестами. Если в ходе разработки архитектура меняется — обновляем `docs/architecture.md`, `docs/cache_pipeline.md`, `docs/db_schema.md`.

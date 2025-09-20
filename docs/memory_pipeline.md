# Memory pipeline (Aimi)

## Goals
- Сохранять полный контекст общения, но отвечать мгновенно.
- Знать актуальные цели/события и напоминать о них вовремя.
- Иметь semantic-поиск по прошлому опыту (summary + embeddings).

## Слои памяти
1. **Session cache (Redis)**
   - `session:{user_id}` — до 30 последних сообщений.
   - `session_meta:{user_id}` — таймстемпы, незавершённые действия, флаги.
   - TTL 10 минут после последнего взаимодействия (или явный `bye`).
2. **Structured storage (Postgres)**
   - `users`, `user_state`, `chat_messages`, `goals`, `habits`, `events`, `reminder_queue`, `reminder_logs`, `session_summary`.
   - `user_state` хранит актуальный «портрет»: summary, активные цели, настроение.
3. **Semantic layer**
   - `memory_vectors` (PGVector/OpenSearch): embeddings summary, заметок, фактов (флаг `is_active`).
   - Используется оркестратором (`top-k` похожих фрагментов).
4. **Graph snapshot**
   - Представление целей/привычек/состояний (таблицы/материализованные представления). Обновляется воркером.

## Поток данных
1. **Online**
   - Сообщение → кеш + `chat_messages`.
   - Оркестратор берёт cache + `user_state` + `memory_vectors` + граф → формирует контекст → LLM.
   - Ответ ассистента сохраняется в cache + БД.
2. **Session end** (bye, таймаут 10 минут, лимит 30 сообщений, событие планировщика)
   - Воркер формирует summary (LLM или правило).
   - Обновляет `session_summary`, `user_state`, `goals/events` (если были изменения).
   - Создаёт/обновляет embeddings (`memory_vectors`), отмечает устаревшие `is_active=false`.
   - Обновляет граф (узлы Goal/Context, веса).
   - Чистит Redis-кеш.
3. **Reminders**
   - Отдельный воркер вычисляет записи в `reminder_queue` по `events` (T-24h, T-2h...).
   - Отправитель (push/email/assistant message) меняет статус, пишет лог.
4. **Classifier worker** (по мере необходимости)
   - Проставляет теги, связывает сообщения с целями, обновляет `session_meta`.

## APIs/службы
- `EventRepository`, `UserStateRepository`, `ReminderRepository` — слой доступа к данным.
- `ConversationService` — кернер диалога (использует кеш + репозитории).
- `ContextBuilder` — собирает `user_state`, ближайшие события, топ-K векторов.
- `ChatClient` — LLM/guardrails.

## Вопросы/дальнейшие шаги
- Определить формат summary (схема JSON, ключевые поля для `user_state`).
- Решить, какой embedding-модель используем на старте (OpenAI text-embedding-3-small? Voyage?).
- Спроектировать граф в Postgres (таблицы + индексы) до миграции в Neo4j.
- Подключить реальные каналы уведомлений (пока mock).

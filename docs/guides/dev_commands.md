# Development Commands Cheat Sheet

## uv (Python toolchain)
- `uv sync` — install/upgrade project dependencies into the virtual environment.
- `UV_CACHE_DIR=.uv_cache uv run pytest` — run tests with a local cache directory (helpful in sandboxed envs).
- `uv run python main.py --mode dev` — start the FastAPI app with autoreload and `.env` settings.
- `uv run alembic upgrade head` — apply the latest database migrations.
- `uv run alembic downgrade -1` — roll back the last migration (use with care).

## Docker Compose
- `docker compose -f docker/docker-compose.yml up -d` — start Postgres and Redis in the background.
- `docker compose -f docker/docker-compose.yml down` — stop services (keeps volumes).
- `docker compose -f docker/docker-compose.yml down -v` — stop services and remove volumes (reset data).
- `docker compose -f docker/docker-compose.yml logs -f postgres` — tail Postgres logs.
- `docker compose -f docker/docker-compose.yml ps` — show container status.
- Полностью удалить именованные volume: `docker volume rm postgres_data` (убедись, что контейнеры остановлены).

## Alembic (migrations)
- `uv run alembic revision -m "description"` — create a new migration file (edit before applying).
- `uv run alembic upgrade head` — upgrade schema to the latest revision.
- `uv run alembic history --verbose` — list applied/available revisions.

### Инициализация Alembic
- Добавь зависимость и подтяни окружение: обнови `pyproject.toml`, затем `uv sync`.
- Сгенерируй структуру проекта Alembic: `uv run alembic init alembic`.
- В `alembic.ini` укажи URL БД (можно оставить заглушку и переопределять через `.env`).
- В `alembic/env.py` подключи модели и настройки:
  - `from aimi.core.config import get_settings`
  - `from aimi.db.base import Base` и `from aimi.db import models`
  - `config.set_main_option("sqlalchemy.url", get_settings().database_url)`
  - `target_metadata = Base.metadata`
  - замени `engine_from_config` на `async_engine_from_config` и оберни запуск `asyncio.run(...)`.
- Проверка: `uv run alembic current` — база должна быть пустой.
- Создай первую ревизию: `uv run alembic revision --autogenerate -m "create users table"`.
- Применяй изменения: `uv run alembic upgrade head`.
- Для новых правок повторяй цепочку `revision --autogenerate` → ручная проверка → `upgrade head`.

## Inspecting Containers & Data
- Postgres shell: `docker exec -it aimi_postgres psql -U aimi -d aimi`
  - Check tables: `\dt`
  - Describe table: `\d+ users`
  - Run query: `SELECT * FROM users LIMIT 5;`
- Redis shell: `docker exec -it aimi_redis redis-cli`
  - List all keys: `KEYS *`
  - List chat keys: `KEYS chat:*`
  - View chat messages: `ZRANGE chat:{chat_id}:messages 0 -1`
  - View chat metadata: `HGETALL chat:{chat_id}:meta`
  - Count messages: `ZCARD chat:{chat_id}:messages`
  - Latest messages: `ZREVRANGE chat:{chat_id}:messages 0 10`

## Miscellaneous
- Clean up stale git lock (if needed): `rm -f .git/index.lock`
- Format logs when tailing uvicorn: check `docker compose ... logs -f` or run app via `uv run`.
- JWT config via environment:
  - `AIMI_JWT_SECRET`, `AIMI_JWT_ALGORITHM`
  - `AIMI_JWT_ACCESS_EXPIRES_SECONDS`, `AIMI_JWT_REFRESH_EXPIRES_SECONDS`

> Tip: ensure `.env` matches docker credentials before running migrations or API.

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
- `docker compose -f docker/docker-compose.yml down -v` — stop services and remove volumes (resets databases).
- `docker compose -f docker/docker-compose.yml logs -f postgres` — tail Postgres logs.
- `docker compose -f docker/docker-compose.yml ps` — show container status.

## Alembic (migrations)
- `uv run alembic revision -m "description"` — create a new migration file (edit before applying).
- `uv run alembic upgrade head` — upgrade schema to the latest revision.
- `uv run alembic history --verbose` — list applied/available revisions.

## Inspecting Containers & Data
- Postgres shell: `docker exec -it aimi_postgres psql -U aimi -d aimi`
  - Check tables: `\dt`
  - Describe table: `\d+ users`
  - Run query: `SELECT * FROM users LIMIT 5;`
- Redis shell: `docker exec -it aimi_redis redis-cli`
  - List keys: `KEYS session:*`
  - Inspect session messages: `LRANGE session:<user_id> 0 -1`
  - Check TTL: `TTL session:<user_id>`

## Miscellaneous
- Clean up stale git lock (if needed): `rm -f .git/index.lock`
- Format logs when tailing uvicorn: check `docker compose ... logs -f` or run app via `uv run`.

> Tip: ensure `.env` matches docker credentials before running migrations or API.

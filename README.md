# Aimi

Aimi is a personal AI coach that tracks goals, plans tasks, and preserves conversational memory across sessions.

We are rebuilding the backend from scratch. The code in `src/aimi` is currently a scaffold and will be filled in according to the specifications in `docs/`.

## Architecture (overview)
- **FastAPI layer (REST + WebSocket)**
  - Thin gateway: handles protocol/authentication and forwards requests to the dialogue service.
- **Dialogue service**
  - Keeps the active session in Redis (up to 30 messages) and prepares prompts for the LLM.
  - Uses `user_state`, Postgres, and vector memory to assemble context.
- **Background workers**
  - Produce session summaries and update `user_state`, the graph, and vector storage.
  - Schedule and send reminders via `reminder_queue`.

Further details live in:

- `docs/architecture/architecture.md` — component interactions and end-to-end flow.
- `docs/reference/db_schema.md` — relational tables (`users`, `goals`, `events`, `user_state`, `memory_vectors`, ...).
- `docs/architecture/cache_pipeline.md` — Redis cache layout and session termination triggers.
- `docs/api/api_auth.md` — Apple Sign In and JWT endpoints.
- `docs/api/api_users.md` — User profile and account management endpoints.
- `docs/api/api_admin.md` — Administrative actions (migrations).
- `docs/planning/tasks.md` — development roadmap.

## Local development
- Dependencies: `uv sync`
- Pre-commit: `uv run pre-commit install` and `uv run pre-commit run --all-files`
- Infrastructure (Postgres + Redis): `docker compose -f docker/docker-compose.yml up -d`
- API skeleton: `uv run python main.py` → http://127.0.0.1:8000
- Chat CLI: `uv run python -m cli.chat --url ws://127.0.0.1:8000/ws/chat`
- Database migrations: `uv run alembic upgrade head`
- Session cache knobs via `.env`:
  - `AIMI_SESSION_CACHE_TTL=600` (seconds before a session expires)
  - `AIMI_SESSION_CACHE_MAX_MESSAGES=30` (number of recent messages kept)
- JWT configuration via `.env`:
  - `AIMI_JWT_SECRET`, `AIMI_JWT_ALGORITHM`
  - `AIMI_JWT_ACCESS_EXPIRES_SECONDS`, `AIMI_JWT_REFRESH_EXPIRES_SECONDS`
- Command quick-reference: see [`docs/guides/dev_commands.md`](docs/guides/dev_commands.md)

> The service is still under heavy development. Keep the documentation up to date as implementation progresses.

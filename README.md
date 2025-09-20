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

- `docs/architecture.md` — component interactions and end-to-end flow.
- `docs/db_schema.md` — relational tables (`users`, `goals`, `events`, `user_state`, `memory_vectors`, ...).
- `docs/cache_pipeline.md` — Redis cache layout and session termination triggers.
- `docs/tasks.md` — development roadmap.

## Local development
- Dependencies: `uv sync`
- Pre-commit: `uv run pre-commit install` and `uv run pre-commit run --all-files`
- Infrastructure (Postgres + Redis): `docker compose -f docker/docker-compose.yml up -d`
- API skeleton: `uv run python main.py` → http://127.0.0.1:8000
- Chat CLI: `uv run python -m cli.chat --url ws://127.0.0.1:8000/ws/chat`

> The service is still under heavy development. Keep the documentation up to date as implementation progresses.

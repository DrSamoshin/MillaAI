# Admin API

## Migrate database
- **Method**: `POST`
- **Path**: `/v1/admin/migrate/`
- **Authentication**: Not required (use cautiously).

**Response**
```json
{
  "status": "success",
  "data": {"message": "Migrations applied"}
}
```

> Endpoint triggers `alembic upgrade head` on the server. Use with caution; idempotent on already-updated schemas.

# User Endpoints

## Get profile
- **Method**: `GET`
- **Path**: `/v1/users/me/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse[UserPayload]`):

```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "Display Name",
    "role": "user",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00+00:00"
  }
}
```

## Get user statistics
- **Method**: `GET`
- **Path**: `/v1/users/me/stats/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse[UserStatsResponse]`):

```json
{
  "status": "success",
  "data": {
    "goals": {
      "total": 5,
      "by_status": {
        "active": 3,
        "completed": 1,
        "paused": 1
      },
      "by_category": {
        "career": 2,
        "health": 1,
        "learning": 2
      }
    },
    "tasks": {
      "total": 12,
      "by_status": {
        "pending": 7,
        "in_progress": 3,
        "completed": 2
      }
    },
    "events": {
      "total": 8,
      "by_type": {
        "meeting": 4,
        "deadline": 2,
        "focus_time": 2
      },
      "by_status": {
        "scheduled": 6,
        "completed": 2
      }
    }
  }
}
```

## Delete account
- **Method**: `DELETE`
- **Path**: `/v1/users/me/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse[None]`):

```json
{
  "status": "success",
  "message": "User deleted"
}
```

> Deletion automatically cascades to remove all related data: chats, messages, goals, tasks, events, notifications, and mental states.

# User Endpoints

## Get profile
- **Method**: `GET`
- **Path**: `/v1/users/me/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse` envelope):

```json
{
  "status": "success",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "Display Name",
      "role": "user",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00+00:00"
    }
  }
}
```

## Delete account
- **Method**: `DELETE`
- **Path**: `/v1/users/me/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response**:

```json
{
  "status": "success",
  "data": {"message": "User deleted"}
}
```

> Deletion currently removes the user record; cascading removal of related entities (messages, events, memory) will be added alongside those modules.

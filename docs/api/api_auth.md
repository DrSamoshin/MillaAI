# Authentication API

## Apple Sign In
- **Method**: `POST`
- **Path**: `/v1/auth/apple-signin/`
- **Request body**

```json
{
  "apple_id": "string",
  "name": "string",
  "email": "string | null",
  "identity_token": "string | null"
}
```

- **Response** (enveloped by `SuccessResponse`)

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
    },
    "token": {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "Bearer",
      "expires_in": 900
    }
  }
}
```

## Refresh Token
- **Method**: `POST`
- **Path**: `/v1/auth/refresh/`
- **Request body**

```json
{
  "refresh_token": "string"
}
```

- **Response**

Identical structure to Apple Sign In response; new access/refresh tokens are issued.

## Notes
- `identity_token` validation is currently deferred; hook exists for future verification against Apple public keys.
- JWT settings are controlled through environment variables (`AIMI_JWT_SECRET`, `AIMI_JWT_ALGORITHM`, `AIMI_JWT_ACCESS_EXPIRES_SECONDS`, `AIMI_JWT_REFRESH_EXPIRES_SECONDS`).
- Refresh tokens are stateless; invalidation requires updating the signing secret.

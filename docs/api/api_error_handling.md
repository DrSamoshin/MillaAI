# API Error Handling

## Envelope Structure
- Every HTTP endpoint returns a consistent JSON envelope with root fields:
  - `status`: `"success"` or `"error"`.
  - `data`: payload for successful responses.
  - `error`: structured information for failures.
- HTTP status codes still reflect the outcome (2xx for success, 4xx/5xx for failures).

```json
{
  "status": "success",
  "data": {"status": "ok", "version": "0.1.0"}
}

{
  "status": "error",
  "error": {
    "code": "chat.payload_validation",
    "message": "Payload validation failed",
    "details": {"field": "message", "reason": "cannot be empty"}
  }
}
```

## Pydantic Schemas
- `SuccessResponse[T]` describes successful envelopes and wraps endpoint-specific payloads.
- `ErrorResponse` bundles failure metadata via `ErrorInfo` (`code`, `message`, optional `details`).

## Exception Flow
- Internal layers raise subclasses of `BaseAppError` with meaningful `code`, `message`, and `http_status`.
- FastAPI registers centralized handlers that:
  - Log errors with structured fields for observability.
  - Convert known exceptions (`BaseAppError`, `HTTPException`, `RequestValidationError`) into an `ErrorResponse` envelope.
  - Catch unexpected exceptions and return a generic `internal.server_error` response.
- This keeps response formatting consistent, simplifies client handling, and prevents leaking implementation details.

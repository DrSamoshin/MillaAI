from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from aimi.api.app import app
from aimi.api.deps import get_conversation_service


class StubConversationService:
    async def handle_incoming(self, *, user_id: str, message: str) -> dict[str, str]:
        return {"reply": f"echo: {message}", "model": "stub-model"}


@pytest.mark.asyncio
async def test_chat_send_returns_success_response() -> None:
    app.dependency_overrides[get_conversation_service] = (
        lambda: StubConversationService()
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/send",
            json={"user_id": "user-1", "message": "Hello"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"] == {"reply": "echo: Hello", "model": "stub-model"}

    app.dependency_overrides.clear()

"""Chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from aimi.api.v1.deps import get_conversation_service, get_current_user
from aimi.api.v1.schemas import ChatRequest, ChatResponsePayload, SuccessResponse
from aimi.db.models import User
from aimi.services.conversation import ConversationService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send/", response_model=SuccessResponse[ChatResponsePayload])
async def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[ChatResponsePayload]:
    user_id = payload.user_id or str(current_user.id)
    raw_result = await service.handle_incoming(user_id=user_id, message=payload.message)
    response = ChatResponsePayload.model_validate(raw_result)
    return SuccessResponse(data=response)

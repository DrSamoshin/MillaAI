"""Chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from aimi.api.deps import get_conversation_service
from aimi.api.schemas import ChatRequest, ChatResponsePayload, SuccessResponse
from aimi.services.conversation import ConversationService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=SuccessResponse[ChatResponsePayload])
async def send_message(
    payload: ChatRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[ChatResponsePayload]:
    raw_result = await service.handle_incoming(
        user_id=payload.user_id,
        message=payload.message,
    )
    response = ChatResponsePayload.model_validate(raw_result)
    return SuccessResponse(data=response)

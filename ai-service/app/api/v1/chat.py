"""M10 — POST /api/v1/chat"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(verify_internal_token)])


@router.post("", response_model=ChatResponse)
def chat_message(request: ChatRequest, db: Session = Depends(get_db)):
    service = ChatService(db)
    return service.process_message(session_id=request.session_id, message=request.message)
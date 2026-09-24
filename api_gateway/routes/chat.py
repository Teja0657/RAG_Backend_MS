import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api_gateway.crud import (
    create_conversation, 
    get_conversation, 
    add_message,
    get_user_conversations, 
    rename_conversation,
    update_pin_status,
    delete_conversation
    )
from api_gateway.auth import get_current_user
from api_gateway.database import get_db


router = APIRouter()


RAG_SERVICE_URL = "http://127.0.0.1:8001"


class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None=None

class RenameRequest(BaseModel):
    title: str


class PinRequest(BaseModel):
    pinned: bool
 

# ==========================================================
# NORMAL CHAT
# ==========================================================

@router.post("/api/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id=current_user["sub"]
    # 1. Create a new conversation if needed
    if request.conversation_id is None:
        conversation = create_conversation(
            db=db,
            user_id=user_id,
            title=request.question[:50],
        )

        conversation_id = conversation.id

    else:
        # 2. Make sure the conversation belongs to this user
        conversation = get_conversation(
            db=db,
            conversation_id=request.conversation_id,
            user_id=user_id
        )

        if conversation is None:
            return {
                "error": "Conversation not found"
            }

        conversation_id = conversation.id

    # 3. Save user's message
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=request.question,
    )

    # 4. Send question to RAG service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RAG_SERVICE_URL}/internal/query",
            json={
                "question": request.question,
            },
            timeout=None,
        )

        response.raise_for_status()
        rag_result = response.json()

    answer = rag_result["answer"]

    # 5. Save assistant response
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
    )

    # 6. Return response to frontend
    return {
        "answer": answer,
        "conversation_id": conversation_id,
    }


# ==========================================================
# STREAMING CHAT
# ==========================================================

@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):

    async def event_generator():

        async with httpx.AsyncClient() as client:

            async with client.stream(
                "POST",
                f"{RAG_SERVICE_URL}/internal/query/stream",
                json={
                    "question": request.question
                },
                timeout=None,
            ) as response:

                response.raise_for_status()

                async for chunk in response.aiter_bytes():

                    yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/chats")
def list_chats(db: Session = Depends(get_db), current_user=Depends(get_current_user),):
    user_id=current_user["sub"]

    conversations= get_user_conversations(
        db=db,
        user_id=user_id,
    )
    return [
        {
            "id": conversation.id,
            "title": conversation.title,
            "pinned": conversation.pinned,
            "created_at": conversation.created_at,
        }
        for conversation in conversations
    ]

@router.get("/api/chats/{conversation_id}")
def get_chat(
    conversation_id: int, 
    db: Session= Depends(get_db),
    current_user= Depends(get_current_user),
    ):
    conversation=get_conversation(
        db=db, 
        conversation_id=conversation_id, 
        user_id=current_user["sub"]
        )
    
    if conversation is None:
        return{
            "error": "Conversation not found"
        }
    
    return {
        "id": conversation.id,
        "title": conversation.title,
        "pinned": conversation.pinned,
        "created_at": conversation.created_at,
        "messages":[
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at
            }
            for message in conversation.messages
        ]
    }


# rename chat
@router.patch("/api/chats/{conversation_id}/rename")
def rename_chat(
    conversation_id: int,
    request: RenameRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id=current_user["sub"]

    conversation = rename_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        title=request.title,
    )

    if conversation is None:
        return {"error": "Conversation not found"}

    return {
        "id": conversation.id,
        "title": conversation.title,
        "pinned": conversation.pinned,
    }

#pin chat
@router.patch("/api/chats/{conversation_id}/pin")
def pin_chat(
    conversation_id: int,
    request: PinRequest,
    db: Session = Depends(get_db),
    current_user= Depends(get_current_user)
):
    user_id=current_user["sub"]
    result = update_pin_status(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        pinned=request.pinned,
    )



    if result is None:
        raise HTTPException(
            status_code=404, 
            detail="Conversation not found"
        )

    if result == "limit_reached":
        raise HTTPException(
            status_code=400, 
            detail="You can pin a maximum of 3 chats."
        )

    return {
        "id": result.id,
        "pinned": result.pinned,
    }

#delet chat
@router.delete("/api/chats/{conversation_id}")
def delete_chat(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    user_id= current_user["sub"]
    
    deleted = delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if not deleted:
        return {"error": "Conversation not found"}

    return {"message": "Conversation deleted successfully"}
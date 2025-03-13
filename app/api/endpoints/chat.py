from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from prisma.models import Chat, Message, User

from app.schemas.chat import (
    ChatCreate,
    ChatOut,
    ChatUpdate,
    MessageCreate,
    MessageOut,
)
from app.services.auth import get_current_active_user
from app.services.chat import (
    add_chat_participant,
    create_chat,
    create_message,
    delete_chat,
    generate_ai_response,
    get_chat,
    get_chat_messages,
    get_user_chats,
    mark_messages_as_read,
    remove_chat_participant,
    update_chat,
)

router = APIRouter()


@router.post("/", response_model=ChatOut)
async def create_new_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new chat."""
    chat = await create_chat(chat_data, current_user.id, chat_data.participant_ids)
    return chat


@router.get("/", response_model=List[ChatOut])
async def read_user_chats(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get all chats for the current user."""
    chats = await get_user_chats(current_user.id)
    return chats


@router.get("/{chat_id}", response_model=ChatOut)
async def read_chat(
    chat_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get a specific chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is a participant
    is_participant = any(p.userId == current_user.id for p in chat.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this chat",
        )
    
    return chat


@router.put("/{chat_id}", response_model=ChatOut)
async def update_existing_chat(
    chat_data: ChatUpdate,
    chat_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is the owner
    if chat.ownerId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update this chat",
        )
    
    updated_chat = await update_chat(chat_id, chat_data)
    return updated_chat


@router.delete("/{chat_id}")
async def delete_existing_chat(
    chat_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Delete a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is the owner
    if chat.ownerId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete this chat",
        )
    
    success = await delete_chat(chat_id)
    return {"success": success}


@router.post("/{chat_id}/participants", response_model=ChatOut)
async def add_participant(
    chat_id: str = Path(...),
    user_id: str = Query(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Add a participant to a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is the owner
    if chat.ownerId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can add participants",
        )
    
    # Check if user is already a participant
    is_participant = any(p.userId == user_id for p in chat.participants)
    if is_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a participant",
        )
    
    await add_chat_participant(chat_id, user_id)
    updated_chat = await get_chat(chat_id)
    return updated_chat


@router.delete("/{chat_id}/participants")
async def remove_participant(
    chat_id: str = Path(...),
    user_id: str = Query(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Remove a participant from a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is the owner or if they are removing themselves
    if chat.ownerId != current_user.id and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can remove other participants",
        )
    
    # Check if user is a participant
    is_participant = any(p.userId == user_id for p in chat.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a participant",
        )
    
    # Don't allow removing the owner
    if user_id == chat.ownerId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner from the chat",
        )
    
    success = await remove_chat_participant(chat_id, user_id)
    return {"success": success}


@router.post("/{chat_id}/messages", response_model=MessageOut)
async def create_chat_message(
    message_data: MessageCreate,
    chat_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new message in a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is a participant
    is_participant = any(p.userId == current_user.id for p in chat.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this chat",
        )
    
    message = await create_message(chat_id, current_user.id, message_data)
    return message


@router.get("/{chat_id}/messages", response_model=List[MessageOut])
async def read_chat_messages(
    chat_id: str = Path(...),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get messages for a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is a participant
    is_participant = any(p.userId == current_user.id for p in chat.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this chat",
        )
    
    messages = await get_chat_messages(chat_id, limit, offset)
    
    # Mark messages as read
    await mark_messages_as_read(chat_id, current_user.id)
    
    return messages


@router.post("/{chat_id}/ai-response", response_model=MessageOut)
async def generate_chat_ai_response(
    chat_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Generate an AI response in a chat."""
    chat = await get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
        )
    
    # Check if the user is a participant
    is_participant = any(p.userId == current_user.id for p in chat.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this chat",
        )
    
    ai_message = await generate_ai_response(chat_id, current_user.id)
    return ai_message
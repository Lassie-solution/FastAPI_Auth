from typing import List, Optional

from prisma.models import Chat, ChatParticipant, Message, User

from app.schemas.chat import ChatCreate, ChatUpdate, MessageCreate
from app.services.openai import Message as OpenAIMessage
from app.services.openai import generate_chat_response, moderate_content


async def create_chat(
    chat_data: ChatCreate, 
    owner_id: str,
    participant_ids: Optional[List[str]] = None
) -> Chat:
    """Create a new chat."""
    # Create the chat
    chat = await Chat.prisma().create(
        data={
            "title": chat_data.title,
            "description": chat_data.description,
            "isGroup": chat_data.is_group,
            "ownerId": owner_id,
        }
    )
    
    # Add the owner as a participant
    await ChatParticipant.prisma().create(
        data={
            "chatId": chat.id,
            "userId": owner_id,
        }
    )
    
    # Add other participants if provided
    if participant_ids:
        for user_id in participant_ids:
            if user_id != owner_id:  # Skip owner as they're already added
                await ChatParticipant.prisma().create(
                    data={
                        "chatId": chat.id,
                        "userId": user_id,
                    }
                )
    
    return chat


async def get_chat(chat_id: str) -> Optional[Chat]:
    """Get a chat by ID."""
    chat = await Chat.prisma().find_unique(
        where={"id": chat_id},
        include={
            "participants": {
                "include": {
                    "user": True
                }
            }
        }
    )
    return chat


async def update_chat(chat_id: str, chat_data: ChatUpdate) -> Optional[Chat]:
    """Update a chat."""
    update_data = chat_data.dict(exclude_unset=True)
    
    if not update_data:
        # No fields to update
        chat = await get_chat(chat_id)
        return chat
    
    chat = await Chat.prisma().update(
        where={"id": chat_id},
        data=update_data,
    )
    return chat


async def delete_chat(chat_id: str) -> bool:
    """Delete a chat."""
    await Chat.prisma().delete(where={"id": chat_id})
    return True


async def get_user_chats(user_id: str) -> List[Chat]:
    """Get all chats for a user."""
    chat_participants = await ChatParticipant.prisma().find_many(
        where={"userId": user_id},
        include={"chat": True}
    )
    return [cp.chat for cp in chat_participants]


async def add_chat_participant(chat_id: str, user_id: str) -> ChatParticipant:
    """Add a user to a chat."""
    participant = await ChatParticipant.prisma().create(
        data={
            "chatId": chat_id,
            "userId": user_id,
        }
    )
    return participant


async def remove_chat_participant(chat_id: str, user_id: str) -> bool:
    """Remove a user from a chat."""
    await ChatParticipant.prisma().delete(
        where={
            "chatId_userId": {
                "chatId": chat_id,
                "userId": user_id,
            }
        }
    )
    return True


async def create_message(
    chat_id: str, 
    user_id: str, 
    message_data: MessageCreate
) -> Message:
    """Create a new message in a chat."""
    # Check if content is appropriate
    is_flagged = await moderate_content(message_data.content)
    if is_flagged:
        raise ValueError("Message content has been flagged as inappropriate.")
    
    message = await Message.prisma().create(
        data={
            "content": message_data.content,
            "chatId": chat_id,
            "userId": user_id,
            "isAI": False,
        }
    )
    
    # Generate AI response if requested
    if message_data.generate_ai_response:
        await generate_ai_response(chat_id, user_id)
    
    return message


async def get_chat_messages(chat_id: str, limit: int = 50, offset: int = 0) -> List[Message]:
    """Get messages for a chat."""
    messages = await Message.prisma().find_many(
        where={"chatId": chat_id},
        include={"user": True},
        order_by=[{"createdAt": "desc"}],
        take=limit,
        skip=offset,
    )
    return list(reversed(messages))  # Return in chronological order


async def mark_messages_as_read(chat_id: str, user_id: str) -> int:
    """Mark all unread messages in a chat as read for a user."""
    # This is a simplified version. In a real app, you'd want to track read status per user
    result = await Message.prisma().update_many(
        where={
            "chatId": chat_id,
            "isRead": False,
            "userId": {"not": user_id},  # Only mark messages from other users
        },
        data={"isRead": True},
    )
    return result.count


async def generate_ai_response(chat_id: str, user_id: str) -> Message:
    """Generate an AI response to the latest messages in a chat."""
    # Get recent messages to build context
    recent_messages = await get_chat_messages(chat_id, limit=10)
    
    # Format messages for OpenAI
    formatted_messages = []
    for msg in recent_messages:
        role = "assistant" if msg.isAI else "user"
        formatted_messages.append(OpenAIMessage(role=role, content=msg.content))
    
    # Add a system message
    formatted_messages.insert(0, OpenAIMessage(
        role="system",
        content="You are a helpful assistant in a chat conversation. Provide concise, helpful responses."
    ))
    
    # Generate response
    response = await generate_chat_response(formatted_messages)
    
    # Save AI message to database
    ai_message = await Message.prisma().create(
        data={
            "content": response.content,
            "chatId": chat_id,
            "userId": user_id,  # Using the same user ID for simplicity
            "isAI": True,
        }
    )
    
    return ai_message
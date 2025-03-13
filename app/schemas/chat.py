from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.user import UserOut


class ChatParticipantBase(BaseModel):
    user_id: str


class ChatParticipantCreate(ChatParticipantBase):
    pass


class ChatParticipantOut(ChatParticipantBase):
    id: str
    chat_id: str
    joined_at: datetime
    user: UserOut

    class Config:
        orm_mode = True


class ChatBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_group: bool = False


class ChatCreate(ChatBase):
    participant_ids: Optional[List[str]] = None


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class ChatOut(ChatBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    participants: List[ChatParticipantOut]
    owner: Optional[UserOut] = None

    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    generate_ai_response: bool = False


class MessageOut(MessageBase):
    id: str
    chat_id: str
    user_id: str
    is_ai: bool
    is_read: bool
    created_at: datetime
    updated_at: datetime
    user: UserOut

    class Config:
        orm_mode = True
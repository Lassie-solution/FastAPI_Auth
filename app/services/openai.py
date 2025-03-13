import logging
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings

# Configure OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = settings.OPENAI_MODEL

logger = logging.getLogger(__name__)


class Message(BaseModel):
    role: str
    content: str


class ChatCompletion(BaseModel):
    content: str
    model: str
    tokens_used: int


async def generate_chat_response(
    messages: List[Message],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> ChatCompletion:
    """Generate a response from OpenAI Chat models."""
    model = model or MODEL
    
    try:
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        response = client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        completion = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        return ChatCompletion(
            content=completion,
            model=model,
            tokens_used=tokens_used,
        )
    
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        raise Exception(f"Failed to generate response: {str(e)}")


async def moderate_content(content: str) -> bool:
    """
    Check if content is appropriate using OpenAI's moderation endpoint.
    Returns True if content is flagged, False otherwise.
    """
    try:
        response = client.moderations.create(input=content)
        return response.results[0].flagged
    except Exception as e:
        logger.error(f"Error moderating content: {str(e)}")
        # Default to not flagged if moderation fails
        return False
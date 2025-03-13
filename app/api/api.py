from fastapi import APIRouter

from app.api.endpoints import admin, auth, chat

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chats", tags=["chats"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
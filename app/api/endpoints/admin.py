from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from prisma.models import Chat, Message, User

from app.schemas.user import UserOut, UserUpdate
from app.services.auth import get_current_admin_user, update_user

router = APIRouter()


@router.get("/users", response_model=List[UserOut])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Get all users (admin only)."""
    users = await User.prisma().find_many(
        skip=skip,
        take=limit,
    )
    return users


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str = Path(...),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Get a specific user (admin only)."""
    user = await User.prisma().find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user_admin(
    user_update: UserUpdate,
    user_id: str = Path(...),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Update a user (admin only)."""
    user = await User.prisma().find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    
    updated_user = await update_user(user_id, user_update)
    return updated_user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str = Path(...),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Delete a user (admin only)."""
    user = await User.prisma().find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    
    # Don't allow admins to delete themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete their own account",
        )
    
    await User.prisma().delete(where={"id": user_id})
    return {"success": True}


@router.get("/chats", response_model=List[Chat])
async def get_all_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Get all chats (admin only)."""
    chats = await Chat.prisma().find_many(
        skip=skip,
        take=limit,
        include={
            "owner": True,
            "participants": {
                "include": {
                    "user": True
                }
            }
        }
    )
    return chats


@router.get("/statistics")
async def get_system_stats(
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Get system statistics (admin only)."""
    total_users = await User.prisma().count()
    total_chats = await Chat.prisma().count()
    total_messages = await Message.prisma().count()
    
    # Get user stats by auth provider
    users_by_provider = await User.prisma().group_by(
        by=["authProvider"],
        _count={"id": True},
    )
    
    # Get recent signups (last 7 days)
    from datetime import datetime, timedelta
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    recent_signups = await User.prisma().count(
        where={"createdAt": {"gte": one_week_ago.isoformat()}}
    )
    
    # Get AI message stats
    ai_messages = await Message.prisma().count(
        where={"isAI": True}
    )
    
    return {
        "total_users": total_users,
        "total_chats": total_chats,
        "total_messages": total_messages,
        "users_by_provider": users_by_provider,
        "recent_signups": recent_signups,
        "ai_messages": ai_messages,
        "user_messages": total_messages - ai_messages,
    }


@router.post("/make-admin/{user_id}")
async def make_user_admin(
    user_id: str = Path(...),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Promote a user to admin (admin only)."""
    user = await User.prisma().find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    
    if user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an admin",
        )
    
    updated_user = await User.prisma().update(
        where={"id": user_id},
        data={"role": "ADMIN"},
    )
    
    return {"success": True, "user": updated_user}
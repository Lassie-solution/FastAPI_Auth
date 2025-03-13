from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from prisma.models import User
from pydantic import EmailStr

from app.core.config import settings
from app.schemas.user import UserCreate, UserUpdate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token for user authentication."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
    user = await User.prisma().find_unique(where={"id": user_id})
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if the current user is active."""
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if the current user is an admin."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


async def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against a provided password."""
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = await User.prisma().find_unique(where={"email": email})
    if not user or user.authProvider != "EMAIL":
        return None
    
    # In a real implementation, you would store the password hash in the database
    stored_password_hash = user.passwordHash if hasattr(user, 'passwordHash') else None
    
    if not stored_password_hash or not await verify_password(password, stored_password_hash):
        return None
    
    return user


async def authenticate_google_user(token: str) -> User:
    """Authenticate a user with Google token."""
    # In a real implementation, you would verify the token with Google
    # and extract user information from the token
    try:
        # Placeholder: Assume we extracted email, name, and Google ID
        email = "google_user@example.com"  # From token verification
        name = "Google User"               # From token verification
        google_id = "google123456"         # From token verification
        
        # Find existing user by auth provider ID
        user = await User.prisma().find_first(
            where={
                "authProvider": "GOOGLE",
                "authProviderId": google_id
            }
        )
        
        # If user doesn't exist, find by email
        if not user:
            user = await User.prisma().find_unique(
                where={"email": email}
            )
            
            # If user exists but with different auth provider, update it
            if user and user.authProvider != "GOOGLE":
                user = await User.prisma().update(
                    where={"id": user.id},
                    data={
                        "authProvider": "GOOGLE",
                        "authProviderId": google_id
                    }
                )
        
        # If user still doesn't exist, create a new one
        if not user:
            user = await User.prisma().create(
                data={
                    "email": email,
                    "name": name,
                    "authProvider": "GOOGLE",
                    "authProviderId": google_id,
                    "role": "USER"
                }
            )
        
        return user
    
    except Exception as e:
        # Log the error
        print(f"Google authentication error: {str(e)}")
        return None


async def authenticate_apple_user(token: str) -> User:
    """Authenticate a user with Apple token."""
    # In a real implementation, you would verify the token with Apple
    # and extract user information
    try:
        # Placeholder: Assume we extracted email, name, and Apple ID
        email = "apple_user@example.com"  # From token verification
        name = "Apple User"               # From token verification
        apple_id = "apple123456"          # From token verification
        
        # Find existing user by auth provider ID
        user = await User.prisma().find_first(
            where={
                "authProvider": "APPLE",
                "authProviderId": apple_id
            }
        )
        
        # If user doesn't exist, find by email
        if not user:
            user = await User.prisma().find_unique(
                where={"email": email}
            )
            
            # If user exists but with different auth provider, update it
            if user and user.authProvider != "APPLE":
                user = await User.prisma().update(
                    where={"id": user.id},
                    data={
                        "authProvider": "APPLE",
                        "authProviderId": apple_id
                    }
                )
        
        # If user still doesn't exist, create a new one
        if not user:
            user = await User.prisma().create(
                data={
                    "email": email,
                    "name": name,
                    "authProvider": "APPLE",
                    "authProviderId": apple_id,
                    "role": "USER"
                }
            )
        
        return user
    
    except Exception as e:
        # Log the error
        print(f"Apple authentication error: {str(e)}")
        return None


async def register_email_user(email: str, password: str, name: Optional[str] = None) -> User:
    """Register a new user with email and password."""
    # Check if user already exists
    existing_user = await User.prisma().find_unique(where={"email": email})
    if existing_user:
        raise ValueError("User with this email already exists")
    
    # Hash the password
    hashed_password = await get_password_hash(password)
    
    # Create user
    user = await User.prisma().create(
        data={
            "email": email,
            "name": name,
            "authProvider": "EMAIL",
            "passwordHash": hashed_password,
            "role": "USER",
        }
    )
    
    return user


async def create_user(user_data: UserCreate) -> User:
    """Create a new user."""
    # Handle password if it's email registration
    password_hash = None
    if user_data.auth_provider == "EMAIL" and user_data.password:
        password_hash = await get_password_hash(user_data.password)
    
    user = await User.prisma().create(data={
        "email": user_data.email,
        "name": user_data.name,
        "authProvider": user_data.auth_provider,
        "authProviderId": user_data.auth_provider_id,
        "passwordHash": password_hash,
        "role": "USER",  # Default role
    })
    return user


async def update_user(user_id: str, user_data: UserUpdate) -> User:
    """Update an existing user."""
    update_data = user_data.dict(exclude_unset=True)
    
    if not update_data:
        # No fields to update
        user = await User.prisma().find_unique(where={"id": user_id})
        return user
    
    user = await User.prisma().update(
        where={"id": user_id},
        data=update_data,
    )
    return user
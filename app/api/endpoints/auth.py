@router.post("/google", response_model=Token)
async def login_google(
    token: str = Body(..., embed=True),
) -> Any:
    """Login with Google auth."""
    user = await authenticate_google_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with Google",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/apple", response_model=Token)
async def login_apple(
    token: str = Body(..., embed=True),
) -> Any:
    """Login with Apple auth."""
    user = await authenticate_apple_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with Apple",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get current user."""
    return current_user


@router.put("/me", response_model=UserOut)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update current user."""
    updated_user = await update_user(current_user.id, user_update)
    return updated_user
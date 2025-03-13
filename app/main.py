from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from app.api.api import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.db.init_db import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0",
)

# Set up CORS
origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",  # For local development
    "http://localhost:5173",  # For Vite development server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up exception handlers
setup_exception_handlers(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks."""
    await init_db()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Welcome to Chat App API"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
import logging
from typing import Optional

from prisma import Prisma
from prisma.models import User

logger = logging.getLogger(__name__)

prisma_client = Prisma()


async def init_db() -> None:
    """Initialize the database."""
    try:
        # Connect to the database
        await prisma_client.connect()
        logger.info("Connected to the database")
        
        # Create default admin if none exists
        await create_default_admin()
        
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


async def create_default_admin() -> Optional[User]:
    """Create a default admin user if no admin exists."""
    # Check if any admin exists
    admin = await User.prisma().find_first(
        where={"role": "ADMIN"}
    )
    
    if admin:
        logger.info("Admin user already exists")
        return None
    
    logger.info("Creating default admin user")
    
    # Create default admin
    admin = await User.prisma().create(
        data={
            "email": "admin@example.com",
            "name": "Default Admin",
            "role": "ADMIN",
            "authProvider": "EMAIL",
            "passwordHash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        }
    )
    
    logger.info(f"Default admin created with ID: {admin.id}")
    return admin
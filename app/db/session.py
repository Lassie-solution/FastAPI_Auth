from prisma import Prisma

# Create a Prisma client
prisma_client = Prisma()


async def get_db():
    """Get database client."""
    try:
        await prisma_client.connect()
        yield prisma_client
    finally:
        await prisma_client.disconnect()
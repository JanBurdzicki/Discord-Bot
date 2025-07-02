"""Database setup script"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from .models import Base
from .session import engine

async def setup_database():
    """Create all database tables"""
    print("🔄 Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drop all tables first
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(setup_database())
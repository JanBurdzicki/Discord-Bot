#!/usr/bin/env python3
"""
Database table setup script for Discord Bot
Run this after setting up PostgreSQL database
"""

import asyncio
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import Base
from db.session import engine

async def setup_db():
    """Create all database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")

        # List the tables that were created
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")

    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database and user exist")
        print("3. .env file has correct database credentials")
        print("4. Required dependencies are installed: pip install sqlalchemy asyncpg python-dotenv")
        sys.exit(1)

    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Setting up Discord Bot database tables...")
    asyncio.run(setup_db())
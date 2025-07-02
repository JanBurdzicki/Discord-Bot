#!/bin/bash

# Load environment variables from .env file
if [ -f "../.env" ]; then
    # Export all variables from .env file
    export $(cat ../.env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found!"
    exit 1
fi

echo "🔄 Setting up PostgreSQL database..."

# Create database and user
sudo -u postgres psql << EOF
-- Create user if not exists
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "✅ Database and user created successfully!"

# Create Python virtual environment if it doesn't exist
if [ ! -d "../venv" ]; then
    echo "🔄 Creating Python virtual environment..."
    python3 -m venv ../venv
fi

# Activate virtual environment
source ../venv/bin/activate

# Install or upgrade required packages
echo "🔄 Installing/upgrading required packages..."
pip install -r ../requirements.txt

# Run database migrations
echo "🔄 Running database migrations..."
cd ../src
python -c "
from database.session import engine
from database.models import Base
import asyncio

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
"

echo "✅ Database setup complete!"
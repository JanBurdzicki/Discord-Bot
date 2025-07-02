#!/bin/bash

# Discord Bot PostgreSQL Setup Script
echo "Setting up PostgreSQL database for Discord Bot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo -e "${RED}PostgreSQL is not running. Starting it...${NC}"
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

echo -e "${GREEN}PostgreSQL is running!${NC}"

# Database configuration
DB_NAME="discord_bot_db"
DB_USER="discord_bot_user"

echo -e "${YELLOW}Please enter a secure password for the database user:${NC}"
read -s DB_PASSWORD

echo -e "${YELLOW}Creating database and user...${NC}"

# Create database and user
sudo -u postgres psql << EOF
-- Create database
CREATE DATABASE $DB_NAME;

-- Create user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to the new database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

\q
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Database setup completed successfully!${NC}"

    echo "DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
    echo "DB_HOST=localhost"
    echo "DB_PORT=5432"
    echo "DB_NAME=$DB_NAME"
    echo "DB_USER=$DB_USER"
    echo "DB_PASSWORD=$DB_PASSWORD"

else
    echo -e "${RED}Database setup failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Setup complete! Next steps:${NC}"

echo "1. Update your database credentials in .env file"
echo "2. Run: python3 db/setup_db.py to create tables"
echo "3. Run your bot!"
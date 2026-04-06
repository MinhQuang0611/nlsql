#!/bin/bash

# Configuration
REPO_URL="ssh://git@gitlab.aisoftech.vn:1024/dungdq/text2dashboard.git"
CONFIG_ZIP="deploy_config.zip"
CONFIG_DIR="deploy_package"

echo ">>> Pulling latest code from GitLab..."
# Ensure the remote is set correctly (optional)
# git remote set-url origin $REPO_URL
git pull origin main

if [ -f "$CONFIG_ZIP" ]; then
    echo ">>> Unzipping configuration files..."
    unzip -o "$CONFIG_ZIP"
    
    echo ">>> Copying .env and config.py to root..."
    if [ -f "$CONFIG_DIR/.env" ]; then
        cp "$CONFIG_DIR/.env" .env
    fi
    if [ -f "$CONFIG_DIR/config.py" ]; then
        cp "$CONFIG_DIR/config.py" config.py
    fi
    
    # Optional: Clean up unzipped folder
    # rm -rf "$CONFIG_DIR"
else
    echo "!!! Warning: $CONFIG_ZIP not found. Skipping config update."
fi

echo ">>> Deploying with Docker Compose (Production)..."
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

echo ">>> Waiting for DB to be ready..."
sleep 10 # Give the DB time to start

if [ -f "$CONFIG_DIR/db_backup.sql" ]; then
    echo ">>> Restoring database from $CONFIG_DIR/db_backup.sql..."
    cat "$CONFIG_DIR/db_backup.sql" | docker exec -i nlsql_postgres_prod psql -U postgres postgres
    echo ">>> Database restoration completed."
else
    echo ">>> No db_backup.sql found. Skipping restoration."
fi

echo ">>> Deployment completed successfully!"

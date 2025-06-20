#!/usr/bin/env bash
# start.sh
# Final startup script that forces the DATABASE_URL into each command's environment.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Run database migrations, ensuring it sees the correct database.
echo "Running database migrations..."
DATABASE_URL=$DATABASE_URL python -m flask db upgrade

# 3. Seed the database, ensuring it sees the correct database.
echo "Seeding the database..."
DATABASE_URL=$DATABASE_URL python -m flask seed

# 4. Start the Gunicorn server, ensuring it sees the correct database.
echo "Starting Gunicorn server..."
gunicorn "app:app" --env DATABASE_URL="$DATABASE_URL"
```
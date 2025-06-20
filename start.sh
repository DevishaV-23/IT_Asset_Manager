#!/usr/bin/env bash
# start.sh
# Final startup script using robust Flask commands.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Run database migrations
echo "Running database migrations..."
python -m flask db upgrade

# 3. Seed the database using our custom Flask command
echo "Seeding the database..."
python -m flask seed

# 4. Start the Gunicorn server
echo "Starting Gunicorn server..."
python -m gunicorn app:app

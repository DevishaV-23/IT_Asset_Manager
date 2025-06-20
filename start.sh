#!/usr/bin/env bash
# start.sh
# Final version: Explicitly disable dotenv loading for the Flask CLI.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Set FLASK_APP for the script's context. This is best practice.
export FLASK_APP=app.py

# 3. Run database migrations, telling Flask NOT to load any .env files.
echo "Running database migrations..."
python -m flask --no-load-dotenv db upgrade

# 4. Seed the database, also telling Flask NOT to load any .env files.
echo "Seeding the database..."
python -m flask --no-load-dotenv seed

# 5. Start the Gunicorn server.
echo "Starting Gunicorn server..."
# Gunicorn does not use the Flask CLI, so it correctly inherits the environment.
gunicorn app:app
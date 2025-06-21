#!/usr/bin/env bash
# start.sh
# Final production version.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Set FLASK_APP for the script's context
export FLASK_APP=app.py

# 3. Run database migrations
# This will apply any new migrations you add in the future.
echo "Running database migrations..."
./.venv/bin/flask db upgrade

# 4. Seed the database
# This is safe to run every time, as it's designed to not re-create data.
echo "Seeding the database..."
./.venv/bin/flask seed

# 5. Start the Gunicorn server
echo "Starting Gunicorn server..."
./.venv/bin/gunicorn app:app
#!/usr/bin/env bash
# start.sh
# Final version: Calls executables directly from the virtual environment.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Install dependencies. This creates the .venv folder.
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Set FLASK_APP for the script's context. This is best practice.
export FLASK_APP=app.py

# 3. Run database migrations by calling the 'flask' executable directly.
# This ensures we use the one that was just installed.
echo "Running database migrations..."
./.venv/bin/flask db upgrade

# 4. Seed the database by calling the 'flask' executable directly.
echo "Seeding the database..."
./.venv/bin/flask seed

# 5. Start the Gunicorn server by calling its executable directly.
echo "Starting Gunicorn server..."
./.venv/bin/gunicorn app:app

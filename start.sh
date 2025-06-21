#!/usr/bin/env bash
# A more verbose start.sh for debugging

# This makes the script exit on any error
set -e
# This prints each command to the log before it is executed
set -x

echo "Installing dependencies..."
pip install -r requirements.txt

export FLASK_APP=app.py

# --- NEW DEBUGGING STEPS ---
echo "--- Checking database state before migration ---"

# The '|| true' part ensures that the script won't exit if these commands fail
# (which they will if the database is brand new and empty).
./.venv/bin/flask db current || true
# --- End Debugging ---

echo "Running database migrations..."
./.venv/bin/flask db upgrade

echo "--- Checking database state AFTER migration ---"
./.venv/bin/flask db current || true
echo "--- End Debugging ---"

echo "Seeding the database..."
./.venv/bin/flask seed

echo "Starting Gunicorn server..."
set +x # Turn off command printing before starting the server
./.venv/bin/gunicorn app:app
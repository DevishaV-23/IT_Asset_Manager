#!/usr/bin/env bash
# start.sh
# This script ensures all commands run in the same context.

# Exit immediately if a command exits with a non-zero status.
set -e

# Install all dependencies from requirements.txt
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations. We use 'python -m flask' to ensure
# the command is found in the environment we just installed into.
echo "Running database migrations..."
python -m flask db upgrade

DEBUG: Print the DATABASE_URL to verify it exists
echo "--- DEBUGGING: Verifying DATABASE_URL ---"
echo "DATABASE_URL is: ${DATABASE_URL}"
echo "--- END DEBUGGING ---"

# Seed the database with initial data (this solves the no-shell problem)
echo "Seeding the database..."
python -c "from asset_manager import create_app; from seed import seed_database; app = create_app(); app.app_context().push(); seed_database()"

# Start the Gunicorn server. We use 'python -m gunicorn' for the same reason.
echo "Starting Gunicorn server..."
python -m gunicorn app:app

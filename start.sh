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

# Start the Gunicorn server. We use 'python -m gunicorn' for the same reason.
echo "Starting Gunicorn server..."
python -m gunicorn app:app

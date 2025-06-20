#!/usr/bin/env bash
# start.sh
# Final startup script that handles all deployment steps in one environment.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. DEBUG: Print the DATABASE_URL to verify it exists BEFORE any database operations
echo "--- DEBUGGING: Verifying DATABASE_URL ---"
echo "DATABASE_URL is: ${DATABASE_URL}"
echo "--- END DEBUGGING ---"

# 3. Run database migrations
echo "Running database migrations..."
python -m flask db upgrade

# 4. Seed the database with initial data
echo "Seeding the database..."
python -c "from asset_manager import create_app; from seed import seed_database; app = create_app(); app.app_context().push(); seed_database()"

# 5. Start the Gunicorn server
echo "Starting Gunicorn server..."
python -m gunicorn app:app

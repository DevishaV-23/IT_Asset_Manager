# migrations/env.py

from logging.config import fileConfig
from alembic import context

# --- Start of New Code ---

# 1. Create an instance of your Flask application
# This is the most important step, as it ensures everything is initialized.
from asset_manager import create_app
app = create_app()

# 2. Import your database object and models
# Now that the app exists, we can safely import these.
from asset_manager.extensions import db
import asset_manager.models

# --- End of New Code ---


# Standard Alembic configuration from here
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the metadata from your app's db object for autogenerate support
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Use the app's configured database URL
    url = app.config.get('SQLALCHEMY_DATABASE_URI')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use the engine from the app's SQLAlchemy instance
    connectable = db.get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


# This is the entry point for the migration script.
# We wrap it in our app's context.
with app.app_context():
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
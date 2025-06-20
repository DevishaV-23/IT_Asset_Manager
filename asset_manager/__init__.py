import os
import click
from flask import Flask, redirect, url_for, flash, request
from functools import wraps
from flask_login import current_user
from . import models
from .extensions import db, login_manager, migrate
from dotenv import load_dotenv
from seed import seed_database


# A custom decorator that restricts access to a route to admin users only
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('assets.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# This function is responsible for creating and configuring the Flask application instance.
def create_app(config_override=None):

    if os.environ.get('RENDER') is None:
        load_dotenv()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    app = Flask(__name__,
                root_path=project_root,
                instance_relative_config=True)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-dev')
    
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # This line ensures compatibility between different database URL formats
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # When DATABASE_URL is not set, we fall back to SQLite in the instance folder.
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or f"sqlite:///{os.path.join(app.instance_path, 'it_asset_manager.db')}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config_override:
        app.config.update(config_override)
    
    # Set a secret key for session security (e.g., for signing cookies).
    app.config['SECRET_KEY'] = os.urandom(24)
    # Configure the database connection (using SQLite in this case).
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///it_asset_manager.db'
    # Disable a Flask-SQLAlchemy feature that is not needed and can be noisy.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config_override:
        app.config.update(config_override)

    # Connect the SQLAlchemy database object to the app.
    db.init_app(app)
    # Connect the Flask-Migrate extension for database migrations.
    migrate.init_app(app, db)
    # Connect the Flask-Login extension for user session management.
    login_manager.init_app(app, db)
    # Tell Flask-Login where to redirect users if they try to access a protected page without being logged in.
    login_manager.login_view = 'auth.login'

    # This function tells Flask-Login how to load a user from the database given the user ID that is stored in the session cookie.
    @login_manager.user_loader
    def load_user(user_id):
         return db.session.get(models.User, int(user_id))
    
    @app.cli.command("seed")
    def seed_command():
        """Seeds the database with initial data."""
        seed_database()
        click.echo("Database seeded successfully.")

    # The 'with app.app_context()' block makes the application instance available for operations like blueprint registration and database creation.
    with app.app_context():
        # Blueprints are collections of routes from other files. This connects them
        from . import auth
        app.register_blueprint(auth.auth_bp)

        from . import assets
        app.register_blueprint(assets.assets_bp)

        from . import admin
        app.register_blueprint(admin.admin_bp)
 

        @app.route('/')
        def index():
            """Redirects the root URL to the login page."""
            return redirect(url_for('auth.login'))

    return app
    
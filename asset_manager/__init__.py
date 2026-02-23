import os
import click
from flask import Flask, redirect, url_for, flash, request
from functools import wraps
from flask_login import current_user
from . import models
from .extensions import db, login_manager, migrate, csrf

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
    basedir = os.path.abspath(os.path.dirname(__file__))
    rootdir = os.path.abspath(os.path.join(basedir, '..'))

    app = Flask(__name__,
                root_path=rootdir,
                instance_relative_config=True)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-dev')
    
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # This is the ONLY line that should set the SQLite path
        local_db_path = os.path.join(rootdir, 'it_asset_manager.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{local_db_path}"
    
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
    # Connect the Flask-WTF extension for CSRF protection
    csrf.init_app(app)


    # This function tells Flask-Login how to load a user from the database given the user ID that is stored in the session cookie.
    @login_manager.user_loader
    def load_user(user_id):
         return db.session.get(models.User, int(user_id))
    
    @app.cli.command("seed")
    def seed_command():
        """Seeds the database with initial data."""
        from seed import seed_database
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
    
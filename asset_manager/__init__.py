import os
import click
from flask import Flask, app, redirect, url_for, flash, request, render_template
from functools import wraps
from flask_login import current_user
from . import models
from .extensions import db, login_manager, migrate, csrf, talisman, limiter
from werkzeug.middleware.proxy_fix import ProxyFix

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
    
    if config_override: 
        app.config.update(config_override)
    else:
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

    # For production environments, we want to enforce secure cookies and HTTPS. For testing, we disable these features to allow the test client to function properly.
    if not app.config.get('TESTING'):
        # Production-Grade Security for Render
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
            REMEMBER_COOKIE_SECURE=True,
            REMEMBER_COOKIE_HTTPONLY=True,
            REMEMBER_COOKIE_SAMESITE="Lax"
        )
        # Trust Render's Load Balancer
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
        
        # Enable Talisman HTTPS/HSTS/CSP
        talisman.init_app(app, content_security_policy=None)
    else:
        # Testing Environment logic
        # Check if we specifically requested 'Security Mode' 
        is_security_test = config_override.get('SECURITY_TEST_MODE', False) if config_override else False
        
        if is_security_test:
            app.config.update(
                SESSION_COOKIE_SECURE=True,
                SESSION_COOKIE_HTTPONLY=True,
                WTF_CSRF_ENABLED=True
            )
            talisman.init_app(app, content_security_policy=None)
        else:
            # Standard functional tests (Admin, Assets, etc.)
            app.config.update(
                SESSION_COOKIE_SECURE=False,
                SESSION_COOKIE_HTTPONLY=False,
                WTF_CSRF_ENABLED=False
            )
            # Talisman is NOT initialised here for regular tests

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
    # Connect the Limiter to the app
    limiter.init_app(app)

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
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('errors/429.html'), 429

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    return app
    
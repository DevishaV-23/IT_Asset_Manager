import os
from flask import Flask, redirect, url_for, flash, request
from functools import wraps
from flask_login import current_user
from . import models
from .extensions import db, login_manager, migrate

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
    
def create_app(config_override=None):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(__name__,
                template_folder=os.path.join(base_dir, 'templates'), 
                static_folder=os.path.join(base_dir, 'static') 
                )
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///it_asset_manager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app, db)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
         return db.session.get(models.User, int(user_id))

    with app.app_context():
        from . import auth
        app.register_blueprint(auth.auth_bp)

        from . import assets
        app.register_blueprint(assets.assets_bp)

        from . import admin
        app.register_blueprint(admin.admin_bp)

        db.create_all()  # Create database tables if they don't exist

        @app.route('/')
        def index():
            """Redirects the root URL to the login page."""
            return redirect(url_for('auth.login'))

    return app
    
from flask import Flask, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user
from flask_migrate import Migrate
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='regular')  # 'admin' or 'regular'
    registration_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<User {self.username} ({self.name})>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_name = db.Column(db.String(150), nullable=False)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Float, nullable=True)
    vendor = db.Column(db.String(100), nullable=True)
    storage_location = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='In Use')  # 'In Use', 'In Repair', 'Retired'
    description = db.Column(db.Text, nullable=True)
    added_on = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_updated_on = db.Column(db.DateTime, nullable=False,
                                default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))
    category_id = db.Column(db.Integer, db.ForeignKey('asset_category.id'), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    creator = db.relationship('User', backref=db.backref('assets_created', lazy='dynamic'))

    def __repr__(self):
        return f'<Asset {self.asset_name}>'   
    

class AssetCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    assets = db.relationship('Asset', backref='category', lazy=True)

    def __repr__(self):
        return f'<AssetCategory {self.name}>'
    
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
    
def create_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(__name__,
                template_folder=os.path.join(base_dir, 'templates'), 
                static_folder=os.path.join(base_dir, 'static') 
                )
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asset_manager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app, db)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        from . import auth
        app.register_blueprint(auth.auth_bp)

        from . import assets
        app.register_blueprint(assets.assets_bp)

        from . import admin
        app.register_blueprint(admin.admin_bp)

        db.create_all()
        create_initial_data()

        return app
    
def create_initial_data():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(name='Administrator', username='admin', email='admin@example.com', role='admin')
            admin_user.set_password('ChangeMe123!')
            db.session.add(admin_user)
            print("Admin user created with username 'admin', name 'Administrator', and password 'ChangeMe123!'. Please change it.")
        default_categories = [
            ("Laptop", "Portable computers"), ("Desktop", "Stationary computer systems"),
            ("Monitor", "Display screens"), ("Printer", "Document printing devices"),
            ("Server", "Network servers"), ("Networking Gear", "Routers, switches, firewalls"),
            ("Software License", "Licenses for software applications"),
            ("Mobile Phone", "Company-issued mobile phones"), ("Tablet", "Company-issued tablet devices")
        ]
        if not AssetCategory.query.first():
            for name, desc in default_categories:
                if not AssetCategory.query.filter_by(name=name).first():
                    category = AssetCategory(name=name, description=desc)
                    db.session.add(category)
            print("Default asset categories created.")
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error during initial data creation: {e}")
from .extensions import db
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# The User class defines the 'user' table in the database.
# It inherits from db.Model to get SQLAlchemy functionality.
# It also inherits from UserMixin, which provides default implementations for the properties that Flask-Login expects user objects to have
# (e.g., is_authenticated, is_active, is_anonymous, get_id()).
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True) # Primary key
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='regular')  # 'admin' or 'regular'
    registration_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # Provides a developer-friendly string representation of the User object
    def __repr__(self):
        return f'<User {self.username} ({self.name})>'
    # Creates a secure password hash from a plain text password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    # Checks if a plain text password matches the stored hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# The Asset class defines the 'asset' table in the database
class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Priamry Key
    asset_name = db.Column(db.String(150), nullable=False)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Float, nullable=True)
    vendor = db.Column(db.String(100), nullable=True)
    storage_location = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='In Use')  # 'In Use', 'In Repair', 'Retired'
    description = db.Column(db.Text, nullable=True)
    # Timestamps
    added_on = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_updated_on = db.Column(db.DateTime, nullable=False,
                                default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))
    # Foreign key linking this asset to a category
    category_id = db.Column(db.Integer, db.ForeignKey('asset_category.id'), nullable=False)
    # Foreign key linking this asset to the user who created it
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # Create a relationship to the User model. This allows you to access `asset.creator` to get the full User object for the user who created the asset.
    creator = db.relationship('User', backref=db.backref('assets_created', lazy='dynamic'))

    def __repr__(self):
        return f'<Asset {self.asset_name}>'   
    
# The AssetCategory class defines the 'asset_category' table
class AssetCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Create a one-to-many relationship. This allows you to access `category.assets` to get a list of all Asset objects belonging to this category.
    # The `backref='category'` creates a `asset.category` attribute on the Asset model to easily get the category from an asset object.
    assets = db.relationship('Asset', backref='category', lazy=True)
    def __repr__(self):
        return f'<AssetCategory {self.name}>'
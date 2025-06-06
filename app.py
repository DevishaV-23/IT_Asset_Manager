from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash   
from datetime import datetime, date, timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asset_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    
def create_initial_data():
    with app.app_context():
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

if __name__ == '__main__':
    app.run(debug=True)
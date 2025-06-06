from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash   
from datetime import datetime, timezone
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asset_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  

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
    

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))     


@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now(timezone.utc).year}


# ---Routes---
@app.route('/')
def index():
    if current_user.is_authenticated:
         return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: # If already logged in, redirect to dashboard
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name= request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'regular') 
        # Validate input
        if not name or not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'danger')
        else:
            new_user = User(name=name, username=username, email=email, role=role)
            new_user.set_password(password)
            try:
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
                app.logger.error(f"Error during registration: {e}")
        return render_template('register.html', title="Register", request_form=request.form)
    return render_template('register.html', title="Register")

@app.route('/login', methods=['GET', 'POST'])   
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', title="Login")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/assets')
@login_required
def list_assets():
    page_title= "Assets Overview"
    page_subtitle = "You cna view and manage all your IT assets here"
    assets = Asset.query.options(joinedload(Asset.creator)).all()
    return render_template('assets_list.html', title="IT Assets", assets=assets, page_title=page_title, page_subtitle=page_subtitle)

@app.route('/assets/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    page_title= "Add an Asset"
    page_subtitle = "Add a new asset"
    categories = AssetCategory.query.all()
    if request.method == 'POST':
        asset_name = request.form['asset_name']
        asset_tag = request.form['asset_tag']
        serial_number = request.form['serial_number']
        try: 
            purchase_date_str = request.form.get('purchase_date')
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d') if purchase_date_str else None
        except ValueError:
            flash('Invalid purchase date format. Please use the date picker or YYYY-MM-DD format.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('add_asset'), request_form=request.form)
        
        purchase_cost_str = request.form.get('purchase_cost')
        purchase_cost = float(purchase_cost_str) if purchase_cost_str else None
        vendor = request.form.get('vendor')
        location = request.form.get('location')
        status = request.form['status']
        description = request.form.get('description')
        category_id = request.form.get('category')

        if not asset_name or not asset_tag or not status or not category_id:
            flash('Asset Name, Asset Tag, Status, and Category are required.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('add_asset'), request_form=request.form)
        
        elif Asset.query.filter_by(asset_tag=asset_tag).first():
            flash(f'Asset Tag {asset_tag} already exists.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('add_asset'), request_form=request.form)
        
        elif serial_number and Asset.query.filter_by(serial_number=serial_number).first():
            flash(f'Serial Number {serial_number} already exists.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('add_asset'), request_form=request.form)
        else:
            new_asset = Asset(
                asset_name=asset_name,
                asset_tag=asset_tag,
                serial_number=serial_number,
                purchase_date=purchase_date,
                purchase_cost=purchase_cost,
                vendor=vendor,
                storage_location=location,
                status=status,
                description=description,
                category_id=category_id,
                created_by_user_id=current_user.id
            )
            try:
                db.session.add(new_asset)
                db.session.commit()
                flash('Asset added successfully!', 'success')
                return redirect(url_for('list_assets'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
                app.logger.error(f"Error adding asset: {e}")
                return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('add_asset'), request_form=request.form)
    return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)

@app.route('/assets/edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    page_title= "Edit an Asset"
    page_subtitle = "Edit an exisiting asset"
    asset_to_edit = Asset.query.get_or_404(asset_id)
    categories = AssetCategory.query.all()
    if request.method =='POST':
        original_asset_tag = asset_to_edit.asset_tag
        new_asset_tag = request.form['asset_tag']
        if new_asset_tag != original_asset_tag and Asset.query.filter_by(asset_tag=new_asset_tag).first():
            flash(f'Asset Tag {new_asset_tag} already exists.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('edit_asset', asset_id=asset_id), request_form=request.form)
        
        original_serial_number = asset_to_edit.serial_number
        new_serial_number = request.form.get('serial_number')
        if new_serial_number and new_serial_number != original_serial_number and Asset.query.filter_by(serial_number=new_serial_number).first():
            flash(f'Serial Number {new_serial_number} already exists.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('edit_asset', asset_id=asset_id), request_form=request.form)  
        
        asset_to_edit.asset_name = request.form['asset_name']
        asset_to_edit.asset_tag = new_asset_tag
        asset_to_edit.serial_number = new_serial_number
        try:
            purchase_date_str = request.form.get('purchase_date')
            asset_to_edit.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        except ValueError:
            flash('Invalid purchase date. Please use the date picker or YYYY-MM-DD format.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('edit_asset', asset_id=asset_id), request_form=request.form)

        purchase_cost_str = request.form.get('purchase_cost')
        asset_to_edit.purchase_cost = float(purchase_cost_str) if purchase_cost_str else None
        asset_to_edit.vendor = request.form.get('vendor')
        asset_to_edit.location = request.form.get('location')
        asset_to_edit.status = request.form['status']
        asset_to_edit.description = request.form.get('description')
        asset_to_edit.category_id = request.form.get('category')
        try:
            db.session.commit()
            flash('Asset updated successfully!', 'success')
            return redirect(url_for('list_assets'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            app.logger.error(f"Error updating asset: {e}") 
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('edit_asset', asset_id=asset_id), request_form=request.form)
    return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('edit_asset', asset_id=asset_id), page_title=page_title, page_subtitle=page_subtitle)

@app.route('/assets/delete/<int:asset_id>', methods=['POST'])
@login_required
def delete_asset(asset_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete assets.', 'danger')
        return redirect(url_for('list_assets'))
    asset_to_delete = Asset.query.get_or_404(asset_id)
    try:
        db.session.delete(asset_to_delete)
        db.session.commit()
        flash('Asset deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
        app.logger.error(f"Error deleting asset: {e}")
    return redirect(url_for('list_assets'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        if current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

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
    create_initial_data()
    app.run(debug=True)
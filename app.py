from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract
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

@app.route('/dashboard')
@login_required
def dashboard():
    page_title= f"Welcome, { current_user.name if current_user.name else current_user.username }"
    page_subtitle = f"Your role is: { current_user.role }"
    total_assets = Asset.query.count()
    active_assets = Asset.query.filter_by(status='In Use').count()
    in_repair_assets = Asset.query.filter_by(status='In Repair').count()
    retired_assets = Asset.query.filter_by(status='Retired').count()
    
    now_utc = datetime.now(timezone.utc)
    current_month = now_utc.month
    current_year = now_utc.year
    new_assets_this_month = Asset.query.filter(
        extract('month', Asset.added_on) == current_month,
        extract('year', Asset.added_on) == current_year
    ).count()

    return render_template('dashboard.html', title="Dashboard", total_assets=total_assets,
                           active_assets=active_assets, in_repair_assets=in_repair_assets,
                           retired_assets=retired_assets, new_assets_this_month=new_assets_this_month, page_title=page_title, page_subtitle=page_subtitle
      )

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    page_title= "My Profile"
    page_subtitle = "Edit your profile information"
    user_to_edit = current_user # User can only edit their own profile
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_email = request.form.get('email')
        new_username = request.form.get('username')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        # Validate name
        if not new_name:
            flash('Name cannot be empty.', 'danger')
            return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form)
        
        user_to_edit.name = new_name

        # Validate email and check uniqueness if changed
        if new_email != user_to_edit.email:
            if not new_email:
                flash('Email cannot be empty.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form)
            existing_email_user = User.query.filter(User.email == new_email, User.id != user_to_edit.id).first()
            if existing_email_user:
                flash('Email address is already registered by another user.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form)
            user_to_edit.email = new_email

        if new_username != user_to_edit.username:
            if not new_username:
                flash('Username cannot be empty.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form)
            existing_username_user = User.query.filter(User.username == new_username, User.id != user_to_edit.id).first()
            if existing_username_user:
                flash('Username is already taken.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form)
            user_to_edit.username = new_username

        password_changed = False
        if new_password: # User wants to change password
            if not current_password:
                flash('Current password is required to change your password.', 'danger')
                return render_template('profile_edit_form.html', title="Edit Profile", page_title=page_title, user_to_edit=user_to_edit, request_form=request.form)
            if not user_to_edit.check_password(current_password):
                flash('Incorrect current password.', 'danger')
                return render_template('profile_edit_form.html', title="Edit Profile", page_title=page_title, user_to_edit=user_to_edit, request_form=request.form)
            if not new_password or not confirm_new_password:
                flash('New password and confirmation are required to change password.', 'danger')
                return render_template('profile_edit_form.html', title="Edit Profile", page_title=page_title, user_to_edit=user_to_edit, request_form=request.form)
            if new_password != confirm_new_password:
                flash('New passwords do not match.', 'danger')
                return render_template('profile_edit_form.html', title="Edit Profile", page_title=page_title, user_to_edit=user_to_edit, request_form=request.form)
            user_to_edit.set_password(new_password)
            password_changed = True
        
        try:
            db.session.commit()
            if password_changed:
                flash('Your profile and password have been updated successfully! Please log in again if your username changed.', 'success')
                # If username changed, logging out might be a good idea to force re-login with new username
                # For simplicity, we'll just flash a message here.
            else:
                flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('dashboard')) 
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            app.logger.error(f"Error updating profile for {user_to_edit.username}: {e}")
            return render_template('profile_edit_form.html', title="Edit Profile", page_title=page_title, user_to_edit=user_to_edit, request_form=request.form)
        
    return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, page_title=page_title, page_subtitle=page_subtitle)

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

@app.route('/categories')
@login_required
def list_categories():
    page_title= "Categories Overview"
    page_subtitle = "You can view and manage asset categories here"
    categories = AssetCategory.query.all()

    category_counts_query = db.session.query(
        AssetCategory.id,
        func.count(Asset.id).label('asset_count')
    ).outerjoin(Asset, AssetCategory.id == Asset.category_id)\
      .group_by(AssetCategory.id).all()
    
    category_counts = {cat_id: count for cat_id, count in category_counts_query}

    for category in categories:
        category.asset_count = category_counts.get(category.id, 0)

    return render_template('categories_list.html', title="Asset Categories", categories=categories, page_title=page_title, page_subtitle=page_subtitle)

@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    page_title= "Add a Category"
    page_subtitle = "Add a new asset category"
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description')
        if not name:
            flash('Category Name is required.', 'danger')
        elif AssetCategory.query.filter_by(name=name).first():
            flash(f'Category {name} already exists.', 'danger')
        else:
            new_category = AssetCategory(name=name, description=description)
            try:
                db.session.add(new_category)
                db.session.commit()
                flash('Category added successfully!', 'success')
                return redirect(url_for('list_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
                app.logger.error(f"Error adding category: {e}")
                return render_template('category_form.html', title='Add Category', form_action_url=url_for('add_category'), request_form=request.form)
    return render_template('category_form.html', title='Add Category', form_action_url=url_for('add_category'), page_title=page_title, page_subtitle=page_subtitle)

@app.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    page_title= "Edit a Category"
    page_subtitle = "Edit an existing asset category"
    category_to_edit = AssetCategory.query.get_or_404(category_id)
    if request.method == 'POST':
        new_name = request.form['name']
        description = request.form.get('description')
        if not new_name:
            flash('Category name is required.', 'danger')
            return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('edit_category', category_id=category_id), request_form=request.form)
        elif new_name != category_to_edit.name and AssetCategory.query.filter_by(name=new_name).first():
            flash(f'Category name "{new_name}" already exists.', 'danger')
            return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('edit_category', category_id=category_id), request_form=request.form)
        else:
            category_to_edit.name = new_name
            category_to_edit.description = description
            try:
                db.session.commit()
                flash('Category updated successfully!', 'success')
                return redirect(url_for('list_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating category: {str(e)}', 'danger')
                app.logger.error(f"Error updating category: {e}")
                return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('edit_category', category_id=category_id), request_form=request.form)
    return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('edit_category', category_id=category_id), page_title=page_title, page_subtitle=page_subtitle)

    
@app.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category_to_delete = AssetCategory.query.get_or_404(category_id)
    if Asset.query.filter_by(category_id=category_id).first():
        flash('Cannot delete category, it is currently associated with one or more assets', 'danger')
        return redirect(url_for('list_categories'))
    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
        app.logger.error(f"Error deleting category: {e}")
    return redirect(url_for('list_categories'))

@app.route('/users')
@login_required
@admin_required
def list_users():
    page_title= "User Management"
    page_subtitle = "You can view and manage users here"
    users = User.query.order_by(User.name).all()
    return render_template('user_list.html', title="User Management", users=users, page_title=page_title, page_subtitle=page_subtitle)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    page_title = "Add New User"
    page_subtitle = "Create a new user account"
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        error = False
        if not all([name, username, email, role, password, confirm_password]):
            flash('All fields are required.', 'danger')
            error = True
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            error = True
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            error = True
        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'danger')
            error = True
        
        if error:
            return render_template('user_form.html', title="Add User", page_title=page_title, form_mode='add', request_form=request.form)

        new_user = User(name=name, username=username, email=email, role=role)
        new_user.set_password(password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f'User {username} created successfully!', 'success')
            return redirect(url_for('list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            app.logger.error(f"Error creating user: {e}")
            return render_template('user_form.html', title="Add User", page_title=page_title, form_mode='add', request_form=request.form)

    return render_template('user_form.html', title="Add User", page_title=page_title, form_mode='add', page_subtitle=page_subtitle)


@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    page_title= "Edit a User"
    page_subtitle = "Edit user information"
    user_to_edit = User.query.get_or_404(user_id)
    if request.method == 'POST':
        if user_to_edit.id == current_user.id and user_to_edit.role == 'admin' and \
           User.query.filter_by(role='admin').count() == 1 and \
           request.form.get('role') == 'regular':
            flash('Cannot demote the last administrator.', 'danger')
            return redirect(url_for('edit_user', user_id=user_id))

        original_username = user_to_edit.username
        new_username = request.form.get('username')
        original_email = user_to_edit.email
        new_email = request.form.get('email')

        user_to_edit.name = request.form.get('name')
        
        if new_username != original_username:
            if not new_username: # Check if new_username is not empty
                flash('Username cannot be empty.', 'danger')
                return render_template('admin/user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, request_form=request.form)
            if User.query.filter(User.username == new_username, User.id != user_id).first(): # Check uniqueness excluding self
                flash('Username already taken.', 'danger')
                return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, request_form=request.form)
            user_to_edit.username = new_username
        
        if new_email != original_email:
            if not new_email: # Check if new_email is not empty
                flash('Email cannot be empty.', 'danger')
                return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, request_form=request.form)
            if User.query.filter(User.email == new_email, User.id != user_id).first(): 
                flash('Email already registered by another user.', 'danger')
                return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, request_form=request.form)
            user_to_edit.email = new_email
            
        user_to_edit.role = request.form.get('role')

        try:
            db.session.commit()
            flash(f'User {user_to_edit.username} updated successfully!', 'success')
            return redirect(url_for('list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
            app.logger.error(f"Error updating user {user_to_edit.username}: {e}")
            return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, request_form=request.form)
    
    return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, page_subtitle=page_subtitle)


@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('list_users'))

    user_to_delete = User.query.get_or_404(user_id)
    
    # Prevent deletion of the last admin
    if user_to_delete.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last administrator.', 'danger')
        return redirect(url_for('list_users'))
        
    try:
        if Asset.query.filter_by(created_by_user_id=user_id).first():
            flash(f'Cannot delete user {user_to_delete.username} as they have assets associated. Reassign or delete assets first.', 'warning')
            return redirect(url_for('list_users'))

        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User {user_to_delete.username} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
        app.logger.error(f"Error deleting user {user_to_delete.username}: {e}")
        
    return redirect(url_for('list_users'))

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
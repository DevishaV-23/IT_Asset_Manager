from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from .extensions import db
from . import admin_required
from .models import Asset, AssetCategory

# This creates a Blueprint named 'assets'. All routes defined in this file will be prefixed with '/assets' and can be referenced with the 'assets.' endpoint.
assets_bp = Blueprint(
    'assets', __name__,
    url_prefix='/assets'
)

# Displays the main dashboard with summary statistics about assets
@assets_bp.route('/')
@login_required
def dashboard():
    # Set the title and and subtitle for the page header template
    page_title= f"Welcome, { current_user.name if current_user.name else current_user.username }"
    page_subtitle = f"Your role is: { current_user.role }"
    # Query for Dashboard Statistics
    total_assets = Asset.query.count()
    active_assets = Asset.query.filter_by(status='In Use').count()
    in_repair_assets = Asset.query.filter_by(status='In Repair').count()
    retired_assets = Asset.query.filter_by(status='Retired').count()
    # Get assets added in the current month and year
    now_utc = datetime.now(timezone.utc)
    current_month = now_utc.month
    current_year = now_utc.year
    new_assets_this_month = Asset.query.filter(
        extract('month', Asset.added_on) == current_month,
        extract('year', Asset.added_on) == current_year
    ).count()
    # Render the page template with all the queried data
    return render_template('dashboard.html', title="Dashboard", total_assets=total_assets,
                           active_assets=active_assets, in_repair_assets=in_repair_assets,
                           retired_assets=retired_assets, new_assets_this_month=new_assets_this_month, page_title=page_title, page_subtitle=page_subtitle
      )

# Displays a list of all assets in the system
@assets_bp.route('/list')
@login_required
def list_assets():
    page_title= "Assets Overview"
    page_subtitle = "View and Manage all your IT assets"
    # Load the 'creator' relationship to prevent extra database queries in the template, so asset and creator are loaded in one go
    assets = Asset.query.options(joinedload(Asset.creator)).all()
    return render_template('assets_list.html', title="IT Assets", assets=assets, page_title=page_title, page_subtitle=page_subtitle)

# Handles both displaying the form to add a new asset (GET) and processing the form submission (POST)
@assets_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    page_title= "Add an Asset"
    page_subtitle = "Add a new asset"
    categories = AssetCategory.query.all()
    if request.method == 'POST':
        # Form Data Retrieval
        asset_name = request.form['asset_name']
        asset_tag = request.form['asset_tag']
        serial_number = request.form['serial_number']

        # Validation Logic
        try: 
            purchase_date_str = request.form.get('purchase_date')
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d') if purchase_date_str else None
        except ValueError:
            flash('Invalid purchase date format. Please use the date picker or YYYY-MM-DD format.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
        purchase_cost_str = request.form.get('purchase_cost')
        purchase_cost = float(purchase_cost_str) if purchase_cost_str else None
        vendor = request.form.get('vendor')
        storage_location = request.form.get('storage_location')
        status = request.form['status']
        description = request.form.get('description')
        category_id = request.form.get('category')

        if not asset_name or not asset_tag or not status or not category_id:
            flash('Asset Name, Asset Tag, Status, and Category are required.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
        elif Asset.query.filter_by(asset_tag=asset_tag).first():
            flash(f'Asset Tag {asset_tag} already exists.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
        elif serial_number and Asset.query.filter_by(serial_number=serial_number).first():
            flash(f'Serial Number {serial_number} already exists.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)  
        # If all validation passes, create the new asset
        else:
            new_asset = Asset(
                asset_name=asset_name,
                asset_tag=asset_tag,
                serial_number=serial_number,
                purchase_date=purchase_date,
                purchase_cost=purchase_cost,
                vendor=vendor,
                storage_location=storage_location,
                status=status,
                description=description,
                category_id=category_id,
                created_by_user_id=current_user.id
            )
            try:
                db.session.add(new_asset)
                db.session.commit()
                flash('Asset added successfully!', 'success')
                return redirect(url_for('assets.list_assets'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding asset: {str(e)}', 'danger')
                return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
    return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)

# Handles displaying a form to edit an existing asset (GET) and processing the submission (POST)
@assets_bp.route('/edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    page_title= "Edit an Asset"
    page_subtitle = "Edit an exisiting asset"
    asset_to_edit = db.session.get(Asset, asset_id)
    if asset_to_edit is None:
        abort(404)
    categories = AssetCategory.query.all()
    if request.method =='POST':
        # Validation logic
        original_asset_tag = asset_to_edit.asset_tag
        new_asset_tag = request.form['asset_tag']
        if new_asset_tag != original_asset_tag and Asset.query.filter_by(asset_tag=new_asset_tag).first():
            flash(f'Asset Tag {new_asset_tag} already exists.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
        original_serial_number = asset_to_edit.serial_number
        new_serial_number = request.form.get('serial_number')
        if new_serial_number and new_serial_number != original_serial_number and Asset.query.filter_by(serial_number=new_serial_number).first():
            flash(f'Serial Number {new_serial_number} already exists.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)  
        # Update asset fields
        asset_to_edit.asset_name = request.form['asset_name']
        asset_to_edit.asset_tag = new_asset_tag
        asset_to_edit.serial_number = new_serial_number
        try:
            purchase_date_str = request.form.get('purchase_date')
            asset_to_edit.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        except ValueError:
            flash('Invalid purchase date. Please use the date picker or YYYY-MM-DD format.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)

        purchase_cost_str = request.form.get('purchase_cost')
        asset_to_edit.purchase_cost = float(purchase_cost_str) if purchase_cost_str else None
        asset_to_edit.vendor = request.form.get('vendor')
        asset_to_edit.storage_location = request.form.get('storage_location')
        asset_to_edit.status = request.form['status']
        asset_to_edit.description = request.form.get('description')
        asset_to_edit.category_id = request.form.get('category')
        try:
            # Commit the updates to the database, if validation passes
            db.session.commit()
            flash('Asset updated successfully!', 'success')
            return redirect(url_for('assets.list_assets'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
    # For a GET request, display the form pre-filled with the category's data
    return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), page_title=page_title, page_subtitle=page_subtitle)

# Handles the deletion of an asset. This is a POST-only route. Restricted to admin users only
@assets_bp.route('/delete/<int:asset_id>', methods=['POST'])
@login_required
def delete_asset(asset_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete assets.', 'danger')
        return redirect(url_for('assets.list_assets'))
    asset_to_delete = db.session.get(Asset, asset_id)
    if asset_to_delete is None:
        abort(404)
    try:
        # Delete the asset
        db.session.delete(asset_to_delete)
        db.session.commit()
        flash('Asset deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting asset: {str(e)}', 'danger')
    return redirect(url_for('assets.list_assets'))

## CATEGORY MANAGEMENT ##

# Displays a list of all asset categories and the count of assets in each
@assets_bp.route('/categories')
@login_required
def list_categories():
    page_title= "Categories Overview"
    page_subtitle = "View and manage asset categories"
    categories = AssetCategory.query.all()
    # Create a subquery to efficiently count assets per category
    category_counts_query = db.session.query(
        AssetCategory.id,
        func.count(Asset.id).label('asset_count')
    ).outerjoin(Asset, AssetCategory.id == Asset.category_id)\
      .group_by(AssetCategory.id).all()
    # Convert the list of tuples into a dictionary for easy lookup
    category_counts = {cat_id: count for cat_id, count in category_counts_query}
    # Attach the asset count to each category object before rendering
    for category in categories:
        category.asset_count = category_counts.get(category.id, 0)

    return render_template('categories_list.html', title="Asset Categories", categories=categories, page_title=page_title, page_subtitle=page_subtitle)

# Handles adding a new asset category. Restricted to admin users
@assets_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    page_title= "Add a Category"
    page_subtitle = "Add a new asset category"
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description')

        # Input Validation
        if not name:
            flash('Category Name is required.', 'danger')
        elif AssetCategory.query.filter_by(name=name).first():
            flash(f'Category {name} already exists.', 'danger')
        else:
            # If validation passes, create and save the new category
            new_category = AssetCategory(name=name, description=description)
            try:
                db.session.add(new_category)
                db.session.commit()
                flash('Category added successfully!', 'success')
                return redirect(url_for('assets.list_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
                return render_template('category_form.html', title='Add Category', form_action_url=url_for('assets.add_category'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
    return render_template('category_form.html', title='Add Category', form_action_url=url_for('assets.add_category'), page_title=page_title, page_subtitle=page_subtitle)

# Handles editing an existing asset category. Restricted to admin users.
@assets_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    page_title= "Edit a Category"
    page_subtitle = "Edit an existing asset category"
    # Fetch the category or return a 404 error if it doesn't exist
    category_to_edit = db.session.get(AssetCategory, category_id)
    if category_to_edit is None:
        abort(404)
    if request.method == 'POST':
        new_name = request.form['name']
        description = request.form.get('description')
        # Input Validation
        if not new_name:
            flash('Category name is required.', 'danger')
            return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        elif new_name != category_to_edit.name and AssetCategory.query.filter_by(name=new_name).first():
            flash(f'Category name "{new_name}" already exists.', 'danger')
            return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        else:
            # If validation passes, update the category object
            category_to_edit.name = new_name
            category_to_edit.description = description
            try:
                db.session.commit()
                flash('Category updated successfully!', 'success')
                return redirect(url_for('assets.list_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating category: {str(e)}', 'danger')
                return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
    # For a GET request, display the form pre-filled with the category's data
    return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), page_title=page_title, page_subtitle=page_subtitle)

   # 

# Handles deleting a category. Restricted to admin users.
@assets_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category_to_delete = db.session.get(AssetCategory, category_id)
    if category_to_delete is None:
        abort(404)
    # Business Logic Check - Prevent deletion of a category if it is currently assigned to any assets
    if Asset.query.filter_by(category_id=category_id).first():
        flash('Cannot delete category, it is currently associated with one or more assets', 'danger')
        return redirect(url_for('assets.list_categories'))
    try:
        # If the category is not in use, delete it
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
    return redirect(url_for('assets.list_categories'))

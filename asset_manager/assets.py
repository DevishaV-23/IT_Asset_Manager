from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from . import db, admin_required
from . import Asset, AssetCategory

assets_bp = Blueprint(
    'assets', __name__,
    url_prefix='/assets'
)

@assets_bp.route('/')
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

@assets_bp.route('/assets')
@login_required
def list_assets():
    page_title= "Assets Overview"
    page_subtitle = "You cna view and manage all your IT assets here"
    assets = Asset.query.options(joinedload(Asset.creator)).all()
    return render_template('assets_list.html', title="IT Assets", assets=assets, page_title=page_title, page_subtitle=page_subtitle)

@assets_bp.route('/assets/add', methods=['GET', 'POST'])
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
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form)
        
        purchase_cost_str = request.form.get('purchase_cost')
        purchase_cost = float(purchase_cost_str) if purchase_cost_str else None
        vendor = request.form.get('vendor')
        location = request.form.get('location')
        status = request.form['status']
        description = request.form.get('description')
        category_id = request.form.get('category')

        if not asset_name or not asset_tag or not status or not category_id:
            flash('Asset Name, Asset Tag, Status, and Category are required.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form)
        
        elif Asset.query.filter_by(asset_tag=asset_tag).first():
            flash(f'Asset Tag {asset_tag} already exists.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form)
        
        elif serial_number and Asset.query.filter_by(serial_number=serial_number).first():
            flash(f'Serial Number {serial_number} already exists.', 'danger')
            return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form)
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
                return redirect(url_for('assets.list_assets'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding asset: {str(e)}', 'danger')
                return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form)
    return render_template('asset_form.html', title='Add Asset', categories=categories, form_action_url=url_for('assets.add_asset'), request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)

@assets_bp.route('/assets/edit/<int:asset_id>', methods=['GET', 'POST'])
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
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form)
        
        original_serial_number = asset_to_edit.serial_number
        new_serial_number = request.form.get('serial_number')
        if new_serial_number and new_serial_number != original_serial_number and Asset.query.filter_by(serial_number=new_serial_number).first():
            flash(f'Serial Number {new_serial_number} already exists.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form)  
        
        asset_to_edit.asset_name = request.form['asset_name']
        asset_to_edit.asset_tag = new_asset_tag
        asset_to_edit.serial_number = new_serial_number
        try:
            purchase_date_str = request.form.get('purchase_date')
            asset_to_edit.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        except ValueError:
            flash('Invalid purchase date. Please use the date picker or YYYY-MM-DD format.', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form)

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
            return redirect(url_for('assets.list_assets'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), request_form=request.form)
    return render_template('asset_form.html', title='Edit Asset', asset=asset_to_edit, categories=categories, form_action_url=url_for('assets.edit_asset', asset_id=asset_id), page_title=page_title, page_subtitle=page_subtitle)

@assets_bp.route('/assets/delete/<int:asset_id>', methods=['POST'])
@login_required
def delete_asset(asset_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete assets.', 'danger')
        return redirect(url_for('assets.list_assets'))
    asset_to_delete = Asset.query.get_or_404(asset_id)
    try:
        db.session.delete(asset_to_delete)
        db.session.commit()
        flash('Asset deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting asset: {str(e)}', 'danger')
    return redirect(url_for('assets.list_assets'))

@assets_bp.route('/categories')
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

@assets_bp.route('/categories/add', methods=['GET', 'POST'])
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
                return redirect(url_for('assets.list_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
                return render_template('category_form.html', title='Add Category', form_action_url=url_for('assets.add_category'), request_form=request.form)
    return render_template('category_form.html', title='Add Category', form_action_url=url_for('assets.add_category'), page_title=page_title, page_subtitle=page_subtitle)

@assets_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
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
            return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), request_form=request.form)
        elif new_name != category_to_edit.name and AssetCategory.query.filter_by(name=new_name).first():
            flash(f'Category name "{new_name}" already exists.', 'danger')
            return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), request_form=request.form)
        else:
            category_to_edit.name = new_name
            category_to_edit.description = description
            try:
                db.session.commit()
                flash('Category updated successfully!', 'success')
                return redirect(url_for('assets.list_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating category: {str(e)}', 'danger')
                return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), request_form=request.form)
    return render_template('category_form.html', title="Edit Category", category=category_to_edit, form_action_url=url_for('assets.edit_category', category_id=category_id), page_title=page_title, page_subtitle=page_subtitle)

    
@assets_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category_to_delete = AssetCategory.query.get_or_404(category_id)
    if Asset.query.filter_by(category_id=category_id).first():
        flash('Cannot delete category, it is currently associated with one or more assets', 'danger')
        return redirect(url_for('assets.list_categories'))
    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
    return redirect(url_for('assets.list_categories'))

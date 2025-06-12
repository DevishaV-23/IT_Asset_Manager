from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import db, admin_required
from . import User, Asset

admin_bp = Blueprint(
    'admin', __name__,
    url_prefix='/admin',
)

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    page_title= "User Management"
    page_subtitle = "View and manage users"
    users = User.query.order_by(User.id).all()
    return render_template('user_list.html', title="User Management", users=users, page_title=page_title, page_subtitle=page_subtitle)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
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
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            return render_template('user_form.html', title="Add User", page_title=page_title, form_mode='add', request_form=request.form)

    return render_template('user_form.html', title="Add User", page_title=page_title, form_mode='add', page_subtitle=page_subtitle)


@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
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
            return redirect(url_for('admin.edit_user', user_id=user_id))

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
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
            return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, request_form=request.form)
    
    return render_template('user_form.html', title="Edit User", page_title=page_title, form_mode='edit', user_to_edit=user_to_edit, page_subtitle=page_subtitle)


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.list_users'))

    user_to_delete = User.query.get_or_404(user_id)
    
    # Prevent deletion of the last admin
    if user_to_delete.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last administrator.', 'danger')
        return redirect(url_for('admin.list_users'))
        
    try:
        if Asset.query.filter_by(created_by_user_id=user_id).first():
            flash(f'Cannot delete user {user_to_delete.username} as they have assets associated. Reassign or delete assets first.', 'warning')
            return redirect(url_for('admin.list_users'))

        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User {user_to_delete.username} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
        
    return redirect(url_for('admin.list_users'))
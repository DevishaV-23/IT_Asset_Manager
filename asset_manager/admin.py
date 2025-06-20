from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .extensions import db
from . import admin_required
from .models import User, Asset

# This creates a Blueprint named 'admin'. All routes defined in this file will be prefixed with '/admin' and can be referenced with the 'admin.' endpoint.
admin_bp = Blueprint(
    'admin', __name__,
    url_prefix='/admin',
)

# Route to query the databse for all users and render the user list template, passing user data, to be displayed
@admin_bp.route('/users')
@login_required # Ensures the user must be logged in to access this page
@admin_required # Ensures the logged-in user must have the 'admin' role
def list_users():
    # Set the title and and subtitle for the page header template 
    page_title= "User Management"
    page_subtitle = "View and manage users"
    users = User.query.order_by(User.id).all()
    # Render the page template with all the queried data
    return render_template('user_list.html', title="User Management", users=users, page_title=page_title, page_subtitle=page_subtitle)

# Handles both displaying the form to add a new user (GET) and processing the form submission (POST).
@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    page_title = "Add New User"
    page_subtitle = "Create a new user account"
     # Handle the form submission when the method is POST.
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        # Input Validation
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
            return render_template('user_form.html', title="Add User", form_mode='add', request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        # If validation passes, create a new User object
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
            return render_template('user_form.html', title="Add User", form_mode='add', request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
    # For a GET request, just display the empty form
    return render_template('user_form.html', title="Add User", page_title=page_title, form_mode='add', page_subtitle=page_subtitle)

# Handles both displaying a form to edit an existing user's details (GET) and processing the edit submission (POST)
@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    page_title= "Edit a User"
    page_subtitle = "Edit user information"
    # Use the db.session.get() to fetch the user by their primary key
    user_to_edit = db.session.get(User, user_id)
    if user_to_edit is None:
        abort(404)
    if request.method == 'POST':
         # Business Logic: Prevent demoting the last admin
        if user_to_edit.id == current_user.id and user_to_edit.role == 'admin' and \
           User.query.filter_by(role='admin').count() == 1 and \
           request.form.get('role') == 'regular':
            flash('Cannot demote the last administrator.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        # Get original values to check if they were changed
        original_username = user_to_edit.username
        new_username = request.form.get('username')
        original_email = user_to_edit.email
        new_email = request.form.get('email')
        # Input Validation for Edit Form 
        user_to_edit.name = request.form.get('name')
        if not user_to_edit.name:
            flash('Name cannot be empty.', 'danger')
            return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
        if new_username != original_username:
            if not new_username: # Check if new_username is not empty
                flash('Username cannot be empty.', 'danger')
                return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            if User.query.filter(User.username == new_username, User.id != user_id).first(): # Check uniqueness excluding self
                flash('Username already taken.', 'danger')
                return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            user_to_edit.username = new_username
        
        if new_email != original_email:
            if not new_email: # Check if new_email is not empty
                flash('Email cannot be empty.', 'danger')
                return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            if User.query.filter(User.email == new_email, User.id != user_id).first(): 
                flash('Email already registered by another user.', 'danger')
                return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            user_to_edit.email = new_email
        # Update the user's role. Passwords are not changed from this form
        user_to_edit.role = request.form.get('role')
        # Commit the changes to the database
        try:
            db.session.commit()
            flash(f'User {user_to_edit.username} updated successfully!', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
            return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
    
    return render_template('user_form.html', title="Edit User", form_mode='edit', user_to_edit=user_to_edit, page_title=page_title, page_subtitle=page_subtitle)

# Handles the deletion of a user. This is a POST-only route to prevent accidental deletion via a simple link
@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    # Rule 1: Prevent an admin from deleting their own account
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.list_users'))
    # Get the user to delete, or return a 404 if they don't exist
    user_to_delete = db.session.get(User, user_id)
    if user_to_delete is None:
        abort(404)
    # Rule 2: Prevent deletion of the last remaining administrator
    if user_to_delete.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last administrator.', 'danger')
        return redirect(url_for('admin.list_users'))
    # Rule 3: Prevent deletion of users who have associated assets
    try:
        if Asset.query.filter_by(created_by_user_id=user_id).first():
            flash(f'Cannot delete user {user_to_delete.username} as they have assets associated. Reassign or delete assets first.', 'warning')
            return redirect(url_for('admin.list_users'))
        # If all checks pass, delete the user and commit
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User {user_to_delete.username} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
        
    return redirect(url_for('admin.list_users'))
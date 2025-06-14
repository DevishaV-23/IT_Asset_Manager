from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash
from . import db
from . import User
import os

auth_bp = Blueprint(
    'auth', __name__,
    url_prefix='/auth'
    )

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: # If already logged in, redirect to dashboard
        return redirect(url_for("assets.dashboard"))

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
                return redirect(url_for("auth.login"))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
                print(f"Error during registration: {e}")
        return render_template('register.html', title="Register", request_form=request.form)
    return render_template('register.html', title="Register")

@auth_bp.route('/login', methods=['GET', 'POST'])   
def login():
    print("HERE", os.listdir(os.path.join(os.getcwd(), 'templates')))
    if current_user.is_authenticated:
        return redirect(url_for('assets.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('assets.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', title="Login")

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
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
            return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
        user_to_edit.name = new_name

        # Validate email and check uniqueness if changed
        if new_email != user_to_edit.email:
            if not new_email:
                flash('Email cannot be empty.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            existing_email_user = User.query.filter(User.email == new_email, User.id != user_to_edit.id).first()
            if existing_email_user:
                flash('Email address is already registered by another user.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            user_to_edit.email = new_email

        if new_username != user_to_edit.username:
            if not new_username:
                flash('Username cannot be empty.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            existing_username_user = User.query.filter(User.username == new_username, User.id != user_to_edit.id).first()
            if existing_username_user:
                flash('Username is already taken.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            user_to_edit.username = new_username

        password_changed = False
        if new_password: # User wants to change password
            if not current_password:
                flash('Current password is required to change your password.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            if not user_to_edit.check_password(current_password):
                flash('Incorrect current password.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            if not new_password or not confirm_new_password:
                flash('New password and confirmation are required to change password.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            if new_password != confirm_new_password:
                flash('New passwords do not match.', 'danger')
                return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
            user_to_edit.set_password(new_password)
            password_changed = True
        
        try:
            db.session.commit()
            if password_changed:
                flash('Your profile and password have been updated successfully! Please log in again if your username changed.', 'success')
            else:
                flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('assets.dashboard')) 
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, request_form=request.form, page_title=page_title, page_subtitle=page_subtitle)
        
    return render_template('profile_form.html', title="Edit Profile", user_to_edit=user_to_edit, page_title=page_title, page_subtitle=page_subtitle)

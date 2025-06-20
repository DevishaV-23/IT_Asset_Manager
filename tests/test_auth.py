from flask import session
from asset_manager.models import User
import pytest

# Tests a user can succcesful register
def test_user_can_register(client, app):
    """Test that a new user can successfully register."""

    # Ensure registration page loads
    assert client.get('/auth/register').status_code == 200
    response = client.post(
        '/auth/register', data={
            'name': 'New Register', 
            'username': 'newregister', 
            'email': 'newregister@example.com',
            'password': 'newpassword',
            'confirm_password': 'newpassword'
        },
        follow_redirects=True
    )

    # Check for success message on the login page
    assert b"Registration successful! Please log in." in response.data

    # Verify with the databse the the user was created
    with app.app_context():
        assert User.query.filter_by(username='newregister').first() is not None

# Decorator runs the test function once for each set of parameters
@pytest.mark.parametrize(('name', 'username', 'email', 'password', 'confirm_password', 'message'), (
    ('Test', 'testuser', 'a@b.com', 'pw', 'pw', b'Username already exists.'),
    ('Test', 'new', 'user@test.com', 'pw', 'pw', b'Email address already registered.'),
    ('Test', 'new', 'a@b.com', 'pw1', 'pw2', b'Passwords do not match.'),
    ('', 'new', 'a@b.com', 'pw', 'pw', b'All fields are required.'),
))

# Tests that the registration form validates input correctly
def test_registration_validates_input(client, name, username, email, password, confirm_password, message):
    """Test that the registration form validates incorrect input."""

    # Submit registration form with a set of invalid parameters
    response = client.post(
        '/auth/register',
        data={
            'name': name,
            'username': username,
            'email': email,
            'password': password,
            'confirm_password': confirm_password
        },
        follow_redirects=True
    )
    
    # Check that the expected validation message is in the response
    assert message in response.data

# Tests that a user can log in and then log out successfully
def test_user_can_login_and_logout(client, auth):
    """Test login with the testuser and subsequent logout."""

    # Login
    login_response = auth.login(username='testuser', password='password')
    assert b'Login successful!' in login_response.data

    # Access a protected page to confirm login worked
    profile_response = client.get('/auth/profile/edit')
    assert profile_response.status_code == 200
    assert b'Edit your profile information' in profile_response.data

    # Logout
    logout_response = auth.logout()
    assert logout_response.status_code == 200 
    assert b'You have been logged out.' in logout_response.data

    # Prove access is revoked by trying to access profile page
    profile_response_after_logout = client.get('/auth/profile/edit', follow_redirects=True)
    assert profile_response_after_logout.status_code == 200
    assert b'Login' in profile_response_after_logout.data
    assert b'Edit your profile information' not in profile_response_after_logout.data

# Tests that a user cannot log in with invalid credentials
def test_login_with_invalid_credentials(client):
    """Test that logging in with an incorrect password fails."""

    # Attempt to log in with an invalid password
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)

    # Check the user is not redirected and sees an error message
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Invalid username or password' in response.data

# Tests that the login page redirects to the dashboard if a user is already logged in
def test_auth_pages_redirect_when_logged_in(client, auth):
    """Test that login and register pages redirect if a user is already logged in."""

    # Login
    auth.login() 

    # Attempt to access the registration page
    register_response = client.get('/auth/register', follow_redirects=True)
    assert b'Your role is: regular' in register_response.data
    assert b'Register' not in register_response.data

    # Try to access the login page
    login_response = client.get('/auth/login', follow_redirects=True)
    assert b'Your role is: regular' in login_response.data
    assert b'Login' not in login_response.data

# Tests that a user can edit their profile successfully
def test_edit_profile_submission(client, auth, app):
    """Test that a logged-in user can successfully edit their profile."""

    # Log in as the standard test user
    auth.login(username='testuser', password='password')

    # Submit the edit form with an updated name and email
    response = client.post(
        '/auth/profile/edit',
        data={
            'name': 'Test User Updated',
            'username': 'testuser', # Username is not being changed here
            'email': 'user-updated@test.com',
            # Password fields are left blank because we are not changing the password
            'current_password': '',
            'new_password': '',
            'confirm_new_password': ''
        },
        follow_redirects=True
    )

    # Check for a successful response and redirection to the dashboard
    assert response.status_code == 200
    assert b'Your profile has been updated successfully!' in response.data
    assert b'Dashboard' in response.data

    # Verify the changes were saved correcty in the database
    with app.app_context():
        from asset_manager.models import User
        user = User.query.filter_by(username='testuser').first()
        assert user.name == 'Test User Updated'
        assert user.email == 'user-updated@test.com'

# Tests that a user cannot edit their profile to to have a username or email that's already taken
def test_edit_profile_validates_duplicates(client, auth, app):
    """Test that a user cannot edit their profile to have a username or email that is already taken."""

    # Create a third user to create the conflict
    with app.app_context():
        from asset_manager.models import User, db
        other_user = User(name='Other', username='otheruser', email='other@user.com')
        other_user.set_password('password')
        db.session.add(other_user)
        db.session.commit()

    # Log in as user
    auth.login(username='testuser', password='password')

    # Scenario 1: Try to take the existing 'otheruser' username
    response_username = client.post('/auth/profile/edit', data={ 'name': 'Test User', 'username': 'otheruser', 'email': 'user@test.com'}, follow_redirects=True)
    assert b'Username is already taken.' in response_username.data
    
    # Scenario 2: Try to take the existing 'otheruser' email
    response_email = client.post('/auth/profile/edit', data={ 'name': 'Test User', 'username': 'testuser', 'email': 'other@user.com'}, follow_redirects=True)
    assert b'Email address is already registered by another user.' in response_email.data

# Tests that a user can change their password
def test_edit_profile_password_change_success(client, auth, app):
    """Test that a user can successfully change their password."""
    # Log in 
    auth.login(username='testuser', password='password')

    # Submit the form to change the password
    response = client.post(
        '/auth/profile/edit',
        data={
            'name': 'Test User',
            'username': 'testuser',
            'email': 'user@test.com',
            'current_password': 'password',
            'new_password': 'a-new-secret-password',
            'confirm_new_password': 'a-new-secret-password'
        },
        follow_redirects=True
    )
    # Check that we land on the dashboard
    assert response.status_code == 200
    assert b'Your profile and password have been updated successfully!' in response.data

    # Logout
    auth.logout()

    # Verify the new password works for logging in
    success_response = auth.login(username='testuser', password='a-new-secret-password')
    assert b'Login successful!' in success_response.data

    # Verify the old password NO LONGER works
    auth.logout()
    fail_response = auth.login(username='testuser', password='password')
    assert b'Invalid username or password' in fail_response.data

# Tests that a user cannot provide invalid data for their password
def test_edit_profile_password_validation(client, auth):
    """Test validation rules when a user tries to change their password."""

    # Log in
    auth.login()
    
    # Scenario 1: New passwords do not match
    response_mismatch = client.post('/auth/profile/edit', data={'name': 'Test User', 'username': 'testuser', 'email': 'user@test.com', 'current_password': 'password', 'new_password': 'new', 'confirm_new_password': 'different'}, follow_redirects=True)
    assert b'New passwords do not match.' in response_mismatch.data

    # Scenario 2: Current password is required but not provided
    response_missing = client.post('/auth/profile/edit', data={'name': 'Test User', 'username': 'testuser', 'email': 'user@test.com', 'current_password': '', 'new_password': 'new', 'confirm_new_password': 'new'}, follow_redirects=True)
    assert b'Current password is required' in response_missing.data


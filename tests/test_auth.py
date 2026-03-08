from sqlalchemy import true
from asset_manager.models import User
import pytest
from flask import session
from flask import get_flashed_messages

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
            'password': 'Newpassword1!',
            'confirm_password': 'Newpassword1!'
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
    ('Test', 'testuser', 'a@b.com', 'B3st_Pr@ctice!', 'B3st_Pr@ctice!', b'Username already exists.'),
    ('Test', 'new', 'user@test.com', 'B3st_Pr@ctice!', 'B3st_Pr@ctice!', b'Email address already registered.'),
    ('Test', 'new', 'a@b.com', 'B3st_Pr@ctice!', 'DifferentPassword123!', b'Passwords do not match.'),
    ('', 'new', 'a@b.com', 'B3st_Pr@ctice!', 'B3st_Pr@ctice!', b'All fields are required.'),
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

# Tests that the registration form enforces password complexity requirements
def test_password_complexity_validation(client, app):
    """Test that registration rejects passwords missing security components."""
    
    # List of weak passwords to test against your consolidated logic
    weak_passwords = [
        'short1!',      # Too short (less than 8)
        'alllowercase1!', # Missing uppercase
        'ALLUPPERCASE1!', # Missing lowercase
        'NoNumbers!',     # Missing numbers
        'NoSpecialChar1'  # Missing special character
    ]

    for weak_pw in weak_passwords:
        with client:
            response = client.post('/auth/register', data={
                'name': 'Test User',
                'username': 'testuser_complex',
                'email': 'complex@test.com',
                'password': weak_pw,
                'confirm_password': weak_pw
            }, follow_redirects=True)

            # check that the user is still on registration page
            assert response.status_code == 200
            
            # Verify the complexity error message was flashed
            messages = get_flashed_messages()
            assert any('Password must be at least 8 characters' in msg for msg in messages)

# Tests that the registration form enforces password confirmation matching
def test_password_match_validation(client, app):
    """Test that mismatched passwords are rejected."""
    with client:
        client.post('/auth/register', data={
            'name': 'Test User',
            'username': 'mismatch_user',
            'email': 'mismatch@test.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'DifferentPassword123!'
        }, follow_redirects=True)

        
        messages = get_flashed_messages()
        assert any('Passwords do not match' in msg for msg in messages)

# Tests that a user can log in and then log out successfully
def test_user_can_login_and_logout(client, auth):
    """Test login with the testuser and subsequent logout."""

    # Login
    login_response = auth.login(username='testuser', password='password')
    assert login_response.status_code == 200
    assert b"Dashboard" in login_response.data

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
    with client:
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        # Check the user is not redirected and sees an error message
        assert response.status_code == 200
        assert b"Invalid credentials" in response.data

def test_login_rate_limit(client):
    with client:
        # Loop for the first 2 failed attempts
        for i in range(2):
            client.post('/auth/login', data={
                'username': 'wronguser',
                'password': 'wrongpassword'
            }, follow_redirects=True)
            
            # Check session counter directly instead of HTML
            assert session['login_attempts'] == (i + 1)

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
    auth.login(username='testuser', password='password')

    # Change password
    response = client.post('/auth/profile/edit', data={
        'name': 'Test User',
        'username': 'testuser',
        'email': 'user@test.com',
        'current_password': 'password',
        'new_password': 'a-new-secret-password',
        'confirm_new_password': 'a-new-secret-password'
    }, follow_redirects=True)
    
    # Check HTML for success message
    assert b"updated successfully" in response.data.lower()

    auth.logout()

    # Verify failure with old password
    with client:
        fail_response = client.post('/auth/login', data={
            'username': 'testuser', 
            'password': 'password' # The old password
        }, follow_redirects=True)
    
    # Check HTML for error message
    assert b"Invalid" in fail_response.data

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


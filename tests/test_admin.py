from asset_manager.extensions import db
import pytest

# Tests that a regular user is redirected from admin pages
def test_admin_page_is_protected(client, auth):
    """A regular user should be redirected from admin pages."""
    # Log in as a regular user
    auth.login(username='testuser', password='password')

    # Try to access the admin page
    response = client.get('/admin/users', follow_redirects=True)

    # Check that access is denies and admin content is not shown
    assert b'You do not have permission' in response.data
    assert b'User Management' not in response.data

# Tests that an admin can view the user list
def test_admin_can_view_user_list(client, auth):
    """An admin user should be able to see the user list."""
    # Log in as an admin user
    auth.login(username='testadmin', password='password')

    # Access the user management page
    response = client.get('/admin/users')

    # Check for a successful response and correct content
    assert response.status_code == 200
    assert b'User Management' in response.data
    assert b'testadmin' in response.data
    assert b'testuser' in response.data

# Tests that an admin can add a new user
def test_admin_can_add_user(client, auth, app):
    """Test that an admin can add a new user."""
    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Ensure the 'add user' page loads correctly
    get_response = client.get('/admin/users/add')
    assert get_response.status_code == 200
    assert b'Add' in get_response.data 

    # Submit the form to create a new user
    post_response = client.post(
        '/admin/users/add',
        data={
            'name': 'Added By Admin',
            'username': 'addedbyadmin',
            'email': 'added@by.admin',
            'role': 'regular',
            'password': 'password',
            'confirm_password': 'password'
        },
        follow_redirects=True
    )

    # Check the response to confirm success
    assert post_response.status_code == 200
    assert b'successfully' in post_response.data 
    assert b'addedbyadmin' in post_response.data 

    # 5. Verify the user was created correctly in the database
    with app.app_context():
        from asset_manager.models import User
        new_user = User.query.filter_by(username='addedbyadmin').first()
        assert new_user is not None
        assert new_user.role == 'regular'

# Tests that a regular user cannot access the 'add user' page
def test_regular_user_cannot_access_add_user_page(client, auth):
    """Test that a regular user is blocked from the 'add user' page."""

    # Log in as a regular user
    auth.login(username='testuser', password='password')

    # Try to access the 'add user' page
    response = client.get('/admin/users/add', follow_redirects=True)

    # Check for the permission error
    assert response.status_code == 200
    assert b'You do not have permission' in response.data
    assert b'Add' not in response.data

# This decorator runs the test function for each set of parameters
@pytest.mark.parametrize(('username', 'email', 'password', 'confirm_password', 'message'), (
    ('testuser', 'new@example.com', 'pw', 'pw', b'Username already exists.'),
    ('newuser', 'admin@test.com', 'pw', 'pw', b'Email address already registered.'),
    ('newuser', 'new@example.com', 'pw1', 'pw2', b'Passwords do not match.'),
))

# Tests the validation rules when an admin adds a user.
def test_add_user_validation(client, auth, username, email, password, confirm_password, message):
    """Tests the validation rules when an admin adds a user."""
    # Log in as an admin to access the form
    auth.login(username='testadmin', password='password')

    # Submit the form with a set of invalid parameters
    response = client.post(
        '/admin/users/add',
        data={
            'name': 'Test Name',
            'username': username,
            'email': email,
            'role': 'regular',
            'password': password,
            'confirm_password': confirm_password
        },
        follow_redirects=True
    )

    # Check that the expected validation message is in the response
    assert message in response.data

# Tests that an admin can edit another user's details
def test_admin_can_edit_user(client, auth, app):
    """Test that an admin can edit another user's details."""

    # Get the ID of the user we intend to edit
    with app.app_context():
        from asset_manager.models import User
        user_to_edit = User.query.filter_by(username='testuser').first()
        user_id = user_to_edit.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Post new data to the edit user form
    response = client.post(
        f'/admin/users/edit/{user_id}',
        data={
            'name': 'Test User Edited',
            'username': 'testuser', # Not changing username
            'email': 'testuser.edited@example.com',
            'role': 'admin' # Promote the user to admin
        },
        follow_redirects=True
    )

    # Check the response from the user list page
    assert response.status_code == 200
    assert b'successfully' in response.data
    assert b'Test User Edited' in response.data

    # Verify the changes were saved to the database
    with app.app_context():
        from asset_manager.models import User
        edited_user = db.session.get(User, user_id)
        assert edited_user.name == 'Test User Edited'
        assert edited_user.email == 'testuser.edited@example.com'
        assert edited_user.role == 'admin'

# Tests that a regular user cannot access the edit user page of another user
def test_regular_user_cannot_access_edit_user_page(client, auth, app):
    """Test a regular user is blocked from editing another user."""

    # Get the ID of a user to target
    with app.app_context():
        from asset_manager.models import User
        target_user = User.query.filter_by(username='testadmin').first()
        target_user_id = target_user.id
        
    # Log in as a regular user
    auth.login(username='testuser', password='password')

    # Attempt to access the admin URL. The @admin decorator should block this
    response = client.get(f'/admin/users/edit/{target_user_id}', follow_redirects=True)

    # Verify the user was redirected to the dashboard, not the admin page
    assert response.status_code == 200
    assert b'Your role is: regular' in response.data
    assert b'Edit user information' not in response.data

# Tests that an admin cannot demote the last admin to a regular user
def test_admin_cannot_demote_last_admin(client, auth, app):
    """Test that an admin cannot demote the last admin to a regular user."""

    # Create the specific scenario by deleting the non-admin user
    with app.app_context():
        from asset_manager.models import User, db
        user_to_delete = User.query.filter_by(username='testuser').first()
        db.session.delete(user_to_delete)
        db.session.commit()
        admin_user = User.query.filter_by(username='testadmin').first()
        admin_id = admin_user.id

    #Log in as the sole admin
    auth.login(username='testadmin', password='password')

    # Attempt to submit the edit form to demote themselves
    response = client.post(f'/admin/users/edit/{admin_id}', data={'name': 'Admin', 'username': 'testadmin', 'email': 'admin@test.com', 'role': 'regular'}, follow_redirects=True)
    
    #Check for the specific error message preventing the demotion
    assert b'Cannot demote the last administrator.' in response.data

# This test checks multiple validation rules for the edit user form
@pytest.mark.parametrize(('key', 'value', 'message'), (
    ('name', '', b'Name cannot be empty.'),
    ('username', '', b'Username cannot be empty.'),
    ('email', '', b'Email cannot be empty.'),
))

# Tests that required fields cannot be made empty when editing a user.
def test_edit_user_empty_field_validation(client, auth, app, key, value, message):
    """Tests that required fields cannot be made empty when editing a user."""

    # Get the ID of the user to be edited
    with app.app_context():
        from asset_manager.models import User
        user_to_edit = User.query.filter_by(username='testuser').first()
        user_id = user_to_edit.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')
    
    # Prepare valid form data, which we will then modify
    form_data = {'name': 'Test User', 'username': 'testuser', 'email': 'user@test.com', 'role': 'regular'}

    # Overwrite one field with an empty value for this test case
    form_data[key] = value 

    # Submit the invalid form data
    response = client.post(f'/admin/users/edit/{user_id}', data=form_data, follow_redirects=True)

    # Verify the edit form is shown again, indicating validation failed
    assert response.status_code == 200
    assert b'Save Changes' in response.data

# Tests that an admin can delete another user
def test_admin_can_delete_user(client, auth, app):
    """Test that an admin can delete another user."""

    # Create a new, temporary user to be deleted
    with app.app_context():
        from asset_manager.models import User, db
        user_to_delete = User(name='Delete Me', username='deleteme', email='delete@me.com', role='regular')
        user_to_delete.set_password('password')
        db.session.add(user_to_delete)
        db.session.commit()
        user_id = user_to_delete.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Post to the delete endpoint for the new user
    response = client.post(f'/admin/users/delete/{user_id}', follow_redirects=True)

    # Check the user list page for a success message
    assert response.status_code == 200
    assert b'User deleteme deleted successfully.' in response.data

    # Verify with the database that the user is truly gone
    with app.app_context():
        deleted_user = db.session.get(User, user_id)
        assert deleted_user is None

# Tests that an admin cannot delete themselves if they are the last admin
def test_admin_cannot_delete_last_admin(client, auth, app):
    """Test that the last remaining admin user cannot be deleted."""

    # Delete the regular user to create the "last admin" state
    with app.app_context():
        from asset_manager.models import User, db
        user_to_delete = User.query.filter_by(username='testuser').first()
        db.session.delete(user_to_delete)
        db.session.commit()
        admin_user = User.query.filter_by(username='testadmin').first()
        admin_id = admin_user.id
    
    # Log in as that last admin
    auth.login(username='testadmin', password='password')

    # Attempt to delete themselves
    response = client.post(f'/admin/users/delete/{admin_id}', follow_redirects=True)

    # Check that the user was redirected back to the user list
    assert response.status_code == 200
    assert b'User Management' in response.data

    # Verify the admin user was NOT deleted from the database
    with app.app_context():
        admin_user_after = db.session.get(User, admin_id)
        assert admin_user_after is not None

# Tests that an admin cannot delete a user who has associated assets
def test_admin_cannot_delete_user_with_assets(client, auth, app):
    """Test that a user with associated assets cannot be deleted."""

    # Create an asset and link it to the 'testuser'
    with app.app_context():
        from asset_manager.models import Asset, AssetCategory, User, db
        user_with_assets = User.query.filter_by(username='testuser').first()
        category = AssetCategory.query.first()
        
        asset = Asset(
            asset_name='User-Owned Asset',
            asset_tag='UOA-001',
            category_id=category.id,
            created_by_user_id=user_with_assets.id, # Link asset to the user
            status='In Use'
        )
        db.session.add(asset)
        db.session.commit()
        user_id_with_assets = user_with_assets.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Attempt to delete the user who owns an assett
    response = client.post(f'/admin/users/delete/{user_id_with_assets}', follow_redirects=True)

    # Check for the specific warning message about associated assets
    assert response.status_code == 200
    assert b'Cannot delete user testuser as they have assets associated.' in response.data

    # Verify the user was NOT deleted from the database
    with app.app_context():
        user_after = db.session.get(User, user_id_with_assets)
        assert user_after is not None

# Tests that trying to delete a user that does not exist returns a 404
def test_delete_nonexistent_user_returns_404(client, auth):
    """Test that trying to delete a user that does not exist returns a 404."""

    # Log in as an admin.
    auth.login(username='testadmin', password='password')

    # Post to the delete endpoint with a user ID that doesn't exist
    response = client.post('/admin/users/delete/99999', follow_redirects=True)

    # Check for the 404 status code
    assert response.status_code == 404
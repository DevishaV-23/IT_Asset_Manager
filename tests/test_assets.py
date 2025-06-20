from asset_manager.models import AssetCategory, Asset,User
from asset_manager.extensions import db

# Tests that the dashboard is protected and requires login
def test_dashboard_is_protected(client):
    """Test that the dashboard requires login."""

    # Attempt to access the protected dashboard URL
    response = client.get('/assets/', follow_redirects=True)

    # Check for the flash message that prompts the user to log in
    assert b'Please log in to access this page.' in response.data

# Tests that when trying to acesss the edit page for a non-existent asset, a 404 is returned
def test_edit_nonexistent_asset_returns_404(client, auth):
    """Test that trying to edit an asset that does not exist returns a 404."""

    # Log in to get past the @login_required decorator
    auth.login()

    # Attempt to GET the edit page with a non-existent ID
    response_get = client.get('/assets/edit/99999')

    # The server should respond with a 404 error
    assert response_get.status_code == 404

    # Try to POST to the edit page for an asset ID that doesn't exist
    response_post = client.post('/assets/edit/99999', data={'name': 'ghost'})

    # The server should respond with a 404 error
    assert response_post.status_code == 404

# Tests that trying to delete an asset that does not exist return a 404 error
def test_delete_nonexistent_asset_returns_404(client, auth):
    """Test that trying to delete an asset that does not exist returns a 404."""

    # Log in as an admin to access the delete route
    auth.login(username='testadmin', password='password')

    # Attempt to POST to the delete endpoint with a non-existent ID
    response = client.post('/assets/delete/99999')

    # The server should respond with a 404 error
    assert response.status_code == 404

# Tests that a logged-in user can create an asset 
def test_asset_creation(client, auth, app):
    """Test that a logged-in user can create an asset."""

    # Log in as a standard user
    auth.login()
    assert client.get('/assets/add').status_code == 200

    # Get a valid category ID to associate the asset with
    with app.app_context():
        # Get a category to associate the asset with
        category = AssetCategory.query.filter_by(name="Test Laptops").first()
        assert category is not None, "Test setup error: 'Test Laptops' category not found in the database."

        # Submit the form with valid data to create a new asset
        response = client.post('/assets/add', data={
            'asset_name': 'My New Test Laptop',
            'asset_tag': 'PYTEST-001',
            'serial_number': 'PYTEST-SN-001',  
            'category': category.id,          
            'status': 'In Use',
            'storage_location': 'Test Lab',
            'purchase_date': '',
            'purchase_cost': '',
            'vendor': '',
            'description': ''
        }, follow_redirects=True)

    # Check for a successful response and that the new asset is on the page
    assert response.status_code == 200
    assert b'Asset added successfully!' in response.data
    assert b'My New Test Laptop' in response.data

# Tests that creating an asset with a duplicate tag or serial number fails
def test_add_asset_duplicate_validation(client, auth, app):
    """Test that creating an asset with a duplicate tag or serial fails."""
    category_id = None # <-- Create a variable to hold the ID

    # Create a baseline asset to create a data conflict
    with app.app_context():
        from asset_manager.models import Asset, AssetCategory, User, db
        category = AssetCategory.query.first()
        user = User.query.filter_by(username='testuser').first()
        category_id = category.id
        existing_asset = Asset(asset_name='Existing Asset', asset_tag='EXISTING-TAG', serial_number='EXISTING-SN', category_id=category.id, status='In Use', created_by_user_id=user.id)
        db.session.add(existing_asset)
        db.session.commit()
    
    # Log in
    auth.login()

    # Scenario 1 - Duplicate Asset Tag
    response_tag = client.post('/assets/add', data={
        'asset_name': 'New Asset', 'asset_tag': 'EXISTING-TAG', 'serial_number': 'NEW-SN', 'category': category_id, 'status': 'In Use', 'storage_location': ''
    }, follow_redirects=True)
    
    assert b'Asset Tag EXISTING-TAG already exists.' in response_tag.data

    # Scenario 2 - Duplicate Serial Number
    response_sn = client.post('/assets/add', data={
        'asset_name': 'New Asset 2', 'asset_tag': 'NEW-TAG', 'serial_number': 'EXISTING-SN', 'category': category_id, 'status': 'In Use', 'storage_location': ''
    }, follow_redirects=True)
    
    assert b'Serial Number EXISTING-SN already exists.' in response_sn.data

# Tests that a logged-in user can edit an asset
def test_edit_asset_submission(client, auth, app):
    """Test that a logged-in user can successfully edit an asset."""

    # Log in as a standard user
    auth.login() 
    asset_id = None
    category_id = None

    # Create a new asset within the test to ensure a clean state
    with app.app_context():
        category = AssetCategory.query.filter_by(name="Test Laptops").first()
        user = User.query.filter_by(username='testuser').first()
        category_id = category.id
        asset_to_edit = Asset(
            asset_name='Editable Laptop',
            asset_tag='EDIT-001',
            category_id=category_id,
            status='In Use',
            created_by_user_id=user.id
        )
        db.session.add(asset_to_edit)
        db.session.commit()
        asset_id = asset_to_edit.id

    # Submit the edit form with new data.
    response = client.post(
        f'/assets/edit/{asset_id}',
        data={
            'asset_name': 'Laptop Was Edited',
            'asset_tag': 'EDIT-002',
            'serial_number': 'NEW-SN-123',
            'category': category_id,
            'status': 'In Storage',
            'storage_location': 'Main Storeroom',
            'purchase_date': '',
            'purchase_cost': '',
            'vendor': '',
            'description': 'This asset has been updated by a test.'
        },
        follow_redirects=True
    )

    # Check for a success message and updated content on the asset list page
    assert response.status_code == 200
    assert b'Asset updated successfully!' in response.data
    assert b'Laptop Was Edited' in response.data

    # Verify the changes were saved correctly in the database
    with app.app_context():
        edited_asset = db.session.get(Asset, asset_id)
        assert edited_asset.asset_name == 'Laptop Was Edited'
        assert edited_asset.asset_tag == 'EDIT-002'
        assert edited_asset.status == 'In Storage'

# Tests that an admin can delete an asset
def test_admin_can_delete_asset(client, auth, app):
    """Test that an admin user can successfully delete an asset."""

    # Create a temporary asset to delete
    with app.app_context():
        from asset_manager.models import AssetCategory, User, Asset, db
        category = AssetCategory.query.first()
        user = User.query.filter_by(username='testadmin').first()
        asset_to_delete = Asset(asset_name='Asset to be Deleted', asset_tag='DELETE-ME', category_id=category.id, status='Retired', created_by_user_id=user.id)
        db.session.add(asset_to_delete)
        db.session.commit()
        asset_id = asset_to_delete.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')
    
    # Send the POST request to the delete endpoint
    response = client.post(f'/assets/delete/{asset_id}', follow_redirects=True)

    # Check for the success message
    assert response.status_code == 200
    assert b'Asset deleted successfully!' in response.data

    # Verify with the database that the asset is truly gone
    with app.app_context():
        deleted_asset = db.session.get(Asset, asset_id)
        assert deleted_asset is None

# Tests that a regular user cannot delete an asset
def test_regular_user_cannot_delete_asset(client, auth, app):
    """Test that a regular user is blocked from deleting an asset."""

    # Create an asset to target
    with app.app_context():
        from asset_manager.models import AssetCategory, User, Asset, db
        category = AssetCategory.query.first()
        user = User.query.filter_by(username='testuser').first()
        asset_to_protect = Asset(asset_name='Protected Asset', asset_tag='PROTECT-ME', category_id=category.id, status='In Use', created_by_user_id=user.id)
        db.session.add(asset_to_protect)
        db.session.commit()
        asset_id = asset_to_protect.id

    # Log in as a regular user
    auth.login(username='testuser', password='password')
    
    # Attempt to post to the delete endpoint
    response = client.post(f'/assets/delete/{asset_id}', follow_redirects=True)

    # Check that the permission error message is shown
    assert response.status_code == 200
    assert b'You do not have permission to delete assets.' in response.data

    # Verify the asset was NOT deleted from the database
    with app.app_context():
        protected_asset = db.session.get(Asset, asset_id)
        assert protected_asset is not None


##CATEGORY TESTS

# Tests that an admin can add a new cateogry
def test_admin_can_add_category(client, auth, app):
    """Test that an admin user can successfully add a new category."""

    # Log in as the admin user
    auth.login(username='testadmin', password='password')

    # Check user is directed to the add category page
    get_response = client.get('/assets/categories/add')
    assert get_response.status_code == 200
    assert b'Add a new asset category' in get_response.data

    # Submit the form to create a new category
    post_response = client.post(
        '/assets/categories/add',
        data={'name': 'New Test Category', 'description': 'A category created by a test.'},
        follow_redirects=True
    )

    # Check for a successful response and the new category on the list page
    assert post_response.status_code == 200
    assert b'Category added successfully!' in post_response.data
    assert b'New Test Category' in post_response.data

    # Verify the category was created in the database
    with app.app_context():
        from asset_manager.models import AssetCategory
        category = AssetCategory.query.filter_by(name='New Test Category').first()
        assert category is not None
        assert category.description == 'A category created by a test.'

# Tests that validation works when adding a new category
def test_add_category_validation(client, auth):
    """Test validation when adding a new category."""

    # Log in as an admin
    auth.login(username='testadmin', password='password')
    
    # Scenario 1: Empty name
    response_empty = client.post('/assets/categories/add', data={'name': '', 'description': ''}, follow_redirects=True)
    assert b'Category Name is required.' in response_empty.data

    # Scenario 2: Duplicate name (using the one from conftest)
    response_dupe = client.post('/assets/categories/add', data={'name': 'Test Laptops', 'description': ''}, follow_redirects=True)
    assert b'Category Test Laptops already exists.' in response_dupe.data

#Tests that a regular user cannot add a new category
def test_regular_user_cannot_add_category(client, auth):
    """Test that a regular user is blocked from adding a category."""
    # 1. Log in as a regular user
    auth.login(username='testuser', password='password')

    # 2. Try to access the 'add category' page
    get_response = client.get('/assets/categories/add', follow_redirects=True)

    # 3. Check that the user is redirected and sees a permission error
    assert get_response.status_code == 200
    assert b'You do not have permission to access this page.' in get_response.data
    assert b'Add a new asset category' not in get_response.data

    # 4. Try to post data directly to the endpoint
    post_response = client.post(
        '/assets/categories/add',
        data={'name': 'Unauthorized Category', 'description': ''},
        follow_redirects=True
    )
    # 5. Verify this is also blocked
    assert b'You do not have permission to access this page.' in post_response.data

# Tests that an admin can edit a category
def test_admin_can_edit_category(client, auth, app):
    """Test that an admin can successfully edit a category."""

    # Create a category to be edited for this test
    with app.app_context():
        from asset_manager.models import AssetCategory, db
        category_to_edit = AssetCategory(name='Original Category Name', description='Original Desc')
        db.session.add(category_to_edit)
        db.session.commit()
        category_id = category_to_edit.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Test that the edit page loads correctly
    get_response = client.get(f'/assets/categories/edit/{category_id}')
    assert get_response.status_code == 200
    assert b'Original Category Name' in get_response.data

    # Submit the edit form with new data
    post_response = client.post(
        f'/assets/categories/edit/{category_id}',
        data={'name': 'Edited Category Name', 'description': 'Updated Desc'},
        follow_redirects=True
    )

    # Check for a success message and that the new name is on the page
    assert post_response.status_code == 200
    assert b'Category updated successfully!' in post_response.data
    assert b'Edited Category Name' in post_response.data
    assert b'Original Category Name' not in post_response.data 

    # Verify the changes were saved correctly in the database
    with app.app_context():
        edited_category = db.session.get(AssetCategory, category_id)
        assert edited_category.name == 'Edited Category Name'
        assert edited_category.description == 'Updated Desc'

# Tests that validation works when editing a category
def test_edit_category_duplicate_name_validation(client, auth, app):
    """Test validation when editing a category to have a duplicate name."""

    # Create two categories to create a naming conflict
    with app.app_context():
        from asset_manager.models import AssetCategory, db
        # Create two categories to test with
        cat1 = AssetCategory(name='Category One')
        cat2 = AssetCategory(name='Category Two')
        db.session.add_all([cat1, cat2])
        db.session.commit()
        cat2_id = cat2.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')
    
    # Attempt to edit 'Category Two' to have the name 'Category One'
    response = client.post(f'/assets/categories/edit/{cat2_id}', data={'name': 'Category One', 'description': ''}, follow_redirects=True)
    
    # Verify that the edit form is re-displayed, indicating validation failed
    assert response.status_code == 200
    assert b'Edit a Category' in response.data

# Tests that a regular user cannot edit a category
def test_regular_user_cannot_edit_category(client, auth, app):
    """Test that a regular user is blocked from editing a category."""

    # Create a category to get a valid ID
    with app.app_context():
        from asset_manager.models import AssetCategory, db
        category_to_edit = AssetCategory(name='Protected Category')
        db.session.add(category_to_edit)
        db.session.commit()
        category_id = category_to_edit.id
    
    # Log in as a regular user
    auth.login(username='testuser', password='password')

    # Check that both GET and POST requests are blocked by the decorator
    get_response = client.get(f'/assets/categories/edit/{category_id}', follow_redirects=True)
    assert b'You do not have permission to access this page.' in get_response.data

    post_response = client.post(f'/assets/categories/edit/{category_id}', follow_redirects=True)
    assert b'You do not have permission to access this page.' in post_response.data

# Tests that an admin can delete a category that is not in use
def test_admin_can_delete_unused_category(client, auth, app):
    """Test admin can delete a category that is not linked to any assets."""

    # Create a new, unused category
    with app.app_context():
        from asset_manager.models import AssetCategory, db
        category_to_delete = AssetCategory(name='Unused Category')
        db.session.add(category_to_delete)
        db.session.commit()
        category_id = category_to_delete.id
    
    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Post to the delete endpoint
    response = client.post(f'/assets/categories/delete/{category_id}', follow_redirects=True)

    # Check for the success message and that the category is gone from the page
    assert response.status_code == 200
    assert b'Category deleted successfully!' in response.data
    assert b'Unused Category' not in response.data

    # Verify it was deleted from the database
    with app.app_context():
        deleted_category = db.session.get(AssetCategory, category_id)
        assert deleted_category is None

# Tests that an admin cannot delete a category that is in use
def test_admin_cannot_delete_used_category(client, auth, app):
    """Test admin is blocked from deleting a category that is in use."""
    
    # Create an asset and assign it to a category to create the condition
    with app.app_context():
        from asset_manager.models import Asset, AssetCategory, User, db
        # Find the category and a user to assign the asset to
        category_in_use = AssetCategory.query.filter_by(name="Test Laptops").first()
        user = User.query.filter_by(username='testadmin').first()
        # Create an asset linked to this category
        asset = Asset(asset_name='Laptop In Use', asset_tag='IN-USE-01', category_id=category_in_use.id, created_by_user_id=user.id, status='In Use')
        db.session.add(asset)
        db.session.commit()
        category_id = category_in_use.id

    # Log in as an admin
    auth.login(username='testadmin', password='password')

    # Attempt to delete the category that is now in use
    response = client.post(f'/assets/categories/delete/{category_id}', follow_redirects=True)

    # Check for the specific error message
    assert response.status_code == 200
    assert b'Cannot delete category, it is currently associated with one or more assets' in response.data

    # Verify the category was NOT deleted from the database
    with app.app_context():
        category = db.session.get(AssetCategory, category_id)
        assert category is not None

# Tests that a regular user cannot delete a category
def test_regular_user_cannot_delete_category(client, auth, app):
    """Test a regular user is blocked from deleting any category."""

    # Get a valid category ID to target
    with app.app_context():
        from asset_manager.models import AssetCategory
        category = AssetCategory.query.filter_by(name="Test Laptops").first()
        category_id = category.id

    # Log in as a regular user
    auth.login(username='testuser', password='password')

    # Attempt to post to the delete endpoint
    response = client.post(f'/assets/categories/delete/{category_id}', follow_redirects=True)

    # Check for the permission denied error
    assert b'You do not have permission to access this page.' in response.data



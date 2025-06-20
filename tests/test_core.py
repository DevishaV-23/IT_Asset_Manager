from asset_manager.models import User
from asset_manager import create_app

# Tests that the app factory creates an app with the correct configuration
def test_config():
    """Test the app factory creates app with correct config."""
    assert not create_app().testing
    assert create_app({'TESTING': True}).testing

# Tests that a logged-out user cannot access any pages
def test_index_redirects_to_login(client):
    """Test the main URL redirects to the login page when logged out."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data

# Tests that a password is securely hashed
def test_user_password_hashing():
    """Test that password hashing and checking works correctly."""
    user = User(username='test_pass', name='Test Pass', email='pass@test.com')
    user.set_password('cat_and_dog')
    assert user.password_hash != 'cat_and_dog'
    assert user.check_password('cat_and_dog')
    assert not user.check_password('dog_and_cat')
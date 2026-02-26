import pytest
from asset_manager import create_app
from asset_manager.extensions import db,talisman
from asset_manager.models import User, AssetCategory

@pytest.fixture
# Create a new app instance for the entire test module
# Sets up the app with a test configuration and an in-memory SQLite database.
def app():
    """Create and configure a new app instance for the entire test module."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'PRESERVE_CONTEXT_ON_EXCEPTION': False,
        'SECRET_KEY': 'test-key',
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax'
    })

    app.config['TALISMAN_ENABLED'] = False


    if not hasattr(app, 'talisman'):
        talisman.init_app(app, content_security_policy=None)

    with app.app_context():
        db.create_all()
        # Seed the in-memory database with test data needed for the tests
        if not User.query.filter_by(username='testadmin').first():
            admin_user = User(name='Test Admin', username='testadmin', email='admin@test.com', role='admin')
            admin_user.set_password('password')
            regular_user = User(name='Test User', username='testuser', email='user@test.com', role='regular')
            regular_user.set_password('password')
            test_cat = AssetCategory(name="Test Laptops", description="Category for testing")
            db.session.add_all([admin_user, regular_user, test_cat])
            db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
# Create a test client for the app
# Provides a test client that can be used to make requests to the app.
def client(app):
    """A test client for the app."""
    return app.test_client()
#
class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username='testuser', password='password'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password},
            follow_redirects=True
        )
    
    def logout(self):
        return self._client.get('/auth/logout', follow_redirects=True)

@pytest.fixture()
def auth(client):
    """Provides an AuthActions object to easily log in/out."""
    return AuthActions(client)
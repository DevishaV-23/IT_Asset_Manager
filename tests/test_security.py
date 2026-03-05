
import pytest
import time

@pytest.mark.security_on
def test_security_headers(client):
    """Test that Talisman is injecting security headers in Production mode."""
    # Simulate a non-testing environment check if possible, 
    # or verify that the app is configured to use Talisman.
    response = client.get('/')
    # If Talisman is active, it sets these by default:
    assert 'X-Content-Type-Options' in response.headers
    assert 'X-Frame-Options' in response.headers



def test_rate_limit_reset_after_time(client, app):
    """Test that the limit resets if enough time passes"""
    with client:
        # 1. Manually set the session to be "locked"
        with client.session_transaction() as sess:
            sess['login_attempts'] = 3
            # Set the last attempt to 61 seconds ago
            sess['last_attempt_time'] = time.time() - 301

        # 2. Try to log in again
        client.get('/auth/login')
        
        # 3. Verify the attempts were reset to 0 in auth.py
        with client.session_transaction() as sess:
            assert sess['login_attempts'] == 0

@pytest.mark.security_on
def test_session_cookie_properties(app):
    """Test that session cookies are flagged as Secure and HttpOnly."""
    # We are testing if our security configuration is present in the app config
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == "Lax"


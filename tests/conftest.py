import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("EBAY_CLIENT_ID", "test-ebay-client-id")
os.environ.setdefault("EBAY_CLIENT_SECRET", "test-ebay-client-secret")
os.environ.setdefault("EBAY_RU_NAME", "test-ebay-ru-name")
os.environ.setdefault("EBAY_ENVIRONMENT", "SANDBOX")


import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth import CurrentUser, UserProfile


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    return CurrentUser(
        id="auth-user-id-123",
        email="test@example.com",
        profile=UserProfile(
            user_id=456,
            first_name="Test",
            last_name="User",
            email="test@example.com",
        ),
    )


@pytest.fixture
def mock_user_no_profile():
    return CurrentUser(id="auth-user-id-123", email="test@example.com", profile=None)


@pytest.fixture
def authed_client(client, mock_user):
    """Client with auth dependency overridden to return a valid user."""
    from app.middleware.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(client, mock_user_no_profile):
    """Client with auth returning a user that has no profile."""
    from app.middleware.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user_no_profile
    yield client
    app.dependency_overrides.clear()

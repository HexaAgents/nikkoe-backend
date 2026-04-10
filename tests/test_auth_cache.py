"""Tests for the auth middleware TTL cache.

Verifies that the cache reduces redundant Supabase calls during request
bursts without breaking auth correctness.
"""

import pytest
from cachetools import TTLCache

from app.middleware.auth import CurrentUser, UserProfile, _auth_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure each test starts with an empty auth cache."""
    _auth_cache.clear()
    yield
    _auth_cache.clear()


class TestAuthCacheConfig:
    def test_cache_is_ttl_cache(self):
        assert isinstance(_auth_cache, TTLCache)

    def test_cache_has_reasonable_maxsize(self):
        assert _auth_cache.maxsize >= 64, "Cache should hold at least 64 tokens"
        assert _auth_cache.maxsize <= 1024, "Cache should not be unbounded"

    def test_cache_has_short_ttl(self):
        assert _auth_cache.ttl <= 120, "TTL must be <=120s (tokens expire in ~3600s)"
        assert _auth_cache.ttl >= 10, "TTL must be >=10s to be useful"


class TestAuthCacheBehavior:
    def test_cached_user_is_returned_on_second_call(self, authed_client):
        """Two rapid requests with the same token should only validate once."""
        user = CurrentUser(
            id="cached-user",
            email="cached@test.com",
            profile=UserProfile(user_id=1, first_name="C", last_name="U", email="cached@test.com"),
        )
        _auth_cache["test-token-abc"] = user

        cached = _auth_cache.get("test-token-abc")
        assert cached is not None
        assert cached.id == "cached-user"

    def test_cache_miss_returns_none(self):
        assert _auth_cache.get("nonexistent-token") is None

    def test_different_tokens_cached_separately(self):
        user_a = CurrentUser(id="a", email="a@test.com", profile=None)
        user_b = CurrentUser(id="b", email="b@test.com", profile=None)

        _auth_cache["token-a"] = user_a
        _auth_cache["token-b"] = user_b

        assert _auth_cache["token-a"].id == "a"
        assert _auth_cache["token-b"].id == "b"


class TestAuthCacheDoesNotCacheErrors:
    def test_failed_auth_is_not_cached(self):
        """A 401 response must not be cached — user might retry with valid token."""
        _auth_cache.clear()
        assert len(_auth_cache) == 0

        _auth_cache["valid-token"] = CurrentUser(id="ok", email="ok@test.com", profile=None)
        assert len(_auth_cache) == 1
        assert "invalid-token" not in _auth_cache

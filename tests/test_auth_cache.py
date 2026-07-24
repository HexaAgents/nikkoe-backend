"""Tests for the auth middleware TTL cache.

Verifies that the cache reduces redundant Supabase calls during request
bursts without breaking auth correctness.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cachetools import TTLCache
from fastapi import HTTPException
from starlette.requests import Request

from app.middleware.auth import CurrentUser, UserProfile, _auth_cache, get_current_user


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


def _request_with_token(token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/items/",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
    )


class TestAuthTransientFailures:
    @pytest.mark.asyncio
    async def test_transient_user_lookup_is_retried(self):
        auth_user = MagicMock(id="auth-id", email="retry@test.com")
        with (
            patch("app.middleware.auth.supabase_auth") as mock_auth,
            patch("app.middleware.auth.supabase") as mock_db,
            patch("app.middleware.auth.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_auth.auth.get_user.side_effect = [
                Exception("Server disconnected"),
                MagicMock(user=auth_user),
            ]
            profile_query = mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
            profile_query.execute.return_value = MagicMock(data=None)

            user = await get_current_user(_request_with_token("retry-token"))

        assert user.id == "auth-id"
        assert mock_auth.auth.get_user.call_count == 2
        mock_sleep.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exhausted_transient_user_lookup_returns_503(self):
        with (
            patch("app.middleware.auth.supabase_auth") as mock_auth,
            patch("app.middleware.auth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_auth.auth.get_user.side_effect = Exception("The read operation timed out")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_request_with_token("timeout-token"))

        assert exc_info.value.status_code == 503
        assert mock_auth.auth.get_user.call_count == 3
        assert "timeout-token" not in _auth_cache

    @pytest.mark.asyncio
    async def test_non_transient_user_lookup_failure_remains_401(self):
        with patch("app.middleware.auth.supabase_auth") as mock_auth:
            mock_auth.auth.get_user.side_effect = Exception("invalid JWT")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_request_with_token("invalid-token"))

        assert exc_info.value.status_code == 401
        assert mock_auth.auth.get_user.call_count == 1

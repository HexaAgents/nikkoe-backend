"""Tests for error classes and exception handler functions."""

import json
from unittest.mock import MagicMock

import pytest

from app.errors import (
    PG_ERROR_MAP,
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    app_error_handler,
    general_error_handler,
    validation_error_handler,
)

# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class TestAppError:
    def test_stores_status_and_message(self):
        err = AppError(422, "Bad input")
        assert err.status_code == 422
        assert err.message == "Bad input"

    def test_is_exception(self):
        err = AppError(500, "Boom")
        assert isinstance(err, Exception)

    def test_str_representation(self):
        err = AppError(400, "Nope")
        assert str(err) == "Nope"


class TestNotFoundError:
    def test_404_with_formatted_message(self):
        err = NotFoundError("Item", "abc-123")
        assert err.status_code == 404
        assert err.message == "Item abc-123 not found"

    def test_is_app_error(self):
        assert isinstance(NotFoundError("X", "1"), AppError)


class TestConflictError:
    def test_409(self):
        err = ConflictError("Already exists")
        assert err.status_code == 409
        assert err.message == "Already exists"


class TestForbiddenError:
    def test_default_message(self):
        err = ForbiddenError()
        assert err.status_code == 403
        assert err.message == "Forbidden"

    def test_custom_message(self):
        err = ForbiddenError("Not your resource")
        assert err.message == "Not your resource"


# ---------------------------------------------------------------------------
# PG_ERROR_MAP
# ---------------------------------------------------------------------------


class TestPgErrorMap:
    def test_duplicate_key(self):
        assert PG_ERROR_MAP["23505"]["status"] == 409

    def test_foreign_key_violation(self):
        assert PG_ERROR_MAP["23503"]["status"] == 409

    def test_not_null_violation(self):
        assert PG_ERROR_MAP["23502"]["status"] == 400


# ---------------------------------------------------------------------------
# Exception handler functions
# ---------------------------------------------------------------------------


class TestAppErrorHandler:
    @pytest.mark.asyncio
    async def test_returns_correct_status_and_body(self):
        err = AppError(404, "Not found")
        resp = await app_error_handler(MagicMock(), err)
        assert resp.status_code == 404
        assert resp.body == b'{"error":"Not found"}'

    @pytest.mark.asyncio
    async def test_custom_status(self):
        err = AppError(418, "I'm a teapot")
        resp = await app_error_handler(MagicMock(), err)
        assert resp.status_code == 418


class TestValidationErrorHandler:
    @pytest.mark.asyncio
    async def test_returns_400_with_details(self):
        from pydantic import ValidationError

        from app.schemas import ItemInput

        try:
            ItemInput()
        except ValidationError as exc:
            resp = await validation_error_handler(MagicMock(), exc)
            assert resp.status_code == 400
            body = json.loads(resp.body)
            assert body["error"] == "Validation failed"
            assert isinstance(body["details"], list)
            assert len(body["details"]) > 0


class TestGeneralErrorHandler:
    @pytest.mark.asyncio
    async def test_pg_duplicate_key_error(self):
        exc = Exception("duplicate")
        exc.code = "23505"
        exc.message = "duplicate key"
        resp = await general_error_handler(MagicMock(), exc)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_pg_foreign_key_error(self):
        exc = Exception("fk violation")
        exc.code = "23503"
        exc.message = "foreign key"
        resp = await general_error_handler(MagicMock(), exc)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_pg_not_null_error(self):
        exc = Exception("not null")
        exc.code = "23502"
        exc.message = "not null"
        resp = await general_error_handler(MagicMock(), exc)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_error_returns_500(self):
        exc = Exception("Something unexpected")
        resp = await general_error_handler(MagicMock(), exc)
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_empty_exception_message(self):
        exc = Exception()
        resp = await general_error_handler(MagicMock(), exc)
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert body["error"] == "Internal server error"

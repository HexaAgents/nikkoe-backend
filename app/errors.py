from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, id: str):
        super().__init__(404, f"{resource} {id} not found")


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(409, message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(403, message)


PG_ERROR_MAP = {
    "23505": {"status": 409, "message": "Duplicate record"},
    "23503": {"status": 409, "message": "Referenced record does not exist"},
    "23502": {"status": 400, "message": "Missing required field"},
}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


async def validation_error_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    details = [e.get("msg", str(e)) for e in exc.errors()]
    return JSONResponse(status_code=400, content={"error": "Validation failed", "details": details})


async def general_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    if hasattr(exc, "code") and hasattr(exc, "message"):
        code = getattr(exc, "code", "")
        mapped = PG_ERROR_MAP.get(str(code))
        if mapped:
            return JSONResponse(status_code=mapped["status"], content={"error": mapped["message"]})

    message = str(exc) if str(exc) else "Internal server error"
    print(f"[API Error] {exc}")
    return JSONResponse(status_code=500, content={"error": message})

from fastapi import Request
from fastapi.responses import JSONResponse

from auth.exception.auth_exceptions import AuthError


async def auth_error_handler(_request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.config import get_session
from auth.constants import AUTH_ROUTER_PREFIX
from auth.dto import AuthRequest, LoginResponse, RegisterResponse
from auth.service import login as login_user
from auth.service import register as register_user

router = APIRouter(prefix=AUTH_ROUTER_PREFIX)

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: AuthRequest, session: Session) -> RegisterResponse:
    user = await register_user(session, body.email, body.password)
    return RegisterResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: AuthRequest, session: Session) -> LoginResponse:
    access_token = await login_user(session, body.email, body.password)
    return LoginResponse(access_token=access_token)

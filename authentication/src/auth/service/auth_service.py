from sqlalchemy.ext.asyncio import AsyncSession

from auth.entity import User
from auth.exception import InvalidCredentialsError
from auth.functions import create_access_token, hash_password, verify_password
from auth.repository import create, get_by_email


async def register(session: AsyncSession, email: str, password: str) -> User:
    return await create(session, email, hash_password(password))


async def login(session: AsyncSession, email: str, password: str) -> str:
    user = await get_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return create_access_token(str(user.id), user.email)

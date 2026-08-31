import uuid
from typing import Annotated

from fastapi import Header, HTTPException

from settlement.constants import USER_ID_HEADER


def require_user_id(
    x_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
) -> uuid.UUID:
    if not x_user_id:
        raise HTTPException(status_code=401)
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401) from None

from typing import Annotated

from fastapi import Header, HTTPException

from auction.constants.auction_constants import USER_ID_HEADER


def require_user_id(
    x_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401)
    return x_user_id

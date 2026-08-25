from fastapi import Request
from fastapi.responses import JSONResponse

from auction.exception.auction_exceptions import AuctionError


async def auction_error_handler(_request: Request, exc: AuctionError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

from fastapi import FastAPI

from auction.controller import router
from auction.exception import AuctionError, auction_error_handler

app = FastAPI(title="auction")
app.add_exception_handler(AuctionError, auction_error_handler)
app.include_router(router)

from auction.constants.auction_constants import (
    ERROR_AUCTION_NOT_DRAFT,
    ERROR_AUCTION_NOT_FOUND,
    ERROR_FORBIDDEN,
)


class AuctionError(Exception):
    status_code: int
    detail: str

    def __init__(self, detail: str, status_code: int) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class AuctionNotFoundError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_AUCTION_NOT_FOUND, 404)


class ForbiddenError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_FORBIDDEN, 403)


class AuctionNotDraftError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_AUCTION_NOT_DRAFT, 409)


class AuctionValidationError(AuctionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, 422)

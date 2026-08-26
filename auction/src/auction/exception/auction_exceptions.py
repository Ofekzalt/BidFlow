from auction.constants.auction_constants import (
    ERROR_AUCTION_ENDED,
    ERROR_AUCTION_NOT_DRAFT,
    ERROR_AUCTION_NOT_FOUND,
    ERROR_AUCTION_NOT_OPEN,
    ERROR_BID_TOO_LOW,
    ERROR_FORBIDDEN,
    ERROR_IDEMPOTENCY_MISMATCH,
    ERROR_PAYMENT_NOT_READY,
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


class AuctionNotOpenError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_AUCTION_NOT_OPEN, 409)


class AuctionEndedError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_AUCTION_ENDED, 409)


class BidTooLowError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_BID_TOO_LOW, 422)


class PaymentNotReadyError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_PAYMENT_NOT_READY, 403)


class IdempotencyConflictError(AuctionError):
    def __init__(self) -> None:
        super().__init__(ERROR_IDEMPOTENCY_MISMATCH, 409)


class AuctionValidationError(AuctionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, 422)

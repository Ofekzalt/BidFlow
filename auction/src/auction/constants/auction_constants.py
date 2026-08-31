USER_ID_HEADER = "X-User-Id"
ERROR_AUCTION_NOT_FOUND = "auction not found"
ERROR_FORBIDDEN = "forbidden"
ERROR_AUCTION_NOT_DRAFT = "auction is not a draft"
ERROR_AUCTION_NOT_OPEN = "auction is not open"
ERROR_AUCTION_ENDED = "auction has ended"
ERROR_BID_TOO_LOW = "amount_cents must be greater than current price"
ERROR_PAYMENT_NOT_READY = "payment method is not ready"
ERROR_IDEMPOTENCY_MISMATCH = "idempotency key reuse with a different request"
ERROR_STARTING_PRICE_POSITIVE = "starting_price_cents must be greater than 0"
ERROR_START_BEFORE_END = "start_time must be before end_time"

AUCTIONS_TABLE_NAME = "auctions"
PROCESSED_EVENTS_TABLE_NAME = "processed_events"
BIDDER_PAYMENT_STATUS_TABLE_NAME = "bidder_payment_status"
BIDS_TABLE_NAME = "bids"
IDEMPOTENCY_KEYS_TABLE_NAME = "idempotency_keys"
OUTBOX_EVENTS_TABLE_NAME = "outbox_events"
AUCTION_ROUTER_PREFIX = "/auctions"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

TITLE_MAX_LENGTH = 255
MAX_CENTS = 2_147_483_647
EVENT_TYPE_AUCTION_ENDED = "AuctionEnded"
EVENT_TYPE_PAYMENT_METHOD_READY = "PaymentMethodReady"
EVENT_TYPE_PAYMENT_METHOD_REMOVED = "PaymentMethodRemoved"
EVENT_TYPE_PAYMENT_SUCCEEDED = "PaymentSucceeded"
EVENT_TYPE_PAYMENT_FAILED = "PaymentFailed"
EVENT_VERSION_V1 = "v1"
CURRENCY_USD = "USD"
PRODUCER_AUCTION = "auction"
RABBITMQ_EVENTS_EXCHANGE = "live-auction.events"
RABBITMQ_RETRY_EXCHANGE = "live-auction.retry"
RABBITMQ_DLX_EXCHANGE = "live-auction.dlx"
QUEUE_AUCTION_ENDED = "settlement.auction-ended"
QUEUE_PAYMENT_METHOD = "auction.payment-method"
QUEUE_PAYMENT_RESULT = "auction.payment-result"
QUEUE_DLQ = "live-auction.dlq"
ROUTING_KEY_AUCTION_ENDED = "auction.ended.v1"
ROUTING_KEY_PAYMENT_METHOD_READY = "payment_method.ready.v1"
ROUTING_KEY_PAYMENT_METHOD_REMOVED = "payment_method.removed.v1"
ROUTING_KEY_PAYMENT_SUCCEEDED = "payment.succeeded.v1"
ROUTING_KEY_PAYMENT_FAILED = "payment.failed.v1"
HEADER_RETRY_COUNT = "x-retry-count"
HEADER_ORIGINAL_ROUTING_KEY = "x-original-routing-key"
HEADER_LAST_ERROR = "x-last-error"

AUCTION_STATUS_DRAFT = "DRAFT"
AUCTION_STATUS_OPEN = "OPEN"
AUCTION_STATUS_UNSOLD = "UNSOLD"
AUCTION_STATUS_PAYMENT_PENDING = "PAYMENT_PENDING"
AUCTION_STATUS_SOLD = "SOLD"
AUCTION_STATUS_UNPAID = "UNPAID"

AUCTION_STATUSES = (
    AUCTION_STATUS_DRAFT,
    AUCTION_STATUS_OPEN,
    AUCTION_STATUS_UNSOLD,
    AUCTION_STATUS_PAYMENT_PENDING,
    AUCTION_STATUS_SOLD,
    AUCTION_STATUS_UNPAID,
)

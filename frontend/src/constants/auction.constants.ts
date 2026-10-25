export const TITLE_MAX_LENGTH = 255;
export const MAX_CENTS = 2_147_483_647;

export const AUCTION_POLL_INTERVAL_MS = 1500;

export const AUCTION_STATUS_DRAFT = "DRAFT";
export const AUCTION_STATUS_OPEN = "OPEN";
export const AUCTION_STATUS_UNSOLD = "UNSOLD";
export const AUCTION_STATUS_SOLD = "SOLD";
export const AUCTION_STATUS_UNPAID = "UNPAID";

export const ERROR_AUCTION_NOT_DRAFT = "auction is not a draft";
export const ERROR_AUCTION_NOT_OPEN = "auction is not open";
export const ERROR_AUCTION_ENDED = "auction has ended";
export const ERROR_BID_TOO_LOW = "amount_cents must be greater than current price";
export const ERROR_FORBIDDEN = "forbidden";
export const ERROR_IDEMPOTENCY_MISMATCH =
  "idempotency key reuse with a different request";
export const ERROR_PAYMENT_NOT_READY = "payment method is not ready";
export const ERROR_START_BEFORE_END = "Start time must be before end time.";

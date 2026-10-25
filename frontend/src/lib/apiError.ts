import type { AxiosResponse } from "axios";

import type { ApiProblemDetail, ApiValidationDetail } from "@/api/types";
import {
  ERROR_AUCTION_ENDED,
  ERROR_AUCTION_NOT_OPEN,
  ERROR_BID_TOO_LOW,
  ERROR_IDEMPOTENCY_MISMATCH,
  ERROR_PAYMENT_NOT_READY,
} from "@/constants/auction.constants";
import {
  AUTH_FORM_INVALID_CREDENTIALS,
  ERROR_EMAIL_ALREADY_REGISTERED,
  ERROR_INVALID_CREDENTIALS,
} from "@/constants/auth.constants";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export type DomainErrorCode =
  | "stale_bid"
  | "auction_closed"
  | "idempotency_conflict"
  | "payment_not_ready"
  | "unknown";

const domainErrorMatchers: Array<{
  status: number;
  detail: string;
  code: DomainErrorCode;
}> = [
  {
    status: 422,
    detail: ERROR_BID_TOO_LOW,
    code: "stale_bid",
  },
  {
    status: 409,
    detail: ERROR_AUCTION_NOT_OPEN,
    code: "auction_closed",
  },
  {
    status: 409,
    detail: ERROR_AUCTION_ENDED,
    code: "auction_closed",
  },
  {
    status: 409,
    detail: ERROR_IDEMPOTENCY_MISMATCH,
    code: "idempotency_conflict",
  },
  {
    status: 403,
    detail: ERROR_PAYMENT_NOT_READY,
    code: "payment_not_ready",
  },
];

export function toDomainErrorCode(error: ApiError): DomainErrorCode {
  const match = domainErrorMatchers.find(
    (candidate) =>
      candidate.status === error.status && candidate.detail === error.detail,
  );
  return match?.code ?? "unknown";
}

export function parseApiError(response: AxiosResponse): ApiError {
  const status = response.status;
  let detail = response.statusText || "Request failed";

  const body = response.data as
    | ApiProblemDetail
    | ApiValidationDetail
    | undefined;

  if (body && "detail" in body) {
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body.detail) && body.detail.length > 0) {
      detail = body.detail.map((issue) => issue.msg).join("; ");
    }
  }

  return new ApiError(status, detail);
}

export function authFieldErrors(error: ApiError): Record<string, string> {
  if (error.status === 409 && error.detail === ERROR_EMAIL_ALREADY_REGISTERED) {
    return { email: error.detail };
  }

  if (error.status === 401 && error.detail === ERROR_INVALID_CREDENTIALS) {
    return { form: AUTH_FORM_INVALID_CREDENTIALS };
  }

  if (error.status === 422) {
    const lower = error.detail.toLowerCase();
    if (lower.includes("password")) {
      return { password: error.detail };
    }
    if (lower.includes("email")) {
      return { email: error.detail };
    }
    return { form: error.detail };
  }

  return { form: error.detail };
}

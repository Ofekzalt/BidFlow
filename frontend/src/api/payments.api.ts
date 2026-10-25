import type { z } from "zod";

import {
  paymentMethodListDto,
  paymentMethodResponseDto,
  setupIntentResponseDto,
} from "@/dto/payment.dto";
import { request } from "@/lib/http";

export type SetupIntentResponse = z.infer<typeof setupIntentResponseDto>;
export type PaymentMethodResponse = z.infer<typeof paymentMethodResponseDto>;

export function createSetupIntent() {
  return request("/payments/setup-intent", {
    method: "POST",
    responseDto: setupIntentResponseDto,
  });
}

export function listPaymentMethods() {
  return request("/payments/methods", {
    method: "GET",
    responseDto: paymentMethodListDto,
  });
}

export function deletePaymentMethod(paymentMethodId: string) {
  return request<void>(`/payments/methods/${paymentMethodId}`, {
    method: "DELETE",
  });
}

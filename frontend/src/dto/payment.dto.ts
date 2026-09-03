import { z } from "zod";

import { uuidDto } from "@/dto/common.dto";

export const setupIntentResponseDto = z.object({
  client_secret: z.string(),
  stripe_customer_id: z.string(),
});

export const paymentMethodResponseDto = z.object({
  id: uuidDto,
  stripe_payment_method_id: z.string(),
  is_default: z.boolean(),
});

export const paymentMethodListDto = z.array(paymentMethodResponseDto);

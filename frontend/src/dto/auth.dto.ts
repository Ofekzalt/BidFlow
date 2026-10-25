import { z } from "zod";

import {
  ERROR_PASSWORD_TOO_SHORT,
  PASSWORD_MIN_LENGTH,
} from "@/constants/auth.constants";
import { isoDateTimeDto, uuidDto } from "@/dto/common.dto";

export const authCredentialsDto = z.object({
  email: z
    .string()
    .trim()
    .pipe(z.email())
    .transform((value) => value.toLowerCase()),
  password: z.string().min(PASSWORD_MIN_LENGTH, {
    message: ERROR_PASSWORD_TOO_SHORT,
  }),
});

export const registerResponseDto = z.object({
  id: uuidDto,
  email: z.string(),
  created_at: isoDateTimeDto,
});

export const loginResponseDto = z.object({
  access_token: z.string(),
  token_type: z.string(),
});

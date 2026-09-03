import type { z } from "zod";

import {
  authCredentialsDto,
  loginResponseDto,
  registerResponseDto,
} from "@/dto/auth.dto";
import {
  apiProblemDetailDto,
  apiValidationDetailDto,
} from "@/dto/common.dto";

export type AuthCredentials = z.infer<typeof authCredentialsDto>;
export type RegisterResponse = z.infer<typeof registerResponseDto>;
export type LoginResponse = z.infer<typeof loginResponseDto>;
export type ApiProblemDetail = z.infer<typeof apiProblemDetailDto>;
export type ApiValidationDetail = z.infer<typeof apiValidationDetailDto>;

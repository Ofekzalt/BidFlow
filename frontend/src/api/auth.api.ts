import type { AuthCredentials } from "@/api/types";
import { loginResponseDto, registerResponseDto } from "@/dto/auth.dto";
import { request } from "@/lib/http";

export function register(credentials: AuthCredentials) {
  return request("/auth/register", {
    method: "POST",
    body: credentials,
    auth: false,
    responseDto: registerResponseDto,
  });
}

export function login(credentials: AuthCredentials) {
  return request("/auth/login", {
    method: "POST",
    body: credentials,
    auth: false,
    responseDto: loginResponseDto,
  });
}

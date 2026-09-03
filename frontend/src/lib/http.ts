import type { z } from "zod";

import {
  CONTENT_TYPE_JSON,
  DEFAULT_API_BASE_URL,
  HEADER_AUTHORIZATION,
  HEADER_CONTENT_TYPE,
  HEADER_IDEMPOTENCY_KEY,
} from "@/constants/api.constants";
import { parseApiError } from "@/lib/apiError";
import { getAccessToken } from "@/auth/tokenStorage";
import axios, { isAxiosError, type AxiosResponse } from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

export const httpClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: CONTENT_TYPE_JSON,
  },
});

type RequestOptions<T> = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  bodyDto?: z.ZodType;
  responseDto?: z.ZodType<T>;
  auth?: boolean;
  idempotencyKey?: string;
};

export type RequestMeta = {
  serverDateMs: number | null;
};

function parseServerDate(response: AxiosResponse) {
  const dateHeader = response.headers.date;
  if (!dateHeader || Array.isArray(dateHeader)) {
    return null;
  }
  const parsed = Date.parse(dateHeader);
  return Number.isNaN(parsed) ? null : parsed;
}

function parseResponseData<T>(
  response: AxiosResponse,
  responseDto?: z.ZodType<T>,
) {
  if (response.status === 204) {
    return undefined as T;
  }

  if (responseDto) {
    return responseDto.parse(response.data);
  }

  return response.data as T;
}

async function executeRequest<T>(
  path: string,
  options: RequestOptions<T>,
) {
  let body = options.body;

  if (body !== undefined && options.bodyDto) {
    body = options.bodyDto.parse(body);
  }

  const headers: Record<string, string> = {};

  if (body !== undefined) {
    headers[HEADER_CONTENT_TYPE] = CONTENT_TYPE_JSON;
  }

  if (options.auth !== false) {
    const token = getAccessToken();
    if (token) {
      headers[HEADER_AUTHORIZATION] = `Bearer ${token}`;
    }
  }

  if (options.idempotencyKey) {
    headers[HEADER_IDEMPOTENCY_KEY] = options.idempotencyKey;
  }

  try {
    const response = await httpClient.request<T>({
      url: path,
      method: options.method ?? "GET",
      data: body,
      headers,
    });

    return {
      response,
      data: parseResponseData(response, options.responseDto),
    };
  } catch (error) {
    if (isAxiosError(error) && error.response) {
      throw parseApiError(error.response);
    }
    throw error;
  }
}

export async function request<T>(
  path: string,
  options: RequestOptions<T> = {},
): Promise<T> {
  const { data } = await executeRequest(path, options);
  return data;
}

export async function requestWithMeta<T>(
  path: string,
  options: RequestOptions<T> = {},
): Promise<{ data: T; meta: RequestMeta }> {
  const { response, data } = await executeRequest(path, options);
  return {
    data,
    meta: {
      serverDateMs: parseServerDate(response),
    },
  };
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

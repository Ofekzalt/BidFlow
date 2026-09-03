export type JwtPayload = {
  sub?: string;
  email?: string;
  exp?: number;
};

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = (4 - (normalized.length % 4)) % 4;
  return atob(normalized + "=".repeat(padding));
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  const payload = token.split(".")[1];
  if (!payload) {
    return null;
  }

  try {
    return JSON.parse(decodeBase64Url(payload)) as JwtPayload;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string, nowMs = Date.now()) {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) {
    return true;
  }

  return payload.exp * 1000 <= nowMs;
}

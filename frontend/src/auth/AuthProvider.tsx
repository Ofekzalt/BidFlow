import {
  createContext,
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { decodeJwtPayload, isTokenExpired } from "@/auth/jwt";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "@/auth/tokenStorage";

type AuthUser = {
  id: string;
  email: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

function readUserFromToken(token: string | null): AuthUser | null {
  if (!token || isTokenExpired(token)) {
    return null;
  }

  const payload = decodeJwtPayload(token);
  if (!payload?.sub) {
    return null;
  }

  return {
    id: payload.sub,
    email: payload.email ?? "",
  };
}

function loadInitialUser() {
  const token = getAccessToken();
  const user = readUserFromToken(token);
  if (token && !user) {
    clearAccessToken();
  }
  return user;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => loadInitialUser());

  const signIn = useCallback((token: string) => {
    setAccessToken(token);
    setUser(readUserFromToken(token));
  }, []);

  const signOut = useCallback(() => {
    clearAccessToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: user !== null,
      signIn,
      signOut,
    }),
    [user, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

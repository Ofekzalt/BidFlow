import { useMemo } from "react";

export function useServerClockSkew(serverDateMs: number | null) {
  return useMemo(() => {
    if (serverDateMs === null) {
      return 0;
    }
    return serverDateMs - Date.now();
  }, [serverDateMs]);
}

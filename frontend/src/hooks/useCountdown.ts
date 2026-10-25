import { useEffect, useMemo, useState } from "react";

import { formatCountdown } from "@/format/time";

export function useCountdown(endTimeIso: string, skewMs: number) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, []);

  return useMemo(() => {
    const endMs = Date.parse(endTimeIso);
    const remainingMs = Math.max(0, endMs - (nowMs + skewMs));

    return {
      remainingMs,
      label: formatCountdown(remainingMs),
      isExpired: remainingMs === 0,
    };
  }, [endTimeIso, nowMs, skewMs]);
}

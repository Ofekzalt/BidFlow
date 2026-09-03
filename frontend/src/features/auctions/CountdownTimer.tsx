import { AUCTION_STATUS_OPEN } from "@/constants/auction.constants";
import { useCountdown } from "@/hooks/useCountdown";
import { Text } from "@/ui/Text";

type CountdownTimerProps = {
  endTimeIso: string;
  status: string;
  skewMs: number;
};

export function CountdownTimer({
  endTimeIso,
  status,
  skewMs,
}: CountdownTimerProps) {
  const { label, isExpired } = useCountdown(endTimeIso, skewMs);

  if (status !== AUCTION_STATUS_OPEN) {
    return null;
  }

  return (
    <Text variant="data" muted={isExpired}>
      {isExpired ? "Ended" : label}
    </Text>
  );
}

import { Link } from "react-router-dom";

import type { AuctionResponse } from "@/api/auctions.api";
import { AuctionStatusBadge } from "@/features/auctions/AuctionStatusBadge";
import { CountdownTimer } from "@/features/auctions/CountdownTimer";
import { CurrentPrice } from "@/features/auctions/CurrentPrice";
import { formatDateTime } from "@/format/time";
import { Card } from "@/ui/Card";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

import styles from "./AuctionCard.module.css";

type AuctionCardProps = {
  auction: AuctionResponse;
  skewMs?: number;
};

export function AuctionCard({ auction, skewMs = 0 }: AuctionCardProps) {
  return (
    <Card className={styles.card}>
      <Stack gap="md">
        <Stack direction="row" justify="space-between" align="center">
          <Link className={styles.titleLink} to={`/auctions/${auction.id}`}>
            <Text variant="heading">{auction.title}</Text>
          </Link>
          <AuctionStatusBadge status={auction.status} />
        </Stack>
        <Text muted>{auction.description}</Text>
        <Stack direction="row" justify="space-between" align="center">
          <Stack gap="sm">
            <Text variant="caption" muted>
              Current price
            </Text>
            <CurrentPrice cents={auction.current_price_cents} />
          </Stack>
          <Stack gap="sm" align="end">
            <Text variant="caption" muted>
              Ends
            </Text>
            <Text variant="caption">{formatDateTime(auction.end_time)}</Text>
            <CountdownTimer
              endTimeIso={auction.end_time}
              status={auction.status}
              skewMs={skewMs}
            />
          </Stack>
        </Stack>
      </Stack>
    </Card>
  );
}

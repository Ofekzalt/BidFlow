import { Link, useParams } from "react-router-dom";

import {
  AUCTION_STATUS_DRAFT,
  AUCTION_STATUS_OPEN,
} from "@/constants/auction.constants";
import { AuctionStatusBadge } from "@/features/auctions/AuctionStatusBadge";
import { BidForm } from "@/features/auctions/BidForm";
import { CountdownTimer } from "@/features/auctions/CountdownTimer";
import { CurrentPrice } from "@/features/auctions/CurrentPrice";
import { useAuction } from "@/hooks/useAuction";
import { useAuth } from "@/auth/useAuth";
import { useServerClockSkew } from "@/hooks/useServerClockSkew";
import { formatDateTime } from "@/format/time";
import { toDomainErrorCode } from "@/lib/apiError";
import { Button } from "@/ui/Button";
import { Card } from "@/ui/Card";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";
import { useToast } from "@/ui/Toast";

import styles from "./AuctionDetailPage.module.css";

export function AuctionDetailPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const { showToast } = useToast();
  const { auction, serverDateMs, isLoading, isError } = useAuction(id);
  const skewMs = useServerClockSkew(serverDateMs);

  if (isLoading) {
    return <Text muted>Loading auction...</Text>;
  }

  if (isError || !auction) {
    return <p className={styles.error}>Unable to load auction.</p>;
  }

  const isSeller = user?.id === auction.seller_id;
  const canBid =
    auction.status === AUCTION_STATUS_OPEN && !isSeller;
  const canEdit =
    auction.status === AUCTION_STATUS_DRAFT && isSeller;

  function handleDomainError(
    code: ReturnType<typeof toDomainErrorCode>,
    message: string,
  ) {
    showToast({
      title: code === "payment_not_ready" ? "Payment method required" : "Bid rejected",
      description: message,
      type: "error",
    });
  }

  return (
    <Stack gap="lg">
      <Stack direction="row" justify="space-between" align="center">
        <Stack gap="sm">
          <Text variant="title">{auction.title}</Text>
          <AuctionStatusBadge status={auction.status} />
        </Stack>
        {canEdit ? (
          <Link to={`/auctions/${auction.id}/edit`}>
            <Button variant="secondary" type="button">
              Edit draft
            </Button>
          </Link>
        ) : null}
      </Stack>

      <div className={styles.grid}>
        <Card>
          <Stack gap="md">
            <Text>{auction.description}</Text>
            <Stack gap="sm">
              <Text variant="caption" muted>
                Current price
              </Text>
              <CurrentPrice cents={auction.current_price_cents} />
            </Stack>
            <Stack gap="sm">
              <Text variant="caption" muted>
                Schedule
              </Text>
              <Text variant="caption">
                {formatDateTime(auction.start_time)} –{" "}
                {formatDateTime(auction.end_time)}
              </Text>
              <CountdownTimer
                endTimeIso={auction.end_time}
                status={auction.status}
                skewMs={skewMs}
              />
            </Stack>
            {auction.current_winner_id ? (
              <Text variant="caption" muted>
                Leading bidder: {auction.current_winner_id}
              </Text>
            ) : null}
          </Stack>
        </Card>

        {canBid ? (
          <Card>
            <Stack gap="md">
              <Text variant="heading">Place a bid</Text>
              <BidForm
                auctionId={auction.id}
                currentPriceCents={auction.current_price_cents}
                onDomainError={handleDomainError}
              />
            </Stack>
          </Card>
        ) : null}

        {isSeller && auction.status === AUCTION_STATUS_OPEN ? (
          <Card>
            <Text muted>
              You are the seller. Bidding is disabled on your own auction.
            </Text>
          </Card>
        ) : null}
      </div>
    </Stack>
  );
}

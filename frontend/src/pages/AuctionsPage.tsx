import { Link } from "react-router-dom";

import { AuctionCard } from "@/features/auctions/AuctionCard";
import { useAuctions } from "@/hooks/useAuctions";
import { Button } from "@/ui/Button";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

import styles from "./AuctionsPage.module.css";

export function AuctionsPage() {
  const { data: auctions, isLoading, isError } = useAuctions();

  return (
    <Stack gap="lg" className={styles.page}>
      <Stack direction="row" justify="space-between" align="center">
        <Stack gap="sm">
          <Text variant="title">Auctions</Text>
          <Text muted>Browse live and upcoming auctions.</Text>
        </Stack>
        <Link to="/auctions/new">
          <Button type="button">Create auction</Button>
        </Link>
      </Stack>

      {isLoading ? <Text muted>Loading auctions...</Text> : null}
      {isError ? (
        <p className={styles.error}>Unable to load auctions.</p>
      ) : null}

      {auctions && auctions.length === 0 ? (
        <p className={styles.empty}>No auctions yet.</p>
      ) : null}

      <div className={styles.list}>
        {auctions?.map((auction) => (
          <AuctionCard key={auction.id} auction={auction} />
        ))}
      </div>
    </Stack>
  );
}

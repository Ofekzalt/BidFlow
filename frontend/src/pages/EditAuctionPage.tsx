import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { openAuction, patchAuction } from "@/api/auctions.api";
import {
  AUCTION_STATUS_DRAFT,
  ERROR_AUCTION_NOT_DRAFT,
  ERROR_FORBIDDEN,
} from "@/constants/auction.constants";
import {
  AuctionDraftForm,
  isoToDatetimeLocal,
} from "@/features/auctions/AuctionDraftForm";
import { useAuction } from "@/hooks/useAuction";
import { useAuth } from "@/auth/useAuth";
import { ApiError } from "@/lib/apiError";
import { auctionKeys } from "@/queries/keys";
import { Button } from "@/ui/Button";
import { Card } from "@/ui/Card";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";
import { useToast } from "@/ui/Toast";

import styles from "./AuctionFormPage.module.css";

export function EditAuctionPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const { auction, isLoading, isError } = useAuction(id);

  const openMutation = useMutation({
    mutationFn: () => openAuction(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: auctionKeys.detail(id) });
      await queryClient.invalidateQueries({ queryKey: auctionKeys.list() });
      showToast({
        title: "Auction opened",
        description: "Bidders can now place bids.",
        type: "success",
      });
      navigate(`/auctions/${id}`);
    },
    onError: (error) => {
      const message =
        error instanceof ApiError ? error.detail : "Unable to open auction.";
      showToast({ title: "Open failed", description: message, type: "error" });
    },
  });

  if (isLoading) {
    return <Text muted>Loading draft...</Text>;
  }

  if (isError || !auction) {
    return <p className={styles.formError}>Unable to load auction.</p>;
  }

  if (user?.id !== auction.seller_id) {
    return <p className={styles.formError}>{ERROR_FORBIDDEN}</p>;
  }

  if (auction.status !== AUCTION_STATUS_DRAFT) {
    return <p className={styles.formError}>{ERROR_AUCTION_NOT_DRAFT}</p>;
  }

  const initialValues = {
    title: auction.title,
    description: auction.description,
    startingPriceDollars: String(auction.starting_price_cents / 100),
    startTime: isoToDatetimeLocal(auction.start_time),
    endTime: isoToDatetimeLocal(auction.end_time),
  };

  return (
    <Stack gap="lg">
      <Stack gap="sm">
        <Text variant="title">Edit auction draft</Text>
        <Text muted>Update the draft or open it for bidding.</Text>
      </Stack>
      <Card>
        <AuctionDraftForm
          mode="patch"
          initialValues={initialValues}
          submitLabel="Save changes"
          onValidSubmit={async (body) => {
            await patchAuction(id, body);
            await queryClient.invalidateQueries({
              queryKey: auctionKeys.detail(id),
            });
            showToast({
              title: "Draft saved",
              type: "success",
            });
          }}
        />
      </Card>
      <Stack direction="row" gap="sm" className={styles.actions}>
        <Button
          type="button"
          onClick={() => openMutation.mutate()}
          disabled={openMutation.isPending}
        >
          {openMutation.isPending ? "Opening..." : "Open auction"}
        </Button>
        <Link to={`/auctions/${id}`}>
          <Button variant="secondary" type="button">
            View auction
          </Button>
        </Link>
      </Stack>
    </Stack>
  );
}

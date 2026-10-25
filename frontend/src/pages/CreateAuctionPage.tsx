import { useNavigate } from "react-router-dom";

import { createAuction } from "@/api/auctions.api";
import { AuctionDraftForm } from "@/features/auctions/AuctionDraftForm";
import { Card } from "@/ui/Card";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

export function CreateAuctionPage() {
  const navigate = useNavigate();

  return (
    <Stack gap="lg">
      <Stack gap="sm">
        <Text variant="title">Create auction draft</Text>
        <Text muted>
          Drafts can be edited until you open them for bidding.
        </Text>
      </Stack>
      <Card>
        <AuctionDraftForm
          mode="create"
          submitLabel="Save draft"
          onValidSubmit={async (body) => {
            const auction = await createAuction(body);
            navigate(`/auctions/${auction.id}/edit`, { replace: true });
          }}
        />
      </Card>
    </Stack>
  );
}

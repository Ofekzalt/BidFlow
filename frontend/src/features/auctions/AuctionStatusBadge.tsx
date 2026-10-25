import {
  AUCTION_STATUS_DRAFT,
  AUCTION_STATUS_OPEN,
  AUCTION_STATUS_SOLD,
  AUCTION_STATUS_UNPAID,
  AUCTION_STATUS_UNSOLD,
} from "@/constants/auction.constants";
import { Badge } from "@/ui/Badge";

type AuctionStatusBadgeProps = {
  status: string;
};

function statusTone(status: string) {
  switch (status) {
    case AUCTION_STATUS_OPEN:
      return "accent" as const;
    case AUCTION_STATUS_DRAFT:
      return "neutral" as const;
    case AUCTION_STATUS_SOLD:
      return "success" as const;
    case AUCTION_STATUS_UNPAID:
    case AUCTION_STATUS_UNSOLD:
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

export function AuctionStatusBadge({ status }: AuctionStatusBadgeProps) {
  return <Badge tone={statusTone(status)}>{status}</Badge>;
}

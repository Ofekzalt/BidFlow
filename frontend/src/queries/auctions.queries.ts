import { queryOptions } from "@tanstack/react-query";

import { getAuctionWithMeta, listAuctions } from "@/api/auctions.api";
import { AUCTION_POLL_INTERVAL_MS } from "@/constants/auction.constants";
import { auctionKeys } from "@/queries/keys";

export function auctionListOptions() {
  return queryOptions({
    queryKey: auctionKeys.list(),
    queryFn: () => listAuctions(),
    staleTime: AUCTION_POLL_INTERVAL_MS,
    refetchInterval: AUCTION_POLL_INTERVAL_MS,
  });
}

export function auctionDetailOptions(auctionId: string) {
  return queryOptions({
    queryKey: auctionKeys.detail(auctionId),
    queryFn: () => getAuctionWithMeta(auctionId),
    staleTime: AUCTION_POLL_INTERVAL_MS,
    refetchInterval: AUCTION_POLL_INTERVAL_MS,
  });
}

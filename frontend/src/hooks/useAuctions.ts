import { useQuery } from "@tanstack/react-query";

import { auctionListOptions } from "@/queries/auctions.queries";

export function useAuctions() {
  return useQuery(auctionListOptions());
}

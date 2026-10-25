import { useQuery } from "@tanstack/react-query";

import { auctionDetailOptions } from "@/queries/auctions.queries";

export function useAuction(auctionId: string) {
  const query = useQuery(auctionDetailOptions(auctionId));

  return {
    ...query,
    auction: query.data?.data,
    serverDateMs: query.data?.meta.serverDateMs ?? null,
  };
}

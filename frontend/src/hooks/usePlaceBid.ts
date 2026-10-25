import { useMutation, useQueryClient } from "@tanstack/react-query";

import { placeBid, type PlaceBidRequest } from "@/api/auctions.api";
import { auctionKeys } from "@/queries/keys";

type PlaceBidVariables = {
  body: PlaceBidRequest;
  idempotencyKey: string;
};

export function usePlaceBid(auctionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ body, idempotencyKey }: PlaceBidVariables) =>
      placeBid(auctionId, body, idempotencyKey),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: auctionKeys.detail(auctionId),
      });
      await queryClient.invalidateQueries({
        queryKey: auctionKeys.list(),
      });
    },
  });
}

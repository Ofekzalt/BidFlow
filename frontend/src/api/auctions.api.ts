import type { z } from "zod";

import {
  auctionListDto,
  auctionResponseDto,
  bidResponseDto,
  createAuctionRequestDto,
  currentBidResponseDto,
  patchAuctionRequestDto,
  placeBidRequestDto,
} from "@/dto/auction.dto";
import { request, requestWithMeta } from "@/lib/http";

export type AuctionResponse = z.infer<typeof auctionResponseDto>;
export type CurrentBidResponse = z.infer<typeof currentBidResponseDto>;
export type PlaceBidRequest = z.infer<typeof placeBidRequestDto>;
export type BidResponse = z.infer<typeof bidResponseDto>;
export type CreateAuctionRequest = z.infer<typeof createAuctionRequestDto>;
export type PatchAuctionRequest = z.infer<typeof patchAuctionRequestDto>;

export function listAuctions() {
  return request("/auctions", {
    method: "GET",
    auth: false,
    responseDto: auctionListDto,
  });
}

export function getAuction(auctionId: string) {
  return request(`/auctions/${auctionId}`, {
    method: "GET",
    auth: false,
    responseDto: auctionResponseDto,
  });
}

export function getAuctionWithMeta(auctionId: string) {
  return requestWithMeta(`/auctions/${auctionId}`, {
    method: "GET",
    auth: false,
    responseDto: auctionResponseDto,
  });
}

export function getCurrentBid(auctionId: string) {
  return request(`/auctions/${auctionId}/current-bid`, {
    method: "GET",
    auth: false,
    responseDto: currentBidResponseDto,
  });
}

export function placeBid(
  auctionId: string,
  body: PlaceBidRequest,
  idempotencyKey: string,
) {
  return request(`/auctions/${auctionId}/bids`, {
    method: "POST",
    body,
    bodyDto: placeBidRequestDto,
    responseDto: bidResponseDto,
    idempotencyKey,
  });
}

export function createAuction(body: CreateAuctionRequest) {
  return request("/auctions", {
    method: "POST",
    body,
    bodyDto: createAuctionRequestDto,
    responseDto: auctionResponseDto,
  });
}

export function patchAuction(auctionId: string, body: PatchAuctionRequest) {
  return request(`/auctions/${auctionId}`, {
    method: "PATCH",
    body,
    bodyDto: patchAuctionRequestDto,
    responseDto: auctionResponseDto,
  });
}

export function openAuction(auctionId: string) {
  return request(`/auctions/${auctionId}/open`, {
    method: "POST",
    responseDto: auctionResponseDto,
  });
}
